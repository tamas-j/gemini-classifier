"""Deterministic checks for prompt/schema alignment.

This does not replace model evals. It catches prompt hygiene regressions that
are cheap to verify before spending tokens on a live classification run.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from schema import Aspect, PrimaryLabel


REQUIRED_SECTIONS = [
    "role",
    "task",
    "sentiment_labels",
    "aspect_taxonomy",
    "decision_guidelines",
    "confidence_calibration",
    "output_contract",
]

DEFENSIVE_PATCH_SMELLS = [
    "never classify",
    "never mention",
    "always classify",
    "absolutely necessary",
    "do not answer",
    "point them to",
]


def literal_values(alias: object) -> list[str]:
    return list(alias.__args__)  # type: ignore[attr-defined]


def section_missing(prompt: str, section: str) -> bool:
    return not re.search(rf"<{section}>\s*.+?\s*</{section}>", prompt, flags=re.DOTALL)


def check_prompt(prompt: str, path: Path) -> list[str]:
    failures: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section_missing(prompt, section):
            failures.append(f"{path}: missing <{section}>...</{section}> section")

    for label in literal_values(PrimaryLabel):
        if label not in prompt:
            failures.append(f"{path}: schema label missing from prompt: {label}")

    for aspect in literal_values(Aspect):
        if aspect not in prompt:
            failures.append(f"{path}: schema aspect missing from prompt: {aspect}")

    lowered = prompt.lower()
    for smell in DEFENSIVE_PATCH_SMELLS:
        if smell in lowered:
            failures.append(f"{path}: review defensive absolute instruction: {smell!r}")

    return failures


def extract_web_prompt(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    match = re.search(r"const systemInstruction = `(?P<prompt>.*?)`;", source, flags=re.DOTALL)
    if not match:
        raise SystemExit(f"{path}: could not find systemInstruction template literal")
    return match.group("prompt")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check prompt hygiene and schema alignment")
    parser.add_argument("--prompt", default="prompts/app_reviews.md")
    parser.add_argument("--web-prompt", default="web/lib/gemini.ts")
    args = parser.parse_args()

    prompt_path = Path(args.prompt)
    web_path = Path(args.web_prompt)

    failures = check_prompt(prompt_path.read_text(encoding="utf-8"), prompt_path)
    failures.extend(check_prompt(extract_web_prompt(web_path), web_path))

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)

    print("Prompt contract checks passed.")


if __name__ == "__main__":
    main()
