"""
Traditional NLP baseline for multilingual app-review classification.

The preferred sentiment model is CardiffNLP's XLM-R sentiment classifier. If
the model is not available locally and dependencies cannot be loaded, the script
falls back to a deterministic multilingual lexicon so the repo remains runnable
without network access.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PrimaryLabel = str

SENTIMENT_ORDER = [
    "very_negative",
    "negative",
    "neutral",
    "positive",
    "very_positive",
]

NEGATIVE_WORDS = {
    "awful", "bad", "broken", "crash", "crashes", "crashing", "fail", "failed",
    "failure", "frustrating", "hate", "impossible", "slow", "terrible", "useless",
    "worst", "bloqueada", "bloqueado", "caro", "crashea", "error", "fallo",
    "horrible", "lento", "malo", "pésimo", "schlecht", "absturz", "abstürzt",
    "langsam", "teuer", "furchtbar", "nul", "lente", "cher", "plante",
    "bloqué", "horrível", "lento", "ruim", "travando", "falha",
}

POSITIVE_WORDS = {
    "amazing", "easy", "excellent", "fast", "great", "love", "perfect",
    "reliable", "smooth", "useful", "bueno", "excelente", "fácil", "genial",
    "rápido", "útil", "super", "einfach", "schnell", "zuverlässig", "parfait",
    "rapide", "pratique", "ótimo", "excelente", "fácil", "rápido", "adoro",
}

ASPECT_KEYWORDS: dict[str, list[str]] = {
    "ui": [
        "interface", "layout", "design", "screen", "navigation", "ui", "ux",
        "interfaz", "diseño", "pantalla", "navegación", "oberfläche", "design",
        "bildschirm", "interface", "écran", "navigation", "tela", "visual",
    ],
    "performance": [
        "slow", "lag", "timeout", "loading", "battery", "lento", "cargando",
        "langsam", "laden", "lente", "chargement", "lento", "carregar",
    ],
    "support": [
        "support", "customer service", "help", "chat", "agent", "soporte",
        "atención", "hilfe", "kundenservice", "assistance", "suporte",
    ],
    "transfers": [
        "transfer", "payment", "deposit", "withdrawal", "pix", "sepa", "pago",
        "transferencia", "überweisung", "zahlung", "virement", "paiement",
        "pagamento", "transferência",
    ],
    "fees": [
        "fee", "charge", "pricing", "subscription", "exchange rate", "comisión",
        "tarifa", "gebühr", "kosten", "frais", "taxa", "mensalidade",
    ],
    "kyc": [
        "verify", "verification", "identity", "document", "passport", "kyc",
        "verificación", "identidad", "documento", "verifizierung", "ausweis",
        "vérification", "identité", "document", "verificação", "identidade",
    ],
    "notifications": [
        "notification", "alert", "push", "sms", "email", "notificación",
        "alerta", "benachrichtigung", "alerte", "notificação",
    ],
    "crashes": [
        "crash", "freeze", "bug", "won't open", "not opening", "crashea",
        "congela", "absturz", "friert", "plante", "bug", "travando", "fecha",
    ],
    "login": [
        "login", "password", "biometric", "fingerprint", "sign in", "iniciar",
        "contraseña", "huella", "anmelden", "passwort", "connexion", "mot de passe",
        "entrar", "senha", "biometria",
    ],
    "security": [
        "fraud", "blocked", "scam", "safe", "security", "bloqueado", "fraude",
        "seguridad", "gesperrt", "sicherheit", "bloqué", "sécurité", "bloqueada",
        "segurança",
    ],
    "cards": [
        "card", "debit", "virtual card", "apple pay", "tarjeta", "karte",
        "carte", "cartão",
    ],
    "rewards": [
        "cashback", "reward", "perk", "points", "promo", "recompensa",
        "puntos", "punkte", "récompense", "pontos",
    ],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {e}") from e
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def detect_language(row: dict[str, Any], text: str) -> str:
    lang = row.get("lang")
    if isinstance(lang, str) and lang:
        return lang
    lowered = text.lower()
    if any(w in lowered for w in ["não", "cartão", "senha", "pix"]):
        return "pt"
    if any(w in lowered for w in ["connexion", "frais", "virement"]):
        return "fr"
    if any(w in lowered for w in ["überweisung", "gebühr", "karte"]):
        return "de"
    if any(w in lowered for w in ["tarjeta", "contraseña", "transferencia"]):
        return "es"
    return "en"


def lexicon_sentiment(text: str) -> tuple[PrimaryLabel, float, dict[str, float]]:
    tokens = re.findall(r"[\wÀ-ÿ']+", text.lower())
    pos = sum(1 for token in tokens if token in POSITIVE_WORDS)
    neg = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    score = pos - neg
    intensity = abs(score)
    if score <= -2:
        label = "very_negative"
    elif score == -1:
        label = "negative"
    elif score == 0:
        label = "neutral"
    elif score == 1:
        label = "positive"
    else:
        label = "very_positive"
    confidence = min(0.9, 0.45 + intensity * 0.15)
    if label == "neutral":
        confidence = 0.5
    return label, confidence, {"negative": float(neg), "neutral": 0.0, "positive": float(pos)}


def transformer_sentiment(texts: list[str]) -> list[tuple[PrimaryLabel, float, dict[str, float]]]:
    try:
        from transformers import pipeline
    except Exception as e:
        raise RuntimeError(f"transformers unavailable: {e}") from e

    classifier = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        tokenizer="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        top_k=None,
        truncation=True,
        device=-1,
    )
    raw_outputs = classifier(texts)
    mapped: list[tuple[PrimaryLabel, float, dict[str, float]]] = []
    for raw in raw_outputs:
        probs = {item["label"].lower(): float(item["score"]) for item in raw}
        neg = probs.get("negative", 0.0)
        neu = probs.get("neutral", 0.0)
        pos = probs.get("positive", 0.0)
        if max(neg, neu, pos) == neu:
            label = "neutral"
            confidence = neu
        elif neg >= pos:
            label = "very_negative" if neg >= 0.72 else "negative"
            confidence = neg
        else:
            label = "very_positive" if pos >= 0.72 else "positive"
            confidence = pos
        mapped.append((label, confidence, probs))
    return mapped


def extract_aspects(text: str) -> list[str]:
    lowered = text.lower()
    aspects = [
        aspect
        for aspect, keywords in ASPECT_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    return aspects or ["other"]


def improvement_signals(text: str, aspects: list[str], sentiment: str) -> list[str]:
    if sentiment in {"positive", "very_positive"}:
        return []
    signals: list[str] = []
    phrases = re.split(r"[.!?;]+", text)
    for phrase in phrases:
        clean = " ".join(phrase.strip().split())
        if not clean:
            continue
        lowered = clean.lower()
        if any(word in lowered for word in NEGATIVE_WORDS) or any(
            keyword in lowered for aspect in aspects for keyword in ASPECT_KEYWORDS.get(aspect, [])
        ):
            signals.append(clean[:96])
        if len(signals) >= 5:
            break
    return signals


def classify_rows(rows: list[dict[str, Any]], use_transformer: bool) -> list[dict[str, Any]]:
    texts = [str(row.get("text", "")) for row in rows]
    if use_transformer:
        try:
            sentiments = transformer_sentiment(texts)
        except Exception as e:
            print(f"Transformer baseline unavailable; falling back to lexicon. Reason: {e}")
            sentiments = [lexicon_sentiment(text) for text in texts]
    else:
        sentiments = [lexicon_sentiment(text) for text in texts]

    outputs: list[dict[str, Any]] = []
    for row, text, (label, confidence, probs) in zip(rows, texts, sentiments):
        aspects = extract_aspects(text)
        outputs.append(
            {
                "id": str(row.get("id")),
                "primary_label": label,
                "confidence": round(float(confidence), 3),
                "rationale": "XLM-R sentiment score plus multilingual keyword aspect matching."
                if use_transformer
                else "Multilingual lexicon score plus keyword aspect matching.",
                "aspects": aspects,
                "improvement_signals": improvement_signals(text, aspects, label),
                "language": detect_language(row, text),
                "baseline_scores": probs,
                "method": "xlm-roberta-sentiment+aspect-lexicon"
                if use_transformer
                else "lexicon+aspect-lexicon",
            }
        )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the traditional NLP baseline over a JSONL manifest")
    parser.add_argument("--manifest", default="input/sample_reviews.jsonl")
    parser.add_argument("--output", default="output/baseline_results.jsonl")
    parser.add_argument("--lexicon-only", action="store_true", help="Skip transformer model loading")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.manifest))
    outputs = classify_rows(rows, use_transformer=not args.lexicon_only)
    write_jsonl(Path(args.output), outputs)
    print(f"Wrote {len(outputs)} baseline rows to {args.output}")


if __name__ == "__main__":
    main()
