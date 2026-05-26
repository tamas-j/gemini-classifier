"""
Classify each row in a JSONL manifest with Google Gemini (structured JSON).

Reads one JSON object per line; each row must include an id and a text field
(configurable). Writes checkpointed results to output/results.jsonl after each
successful call so runs can resume.

Usage:
    uv sync
    copy .env.example to .env and set GEMINI_API_KEY
    uv run python classify.py --manifest input/manifest.jsonl
    uv run python classify.py --model gemini-2.5-flash --start 0 --end 5
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from schema import ClassificationOutput, response_json_schema

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MANIFEST = "input/manifest.jsonl"
DEFAULT_PROMPT = "prompts/system.md"
DEFAULT_OUTPUT = "output/results.jsonl"
DEFAULT_ID_KEY = "id"
DEFAULT_TEXT_KEY = "text"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
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


def load_results_index(path: Path) -> dict[str, dict]:
    """Map id -> last written record (successful classifications only)."""
    by_id: dict[str, dict] = {}
    if not path.exists():
        return by_id
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            iid = obj.get("id")
            if isinstance(iid, str):
                by_id[iid] = obj
    return by_id


def write_results_ordered(
    manifest: list[dict],
    by_id: dict[str, dict],
    path: Path,
    id_key: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in manifest:
            iid = row.get(id_key)
            if iid is None or str(iid) not in by_id:
                continue
            f.write(json.dumps(by_id[str(iid)], ensure_ascii=False) + "\n")


def classify_one(
    client: genai.Client,
    model: str,
    system_instruction: str,
    text: str,
    temperature: float,
) -> ClassificationOutput:
    schema = response_json_schema()
    response = client.models.generate_content(
        model=model,
        contents=text,
        config={
            "system_instruction": system_instruction,
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        },
    )
    raw = response.text
    if not raw:
        raise RuntimeError("Empty response text from model")
    return ClassificationOutput.model_validate_json(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini structured classification over JSONL")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="Path to JSONL manifest")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="System prompt file (markdown)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSONL path")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model id")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--id-key", default=DEFAULT_ID_KEY, dest="id_key", help="Manifest field for row id")
    parser.add_argument("--text-key", default=DEFAULT_TEXT_KEY, dest="text_key", help="Manifest field for document text")
    parser.add_argument("--start", type=int, default=0, help="Start index (inclusive)")
    parser.add_argument("--end", type=int, default=None, help="End index (exclusive)")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls")
    parser.add_argument("--force", action="store_true", help="Re-classify even if id is already in output")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment or .env file."
        )

    manifest_path = Path(args.manifest)
    prompt_path = Path(args.prompt)
    output_path = Path(args.output)

    if not manifest_path.is_file():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    manifest = load_jsonl(manifest_path)
    subset = manifest[args.start : args.end]

    system_instruction = prompt_path.read_text(encoding="utf-8")
    by_id = load_results_index(output_path)
    if args.force:
        for row in subset:
            iid = row.get(args.id_key)
            if iid is not None:
                by_id.pop(str(iid), None)

    print(f"Classifying {len(subset)} rows with {args.model}")
    print(f"Already completed (resume cache): {len(by_id)}")

    client = genai.Client(api_key=api_key)
    errors: list[str] = []

    for i, row in enumerate(subset):
        iid = row.get(args.id_key)
        text = row.get(args.text_key)
        if iid is None:
            print(f"  [{i + 1}] SKIP row missing {args.id_key!r}")
            continue
        sid = str(iid)
        if sid in by_id and not args.force:
            continue
        if text is None:
            print(f"  [{i + 1}] SKIP {sid} missing {args.text_key!r}")
            continue
        if not isinstance(text, str):
            text = str(text)

        print(f"  [{i + 1}/{len(subset)}] id={sid}...", end=" ", flush=True)
        try:
            result = classify_one(
                client,
                args.model,
                system_instruction,
                text,
                args.temperature,
            )
            record = {"id": sid, **result.model_dump()}
            by_id[sid] = record
            print(f"label={result.primary_label} conf={result.confidence:.2f}")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append(sid)

        write_results_ordered(manifest, by_id, output_path, args.id_key)

        if i < len(subset) - 1:
            time.sleep(args.delay)

    print(f"\nDone. Cached {len(by_id)} rows, {len(errors)} errors in this run.")
    if errors:
        print(f"Error ids: {errors}")


if __name__ == "__main__":
    main()
