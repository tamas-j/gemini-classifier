export type Sentiment =
  | "very_negative"
  | "negative"
  | "neutral"
  | "positive"
  | "very_positive";

export type ClassificationResult = {
  id?: string;
  primary_label: Sentiment;
  confidence: number;
  rationale: string;
  aspects: string[];
  improvement_signals: string[];
  language: string;
  method?: string;
  cached?: boolean;
  unavailableReason?: string;
};

export type SampleReview = {
  id: string;
  label: string;
  app: string;
  lang: string;
  text: string;
};
