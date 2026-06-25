#!/usr/bin/env python3
"""Normalize Hugo front matter before building."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any


TAG_LINE = re.compile(r"^tags:\s*(.*)$")
FRONT_MATTER_END = "---"


def parse_tags(raw: str) -> list[str] | None:
    value = raw.strip()
    if not value:
        return []

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        try:
            parsed: Any = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return [strip_quotes(part.strip()) for part in inner.split(",")]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed]
        return None

    return [value.strip().strip("'\"")]


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def render_tags(tags: list[str]) -> str:
    rendered = ", ".join('"' + tag.replace('"', '\\"') + '"' for tag in tags)
    return f"tags: [{rendered}]"


def clean_tags(tags: list[str]) -> list[str]:
    normalized = []
    for tag in tags:
        tag = tag.strip().strip("'\"")
        if not tag or "/" in tag:
            continue
        normalized.append(tag)
    return normalized


def parse_multiline_tags(lines: list[str], start_index: int) -> tuple[list[str], int]:
    tags = []
    index = start_index + 1
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == FRONT_MATTER_END:
            break
        if not stripped:
            index += 1
            continue
        if not line.startswith((" ", "\t", "-")) and ":" in line:
            break
        if stripped.startswith("-"):
            tags.append(strip_quotes(stripped[1:].strip()))
            index += 1
            continue
        break
    return tags, index


def normalize_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False

    changed = False
    index = 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == "---":
            break

        match = TAG_LINE.match(line)
        if not match:
            index += 1
            continue

        raw_tags = match.group(1)
        if raw_tags.strip():
            tags = parse_tags(raw_tags)
            next_index = index + 1
        else:
            tags, next_index = parse_multiline_tags(lines, index)

        if tags is None:
            index += 1
            continue

        normalized = clean_tags(tags)
        if normalized != tags:
            changed = True

        new_line = render_tags(normalized)
        if new_line != line or next_index != index + 1:
            lines[index:next_index] = [new_line]
            index += 1
            changed = True
            continue

        index += 1

    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"normalized {path}")

    return changed


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: normalize_hugo_content.py <content-root>", file=sys.stderr)
        sys.exit(1)

    content_root = Path(sys.argv[1])
    changed = False
    for path in content_root.rglob("*.md"):
        changed = normalize_file(path) or changed

    if not changed:
        print("content front matter already normalized")


if __name__ == "__main__":
    main()
