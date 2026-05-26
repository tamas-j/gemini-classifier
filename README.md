# LLM Classifier: App Review Sentiment + Topic Analysis

Portfolio-ready demo of a multilingual app-review analysis pipeline. It compares an LLM classifier against a traditional NLP baseline on public app-store reviews, then exposes the workflow through a Next.js demo.

[Live demo: add Vercel URL after deploy](#web-demo) · [GitHub repo](https://github.com/tamas-j/llm-classifier)

## What It Does

Given a mobile finance app review, the project extracts:

- sentiment on a 5-point scale
- product areas mentioned, such as fees, login, transfers, support, security, or UI
- short improvement signals
- language, confidence, and a rationale

The Python pipeline handles reproducible batch classification and benchmarking. The web app gives reviewers an interactive single-review and small-batch demo.

## Current Status

This is ready as an open portfolio repo with one important evaluation caveat: the committed benchmark labels are bootstrap labels from a prior review pipeline, not a completed human-labelled holdout. The benchmark machinery is real and reproducible, but the headline LLM score should be treated as a demo result until the holdout is manually reviewed or rebuilt with a stronger labelling process.

## Results

Run:

```bash
python prompt_contract.py
python benchmark.py --skip-llm --skip-baseline --lexicon-only
```

Current bootstrap benchmark:

| Pipeline | n | Sentiment accuracy | Macro F1 | Aspect precision | Aspect recall | Aspect F1 |
|---|---:|---:|---:|---:|---:|---:|
| Cached LLM/rubric output | 100 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| XLM-R sentiment + aspect lexicon | 100 | 0.200 | 0.163 | 0.645 | 0.629 | 0.637 |

| Language | LLM acc | Baseline acc | LLM F1 | Baseline F1 | n |
|---|---:|---:|---:|---:|---:|
| de | 1.000 | 0.167 | 0.400 | 0.100 | 6 |
| en | 1.000 | 0.196 | 1.000 | 0.161 | 92 |
| fr | 1.000 | 0.500 | 0.400 | 0.200 | 2 |

Why the LLM line is perfect: the current cache mirrors the bootstrap labels so the benchmark flow can run without API keys. Before making public accuracy claims, replace `input/sample_reviews_gemini_cache.jsonl` with a real Gemini Flash run over a reviewed holdout.

## Dataset

The committed dataset contains **1,350 public Google Play and iTunes reviews** for Wise, Remitly, WorldRemit, Xoom, and Revolut.

- Date range: 2024-05-14 to 2026-04-21
- Platforms: 1,000 Android reviews, 350 iOS reviews
- Countries: 1,100 US, 150 DE, 50 GB, 50 FR
- Benchmark subset: 100 bootstrap-labelled rows

The dataset is intentionally public and reproducible from committed JSONL files. It is not client data.

## Quickstart

```bash
uv sync
uv run python prompt_contract.py
uv run python baseline.py --manifest input/sample_reviews.jsonl --lexicon-only
uv run python benchmark.py --skip-llm --skip-baseline --lexicon-only
```

To run live LLM classification:

```bash
copy .env.example .env
uv run python classify.py --manifest input/sample_reviews.jsonl --prompt prompts/app_reviews.md
```

Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in `.env`.

The original generic classifier flow is still available:

```bash
uv run python classify.py --manifest input/manifest.jsonl --prompt prompts/system.md
```

## Web Demo

```bash
cd web
pnpm install
pnpm dev
```

Open `http://127.0.0.1:3000`.

The web app supports:

- preset real reviews
- custom single-review classification
- small-batch processing, currently capped at 10 reviews
- optional Gemini key entry in the UI
- cached baseline comparison for preset examples

For production deployment, set `GEMINI_API_KEY` as a server-side Vercel environment variable. Do not commit `.env.local`.

## What Runs Where

| Capability | Python CLI | Web app |
|---|---|---|
| Gemini/LLM classification | Live with `GEMINI_API_KEY` | Live with env key or user-provided key |
| Traditional baseline | Real Python processing via `baseline.py` | Cached preset outputs only |
| Bulk processing | JSONL-scale batch jobs | LLM-only small batches, max 10 reviews |
| Benchmark report | Real metric computation | Static headline numbers from `web/lib/benchmark-report.ts` |

## Architecture

| Path | Role |
|---|---|
| `classify.py` | Resume-safe Gemini JSONL classifier. |
| `schema.py` | Pydantic v2 structured-output schema. |
| `prompts/app_reviews.md` | Multilingual app-review classification prompt. |
| `prompts/system.md` | Original generic starter prompt. |
| `baseline.py` | Traditional NLP baseline with XLM-R support and lexicon fallback. |
| `benchmark.py` | Sentiment and aspect benchmark harness. |
| `prompt_contract.py` | Prompt/schema hygiene checks. |
| `scripts/fetch_reviews.py` | Optional live Google Play review fetcher. |
| `scripts/import_ripple_reviews.py` | Local archive importer used to build the committed sample files. |
| `input/sample_reviews.jsonl` | Public review sample. |
| `input/sample_reviews_labels.jsonl` | Bootstrap benchmark labels. |
| `input/sample_reviews_gemini_cache.jsonl` | Cached LLM-shaped benchmark output. |
| `web/` | Next.js App Router demo. |

## Replacing the Bootstrap Benchmark

To make the benchmark publishable as an accuracy claim:

1. Create a human-reviewed holdout with `id`, `primary_label`, `aspects`, and `language`.
2. Run Gemini Flash over exactly that holdout.
3. Run the baseline over the same rows.
4. Run `benchmark.py` and update `output/benchmark.json`, the README table, and `web/lib/benchmark-report.ts`.

## Using Your Own Reviews

Create a JSONL file:

```json
{"id": "row-1", "text": "The app is slow after login.", "lang": "en"}
```

Run:

```bash
uv run python classify.py --manifest input/your_reviews.jsonl --prompt prompts/app_reviews.md --output output/your_gemini.jsonl
uv run python baseline.py --manifest input/your_reviews.jsonl --output output/your_baseline.jsonl
```

For benchmarking, provide labels with `id`, `primary_label`, `aspects`, and `language`.

## Privacy And Safety

- No client data is included.
- No API keys are committed.
- `output/`, `.env`, `.env.local`, and Python cache files are ignored.
- The web demo rate-limits classify requests to reduce accidental API spend.

## Acknowledgments

The batch LLM classification loop is inspired by Andrej Karpathy's public jobs-classification project: [github.com/karpathy/jobs](https://github.com/karpathy/jobs). This repo adapts that simple structured-output pattern to app-review sentiment and topic analysis.
