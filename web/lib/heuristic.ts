import type { ClassificationResult, Sentiment } from "@/lib/types";

const positive = [
  "excellent",
  "fast",
  "great",
  "love",
  "perfect",
  "rápida",
  "excelente",
  "fácil",
  "schnell",
  "super",
  "parfait",
  "rapides",
  "rápido",
  "confiável",
];

const negative = [
  "crash",
  "crashing",
  "slow",
  "fee",
  "not replied",
  "crashea",
  "tarda",
  "comisión",
  "stürzt",
  "langsam",
  "gebühr",
  "plante",
  "lents",
  "frais",
  "fecha",
  "demora",
  "taxa",
];

const aspectTerms: Record<string, string[]> = {
  ui: ["layout", "screen", "interface", "interfaz", "oberfläche", "navigation", "tela"],
  performance: ["slow", "fast", "tarda", "rápida", "langsam", "schnell", "lents", "rapides", "demora", "rápido"],
  support: ["support", "soporte", "kundenservice", "assistance", "suporte"],
  transfers: ["transfer", "transfers", "transferencia", "überweisungen", "virements", "pix"],
  fees: ["fee", "fees", "comisión", "gebühr", "frais", "taxa"],
  notifications: ["notification", "notificaciones", "benachrichtigungen", "alertes", "notificações"],
  crashes: ["crash", "crashing", "crashea", "stürzt", "plante", "fecha"],
  login: ["login", "iniciar sesión", "connexion"],
  cards: ["card", "tarjeta", "karte", "carte", "cartão"],
};

export function heuristicClassify(text: string, id?: string): ClassificationResult {
  const lowered = text.toLowerCase();
  const pos = positive.filter((word) => lowered.includes(word)).length;
  const neg = negative.filter((word) => lowered.includes(word)).length;
  let label: Sentiment = "neutral";
  if (neg - pos >= 2) label = "very_negative";
  else if (neg > pos) label = "negative";
  else if (pos - neg >= 2) label = "very_positive";
  else if (pos > neg) label = "positive";

  const aspects = Object.entries(aspectTerms)
    .filter(([, terms]) => terms.some((term) => lowered.includes(term)))
    .map(([aspect]) => aspect);

  const language = lowered.includes("não") || lowered.includes("cartão")
    ? "pt"
    : lowered.includes("connexion") || lowered.includes("virements")
      ? "fr"
      : lowered.includes("über") || lowered.includes("gebühr")
        ? "de"
        : lowered.includes("transferencia") || lowered.includes("comisión")
          ? "es"
          : "en";

  return {
    id,
    primary_label: label,
    confidence: label === "neutral" ? 0.52 : Math.min(0.88, 0.56 + Math.abs(pos - neg) * 0.12),
    rationale: "Local fallback used because GEMINI_API_KEY is not configured for this demo environment.",
    aspects: aspects.length ? aspects : ["other"],
    improvement_signals: label === "negative" || label === "very_negative" ? [text.slice(0, 96)] : [],
    language,
    method: "local-fallback",
  };
}
