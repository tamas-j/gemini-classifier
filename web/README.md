# Web Demo

Next.js App Router frontend for the app-review classifier.

```bash
pnpm install
pnpm dev
```

Set `GEMINI_API_KEY` in `.env.local` or in Vercel for live LLM calls. Without a key, the classify route uses a lightweight local fallback so the interface remains testable.

The web baseline is cached for preset examples only. Run the full traditional NLP baseline from the project root:

```bash
python baseline.py --manifest input/sample_reviews.jsonl
```
