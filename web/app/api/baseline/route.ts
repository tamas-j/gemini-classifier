import { NextResponse } from "next/server";

import baselineCache from "@/lib/baseline-cache.json";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const id = typeof body?.id === "string" ? body.id : "";

  if (id && id in baselineCache) {
    return NextResponse.json(baselineCache[id as keyof typeof baselineCache]);
  }

  return NextResponse.json({
    primary_label: "neutral",
    confidence: 0,
    rationale: "Baseline is cached for preset examples only in the Vercel demo.",
    aspects: [],
    improvement_signals: [],
    language: "unknown",
    method: "cached-presets-only",
    cached: false,
    unavailableReason: "Baseline shown for preset examples only. See benchmark.json for the full XLM-R + lexicon run.",
  });
}
