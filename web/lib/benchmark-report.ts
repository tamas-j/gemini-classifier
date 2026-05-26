export const benchmarkReport = {
  n: 100,
  note: "Real public app-store reviews from the archive. Labels are bootstrap labels from the prior review pipeline, so refresh with a human-reviewed holdout before publishing final claims.",
  pipelines: {
    gemini: {
      name: "Cached LLM rubric",
      sentimentAccuracy: 1.0,
      macroF1: 1.0,
      aspectPrecision: 1.0,
      aspectRecall: 1.0,
      aspectF1: 1.0,
    },
    baseline: {
      name: "XLM-R + lexicon",
      sentimentAccuracy: 0.2,
      macroF1: 0.163,
      aspectPrecision: 0.645,
      aspectRecall: 0.629,
      aspectF1: 0.637,
    },
  },
  languages: [
    { lang: "de", geminiAccuracy: 1.0, baselineAccuracy: 0.167, n: 6 },
    { lang: "en", geminiAccuracy: 1.0, baselineAccuracy: 0.196, n: 92 },
    { lang: "fr", geminiAccuracy: 1.0, baselineAccuracy: 0.5, n: 2 },
  ],
};
