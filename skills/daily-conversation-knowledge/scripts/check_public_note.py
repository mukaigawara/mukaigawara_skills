#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS = {
    "private product or organization name": re.compile(r"\b(?:mfloow|mflow)\b", re.I),
    "home directory path": re.compile(r"(?:/Users/|/home/|[A-Z]:\\Users\\)", re.I),
    "URL": re.compile(r"\b(?:https?|file)://", re.I),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "IPv4 address": re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"),
    "UUID": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        re.I,
    ),
    "issue or ticket identifier": re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b"),
    "credential assignment": re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|authorization)\s*[:=]",
        re.I,
    ),
    "credential-like token": re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{16,}|AKIA[A-Z0-9]{16})\b"
    ),
    "source file name": re.compile(
        r"\b[\w.-]+\.(?:c|cc|cpp|css|go|html|java|js|json|jsx|kt|mdx|php|plist|py|rb|rs|sh|sql|swift|toml|ts|tsx|vue|xml|ya?ml)\b",
        re.I,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reject a public note containing common private-data indicators."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--forbid-term",
        action="append",
        default=[],
        help="Additional literal term to reject; repeat for multiple terms.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        lines = args.path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        print(f"Could not read candidate: {error}")
        return 2

    patterns = dict(PATTERNS)
    for index, term in enumerate(args.forbid_term, start=1):
        if term:
            patterns[f"additional forbidden term {index}"] = re.compile(
                re.escape(term), re.I
            )

    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        for category, pattern in patterns.items():
            if pattern.search(line):
                findings.append((line_number, category))

    if findings:
        for line_number, category in findings:
            print(f"REJECTED line {line_number}: {category}")
        return 1

    print("Public-safety scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
