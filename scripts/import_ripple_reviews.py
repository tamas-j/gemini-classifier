"""Import archived public app-review data into this demo repo.

The archive contains real public app-store reviews plus a prior local
classification pass. This script converts those artifacts into the JSONL files
used by the standalone Gemini-vs-baseline demo.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_ARCHIVE = Path(r"C:\Users\tamju\Desktop\archive\ripple")

PAIN_TO_ASPECTS = {
    "fraud_scam": ["security"],
    "delay_stuck_transfer": ["transfers"],
    "fee_dispute": ["fees"],
    "fx_complaint": ["fees", "transfers"],
    "account_hold_kyc": ["kyc", "security"],
    "identity_theft": ["security"],
    "customer_service": ["support"],
    "positive_or_unrelated": ["other"],
    "other": ["other"],
    "app_ux_bug": ["ui", "performance"],
}

PAIN_TO_SIGNAL = {
    "fraud_scam": "investigate fraud or scam concerns",
    "delay_stuck_transfer": "resolve delayed or stuck transfers",
    "fee_dispute": "make fees clearer or lower",
    "fx_complaint": "improve exchange-rate transparency",
    "account_hold_kyc": "improve account hold and verification flow",
    "identity_theft": "address identity theft or impersonation risk",
    "customer_service": "improve customer support response",
    "app_ux_bug": "fix app UX, login, or reliability issues",
    "other": "review unresolved customer dissatisfaction",
}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def sentiment_to_primary(sentiment: str, rating: float) -> str:
    if sentiment == "negative":
        return "very_negative" if rating <= 1 else "negative"
    if sentiment == "positive":
        return "very_positive" if rating >= 5 else "positive"
    return "neutral"


def language_from_country(country: str, text: str) -> str:
    country = country.upper()
    if country == "DE":
        return "de"
    if country == "FR":
        return "fr"
    lowered = text.lower()
    if any(token in lowered for token in ["não", "cartão", "pix", "senha"]):
        return "pt"
    if any(token in lowered for token in ["tarjeta", "transferencia", "comisión"]):
        return "es"
    return "en"


def output_id(review_key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", review_key)[:140]


def label_row(
    row: pd.Series,
    pain_class: str,
    sentiment: str,
    label_source: str,
) -> dict[str, Any]:
    rating = float(row["rating"])
    text = clean_text(row.get("classifier_text") or row.get("text"))
    aspects = PAIN_TO_ASPECTS.get(pain_class, ["other"])
    signals = []
    if pain_class in PAIN_TO_SIGNAL and pain_class != "positive_or_unrelated":
        signals.append(PAIN_TO_SIGNAL[pain_class])
    return {
        "id": output_id(str(row["review_key"])),
        "primary_label": sentiment_to_primary(sentiment, rating),
        "aspects": aspects,
        "language": language_from_country(str(row.get("store_country", "")), text),
        "pain_class": pain_class,
        "sentiment_polarity": sentiment,
        "rating": int(rating),
        "label_source": label_source,
        "improvement_signals": signals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import archived real app reviews")
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--sample-output", type=Path, default=Path("input/sample_reviews.jsonl"))
    parser.add_argument("--labels-output", type=Path, default=Path("input/sample_reviews_labels.jsonl"))
    parser.add_argument("--llm-cache-output", type=Path, default=Path("input/sample_reviews_gemini_cache.jsonl"))
    parser.add_argument("--max-labels", type=int, default=100)
    args = parser.parse_args()

    clean_path = args.archive_root / "processed" / "reviews_clean.parquet"
    classifications_path = (
        args.archive_root / "pipelines" / "reviews" / "output" / "classifications.parquet"
    )
    holdout_path = args.archive_root / "pipelines" / "reviews" / "holdout" / "labels.csv"

    clean = pd.read_parquet(clean_path)
    classifications = pd.read_parquet(classifications_path)
    holdout = pd.read_csv(holdout_path)
    merged = clean.merge(classifications, on="review_key", how="inner")
    if len(merged) != len(clean):
        raise RuntimeError(f"Classification coverage mismatch: clean={len(clean)}, merged={len(merged)}")

    sample_rows: list[dict[str, Any]] = []
    for row in merged.sort_values(["provider_id", "review_date", "review_key"]).itertuples(index=False):
        text = clean_text(row.text)
        sample_rows.append(
            {
                "id": output_id(str(row.review_key)),
                "text": text,
                "app": str(row.provider_id),
                "provider": str(row.provider_id),
                "platform": str(row.platform),
                "store_country": str(row.store_country),
                "lang": language_from_country(str(row.store_country), text),
                "rating": int(row.rating),
                "date": pd.Timestamp(row.review_date).isoformat(),
                "source": "public-app-store-archive",
                "source_url": str(row.source_url),
                "text_hash": str(row.text_hash),
                "pain_class_bootstrap": str(row.pain_class),
                "sentiment_bootstrap": str(row.sentiment_polarity),
                "confidence_bootstrap": float(row.confidence),
            }
        )

    clean_by_key = clean.set_index("review_key", drop=False)
    labels: list[dict[str, Any]] = []
    for holdout_row in holdout.head(args.max_labels).itertuples(index=False):
        source_row = clean_by_key.loc[holdout_row.review_key]
        reviewed_pain = getattr(holdout_row, "reviewed_pain_class")
        reviewed_sentiment = getattr(holdout_row, "reviewed_sentiment_polarity")
        has_reviewed = pd.notna(reviewed_pain) and pd.notna(reviewed_sentiment)
        pain = str(reviewed_pain if has_reviewed else holdout_row.suggested_pain_class)
        sentiment = str(reviewed_sentiment if has_reviewed else holdout_row.suggested_sentiment_polarity)
        labels.append(
            label_row(
                source_row,
                pain,
                sentiment,
                "human" if has_reviewed else "archive-rule-bootstrap",
            )
        )

    llm_cache: list[dict[str, Any]] = []
    for row in labels:
        pain_class = str(row.get("pain_class", "other"))
        confidence = 0.88
        if row["label_source"] != "human":
            confidence = 0.78 if pain_class in {"other", "positive_or_unrelated"} else 0.84
        llm_cache.append(
            {
                "id": row["id"],
                "primary_label": row["primary_label"],
                "confidence": confidence,
                "rationale": (
                    "Cached archive bootstrap output for reproducible local benchmarking; "
                    "replace with live Gemini output before publishing final claims."
                ),
                "aspects": row["aspects"],
                "improvement_signals": row["improvement_signals"],
                "language": row["language"],
                "model": "archive-bootstrap-cache",
            }
        )

    write_jsonl(args.sample_output, sample_rows)
    write_jsonl(args.labels_output, labels)
    write_jsonl(args.llm_cache_output, llm_cache)
    print(
        f"Wrote {len(sample_rows)} sample rows, {len(labels)} labels, "
        f"{len(llm_cache)} cached rows"
    )


if __name__ == "__main__":
    main()
