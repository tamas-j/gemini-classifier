"""Benchmark Gemini app-review classifications against the baseline."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, f1_score

from baseline import classify_rows, load_jsonl, write_jsonl


def by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in rows if "id" in row}


def filter_rows(
    labels: list[dict[str, Any]],
    sample_size: int | None,
    languages: set[str] | None,
) -> list[dict[str, Any]]:
    rows = labels
    if languages:
        rows = [row for row in rows if row.get("language") in languages or row.get("lang") in languages]
    if sample_size is not None:
        rows = rows[:sample_size]
    return rows


def aspect_prf(y_true: list[set[str]], y_pred: list[set[str]]) -> dict[str, float]:
    tp = fp = fn = 0
    for truth, pred in zip(y_true, y_pred):
        tp += len(truth & pred)
        fp += len(pred - truth)
        fn += len(truth - pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def metrics_for(labels: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    available = [row for row in labels if str(row["id"]) in predictions]
    y_true = [row["primary_label"] for row in available]
    y_pred = [predictions[str(row["id"])]["primary_label"] for row in available]
    true_aspects = [set(row.get("aspects", [])) for row in available]
    pred_aspects = [set(predictions[str(row["id"])].get("aspects", [])) for row in available]

    per_language: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(available):
        grouped[str(row.get("language") or row.get("lang") or "unknown")].append(index)
    for lang, indexes in grouped.items():
        yt = [y_true[i] for i in indexes]
        yp = [y_pred[i] for i in indexes]
        per_language[lang] = {
            "n": len(indexes),
            "sentiment_accuracy": accuracy_score(yt, yp),
            "sentiment_macro_f1": f1_score(yt, yp, labels=[
                "very_negative",
                "negative",
                "neutral",
                "positive",
                "very_positive",
            ], average="macro", zero_division=0),
        }

    return {
        "n": len(available),
        "sentiment_accuracy": accuracy_score(y_true, y_pred) if y_true else 0.0,
        "sentiment_macro_f1": f1_score(
            y_true,
            y_pred,
            labels=["very_negative", "negative", "neutral", "positive", "very_positive"],
            average="macro",
            zero_division=0,
        )
        if y_true
        else 0.0,
        "aspect": aspect_prf(true_aspects, pred_aspects),
        "per_language": per_language,
    }


def markdown_table(report: dict[str, Any]) -> str:
    lines = [
        "| Pipeline | n | Sentiment accuracy | Macro F1 | Aspect precision | Aspect recall | Aspect F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ["gemini", "baseline"]:
        row = report["pipelines"][name]
        lines.append(
            f"| {row['label']} | {row['n']} | {row['sentiment_accuracy']:.3f} | "
            f"{row['sentiment_macro_f1']:.3f} | {row['aspect']['precision']:.3f} | "
            f"{row['aspect']['recall']:.3f} | {row['aspect']['f1']:.3f} |"
        )
    lines.extend(["", "| Language | LLM acc | Baseline acc | LLM F1 | Baseline F1 | n |", "|---|---:|---:|---:|---:|---:|"])
    langs = sorted(
        set(report["pipelines"]["gemini"]["per_language"])
        | set(report["pipelines"]["baseline"]["per_language"])
    )
    for lang in langs:
        g = report["pipelines"]["gemini"]["per_language"].get(lang, {})
        b = report["pipelines"]["baseline"]["per_language"].get(lang, {})
        n = g.get("n", b.get("n", 0))
        lines.append(
            f"| {lang} | {g.get('sentiment_accuracy', 0):.3f} | "
            f"{b.get('sentiment_accuracy', 0):.3f} | {g.get('sentiment_macro_f1', 0):.3f} | "
            f"{b.get('sentiment_macro_f1', 0):.3f} | {n} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark app-review sentiment and aspect extraction")
    parser.add_argument("--manifest", default="input/sample_reviews.jsonl")
    parser.add_argument("--labels", default="input/sample_reviews_labels.jsonl")
    parser.add_argument("--llm-cache", default="input/sample_reviews_gemini_cache.jsonl")
    parser.add_argument("--baseline-cache", default="output/baseline_results.jsonl")
    parser.add_argument("--output", default="output/benchmark.json")
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--languages", default="", help="Comma-separated language codes")
    parser.add_argument("--skip-llm", action="store_true", help="Use cached LLM results only")
    parser.add_argument("--skip-baseline", action="store_true", help="Use cached baseline results only")
    parser.add_argument("--lexicon-only", action="store_true", help="Use baseline fallback without transformer")
    args = parser.parse_args()

    labels = load_jsonl(Path(args.labels))
    language_filter = {x.strip() for x in args.languages.split(",") if x.strip()} or None
    labels = filter_rows(labels, args.sample_size, language_filter)
    label_ids = {str(row["id"]) for row in labels}

    llm_cache_path = Path(args.llm_cache)
    if not llm_cache_path.is_file():
        raise SystemExit(
            f"Missing LLM cache: {llm_cache_path}. Run classify.py or provide --llm-cache."
        )
    llm_predictions = {
        key: value
        for key, value in by_id(load_jsonl(llm_cache_path)).items()
        if key in label_ids
    }

    baseline_cache_path = Path(args.baseline_cache)
    if args.skip_baseline and baseline_cache_path.is_file():
        baseline_predictions = by_id(load_jsonl(baseline_cache_path))
    else:
        manifest = [row for row in load_jsonl(Path(args.manifest)) if str(row.get("id")) in label_ids]
        baseline_rows = classify_rows(manifest, use_transformer=not args.lexicon_only)
        write_jsonl(baseline_cache_path, baseline_rows)
        baseline_predictions = by_id(baseline_rows)

    report = {
        "benchmark": {
            "labels": args.labels,
            "label_count": len(labels),
            "label_source_note": "Weak labels bootstrapped for the public demo; see README caveats.",
        },
        "pipelines": {
            "gemini": {
                "label": "Cached LLM/rubric output",
                **metrics_for(labels, llm_predictions),
            },
            "baseline": {
                "label": "XLM-R sentiment + aspect lexicon",
                **metrics_for(labels, baseline_predictions),
            },
        },
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(markdown_table(report))
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
