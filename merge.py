"""
Join a JSONL manifest with classify.py output (by id).

Typical use: you have sidecar metadata in the manifest (title, url, etc.) and
want one JSON file with both metadata and model labels.

Usage:
    uv run python merge.py --manifest input/manifest.jsonl --results output/results.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def load_results_by_id(path: Path, id_key: str = "id") -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in load_jsonl(path):
        iid = row.get(id_key)
        if isinstance(iid, str):
            out[iid] = row
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge manifest JSONL with classification results")
    parser.add_argument("--manifest", required=True, help="Original JSONL manifest")
    parser.add_argument("--results", default="output/results.jsonl", help="Output from classify.py")
    parser.add_argument("--output", default="output/merged.json", help="Pretty-printed JSON array")
    parser.add_argument("--id-key", default="id", dest="id_key", help="Join key field name")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    results_path = Path(args.results)
    out_path = Path(args.output)

    if not manifest_path.is_file():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if not results_path.is_file():
        raise SystemExit(f"Results not found: {results_path}")

    manifest = load_jsonl(manifest_path)
    by_id = load_results_by_id(results_path, args.id_key)

    merged: list[dict] = []
    for row in manifest:
        raw_id = row.get(args.id_key)
        sid = str(raw_id) if raw_id is not None else None
        if sid is None or sid not in by_id:
            merged.append({**row, "classification": None})
            continue
        r = by_id[sid]
        classification = {k: v for k, v in r.items() if k != args.id_key}
        merged.append({**row, "classification": classification})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(merged)} rows to {out_path}")


if __name__ == "__main__":
    main()
