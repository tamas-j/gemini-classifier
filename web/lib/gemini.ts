import { GoogleGenerativeAI } from "@google/generative-ai";

import { heuristicClassify } from "@/lib/heuristic";
import type { ClassificationResult } from "@/lib/types";

const systemInstruction = `<role>
You are a careful multilingual mobile app-review analyst for mobile finance apps.
</role>

<task>
You will receive one review per request. Classify the review into the structured-output schema used by the API.
Work only from the review text provided. The reviewer text is the sole source of truth.
</task>

<sentiment_labels>
Choose exactly one primary_label:
- very_negative: severe frustration, unusable app, repeated failures, account access problems, money blocked or missing, fraud/security panic, or angry complaint.
- negative: clear complaint or disappointment, but less severe than very_negative.
- neutral: mixed, factual, unclear, feature request without clear sentiment, or no strong sentiment.
- positive: clear satisfaction or praise.
- very_positive: enthusiastic praise, strong recommendation, delight, or "best app" style language.
</sentiment_labels>

<aspect_taxonomy>
Use only these aspects: ui, performance, support, transfers, fees, kyc, notifications, crashes, login, security, cards, rewards, other.
Extract every directly supported aspect, up to the schema limit. Use other only for important app-review content outside the listed categories.
</aspect_taxonomy>

<decision_guidelines>
- Do not invent app features, user requests, incidents, causes, or fixes not mentioned in the review.
- Prefer the strongest directly supported label, but do not upgrade severity merely because finance apps are high stakes.
- A crash, blocked login, locked account, missing money, fraud concern, or ignored urgent support request can justify very_negative.
- A single mild complaint without urgency is usually negative, not very_negative.
- Mixed praise and complaint is usually neutral unless one side clearly dominates.
- Feature requests with little emotion are usually neutral; requests attached to frustration can be negative.
- State both sides of ambiguity internally: the cost of overreacting is exaggerated severity, and the cost of underreacting is hiding a serious user problem.
</decision_guidelines>

<confidence_calibration>
confidence must be 0.0 to 1.0. Use 0.85+ only for clear direct cues, 0.60 to 0.84 for mostly clear reviews with minor ambiguity, and below 0.60 for unclear or unusable text.
</confidence_calibration>

<output_contract>
Return strict JSON with: primary_label, confidence, rationale, aspects, improvement_signals, language.
Extract up to five short improvement_signals. Return an empty list for pure praise with no improvement signal.
Write one short rationale grounded in decisive phrases or patterns. Do not translate the review or quote long passages.
</output_contract>`;

const responseSchema = {
  type: "object",
  properties: {
    primary_label: {
      type: "string",
      enum: ["very_negative", "negative", "neutral", "positive", "very_positive"],
    },
    confidence: { type: "number" },
    rationale: { type: "string" },
    aspects: {
      type: "array",
      items: {
        type: "string",
        enum: [
          "ui",
          "performance",
          "support",
          "transfers",
          "fees",
          "kyc",
          "notifications",
          "crashes",
          "login",
          "security",
          "cards",
          "rewards",
          "other",
        ],
      },
    },
    improvement_signals: {
      type: "array",
      items: { type: "string" },
    },
    language: { type: "string" },
  },
  required: ["primary_label", "confidence", "rationale", "aspects", "improvement_signals", "language"],
};

export async function classifyWithGemini(
  text: string,
  id?: string,
  requestApiKey?: string
): Promise<ClassificationResult> {
  const apiKey = requestApiKey || process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey) {
    return heuristicClassify(text, id);
  }

  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
    systemInstruction,
  });

  const result = await model.generateContent({
    contents: [{ role: "user", parts: [{ text }] }],
    generationConfig: {
      temperature: 0.2,
      responseMimeType: "application/json",
      responseSchema,
    },
  } as never);

  const raw = result.response.text();
  const parsed = JSON.parse(raw) as ClassificationResult;
  return {
    ...parsed,
    id,
    confidence: Number(parsed.confidence),
    method: process.env.GEMINI_MODEL || "gemini-2.5-flash",
  };
}
