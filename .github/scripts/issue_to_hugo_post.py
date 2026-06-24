#!/usr/bin/env python3
"""Convert a GitHub issue event into a Hugo Markdown post."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CONTROL_LABEL_PREFIXES = ("status:", "type:", "kind:")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def load_issue(event_path: Path) -> dict[str, Any]:
    with event_path.open(encoding="utf-8") as event_file:
        event = json.load(event_file)

    issue = event.get("issue")
    if not issue:
        die("this workflow must be triggered by an issue event")

    if issue.get("pull_request"):
        die("pull request issues are ignored")

    return issue


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_string_list(values: list[str]) -> str:
    return "[" + ", ".join(yaml_string(value) for value in values) + "]"


def issue_date(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.date().isoformat()


def issue_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.isoformat()


def label_names(issue: dict[str, Any]) -> list[str]:
    labels = []
    for label in issue.get("labels", []):
        name = str(label.get("name", "")).strip()
        if not name:
            continue
        if name.lower().startswith(CONTROL_LABEL_PREFIXES):
            continue
        labels.append(name)
    return labels


def plain_summary(markdown: str) -> str:
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("#", "!", "|", "```", ">", "- ", "* ")):
            continue
        line = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"[`*_~>#-]+", "", line).strip()
        if line:
            return line[:140]
    return ""


def post_body(issue: dict[str, Any]) -> str:
    body = issue.get("body") or ""
    body = body.strip()
    if body:
        return body + "\n"
    return ""


def render_post(issue: dict[str, Any]) -> str:
    body = post_body(issue)
    title = str(issue.get("title") or f"Issue #{issue['number']}")
    summary = plain_summary(body)
    tags = label_names(issue)

    front_matter = [
        "---",
        f"title: {yaml_string(title)}",
        f"date: {issue_date(issue['created_at'])}",
        f"lastmod: {yaml_string(issue_datetime(issue['updated_at']))}",
        f"summary: {yaml_string(summary)}",
        f"tags: {yaml_string_list(tags)}",
        f"github_issue: {issue['number']}",
        "---",
        "",
    ]

    return "\n".join(front_matter) + body


def main() -> None:
    if len(sys.argv) != 3:
        die("usage: issue_to_hugo_post.py <github-event-json> <hugo-section-dir>")

    event_path = Path(sys.argv[1])
    section_dir = Path(sys.argv[2])
    issue = load_issue(event_path)

    section_dir.mkdir(parents=True, exist_ok=True)
    post_path = section_dir / f"issue-{issue['number']}.md"
    post_path.write_text(render_post(issue), encoding="utf-8")
    print(post_path)


if __name__ == "__main__":
    main()
