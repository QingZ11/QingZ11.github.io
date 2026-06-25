#!/usr/bin/env python3
"""Normalize Hugo front matter before building."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any


TAG_LINE = re.compile(r"^tags:\s*(.*)$")


def parse_tags(raw: str) -> list[str] | None:
    value = raw.strip()
    if not value:
        return []

    if value.startswith("[") and value.endswith("]"):
        try:
            parsed: Any = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed]
        return None

    return [value.strip().strip("'\"")]


def render_tags(tags: list[str]) -> str:
    rendered = ", ".join('"' + tag.replace('"', '\\"') + '"' for tag in tags)
    return f"tags: [{rendered}]"


def normalize_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False

    changed = False
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            break

        match = TAG_LINE.match(line)
        if not match:
            continue

        tags = parse_tags(match.group(1))
        if tags is None:
            continue

        normalized = []
        for tag in tags:
            tag = tag.strip()
            if not tag or tag == "/":
                changed = True
                continue
            normalized.append(tag)

        new_line = render_tags(normalized)
        if new_line != line:
            lines[index] = new_line
            changed = True

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
