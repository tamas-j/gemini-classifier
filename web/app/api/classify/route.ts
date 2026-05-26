import { NextRequest, NextResponse } from "next/server";

import { classifyWithGemini } from "@/lib/gemini";

const buckets = new Map<string, { count: number; resetAt: number }>();
const WINDOW_MS = 60_000;
const LIMIT = 12;

function clientKey(request: NextRequest) {
  return (
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    request.headers.get("x-real-ip") ||
    "local"
  );
}

function rateLimited(request: NextRequest) {
  const key = clientKey(request);
  const now = Date.now();
  const bucket = buckets.get(key);
  if (!bucket || bucket.resetAt < now) {
    buckets.set(key, { count: 1, resetAt: now + WINDOW_MS });
    return false;
  }
  bucket.count += 1;
  return bucket.count > LIMIT;
}

export async function POST(request: NextRequest) {
  if (rateLimited(request)) {
    return NextResponse.json({ error: "Rate limit exceeded" }, { status: 429 });
  }

  const body = await request.json().catch(() => null);
  const text = typeof body?.text === "string" ? body.text.trim() : "";
  const id = typeof body?.id === "string" ? body.id : undefined;
  const requestApiKey = typeof body?.apiKey === "string" ? body.apiKey.trim() : undefined;

  if (!text) {
    return NextResponse.json({ error: "Review text is required" }, { status: 400 });
  }

  try {
    const result = await classifyWithGemini(text, id, requestApiKey);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Classification failed" },
      { status: 500 }
    );
  }
}
