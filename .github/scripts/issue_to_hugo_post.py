#!/usr/bin/env python3
"""Convert a GitHub issue event into Hugo content."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


KIND_LABEL_PREFIX = "kind:"
CONTROL_LABEL_PREFIXES = ("kind:", "status:", "type:")
DELETE_LABEL = "status:deleted"

KIND_CONFIG: dict[str, dict[str, Any]] = {
    "post": {
        "section": "post",
        "metadata_keys": ("date", "summary"),
        "body": True,
        "tags": True,
    },
    "blog": {
        "section": "blogs",
        "metadata_keys": ("date", "external_url", "summary"),
        "body": False,
        "tags": True,
    },
    "book": {
        "section": "books",
        "metadata_keys": ("date", "external_url", "cover", "author", "category"),
        "body": False,
        "tags": False,
    },
    "watch": {
        "section": "watches",
        "metadata_keys": ("date", "external_url", "cover", "timeline", "category"),
        "body": False,
        "tags": False,
    },
    "podcast": {
        "section": "podcasts",
        "metadata_keys": ("date", "external_url", "cover", "episode", "category"),
        "body": False,
        "tags": False,
    },
}


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


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_list(values: list[Any]) -> str:
    return "[" + ", ".join(yaml_scalar(value) for value in values) + "]"


def front_matter_value(value: Any) -> str:
    if isinstance(value, list):
        return yaml_list(value)
    return yaml_scalar(value)


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
        if name:
            labels.append(name)
    return labels


def content_kind(issue: dict[str, Any]) -> str:
    kinds = [
        label[len(KIND_LABEL_PREFIX) :].strip()
        for label in label_names(issue)
        if label.lower().startswith(KIND_LABEL_PREFIX)
    ]

    if not kinds:
        return "post"

    unique_kinds = sorted(set(kinds))
    if len(unique_kinds) > 1:
        die(f"issue has multiple kind labels: {', '.join(unique_kinds)}")

    kind = unique_kinds[0]
    if kind == "cat-pic":
        die("kind:cat-pic is reserved for the Pics refactor and is not implemented yet")
    if kind not in KIND_CONFIG:
        die(f"unsupported kind label: kind:{kind}")
    return kind


def content_tags(issue: dict[str, Any]) -> list[str]:
    tags = []
    for label in label_names(issue):
        lowered = label.lower()
        if lowered.startswith(CONTROL_LABEL_PREFIXES):
            continue
        tags.append(label)
    return tags


def is_deleted(issue: dict[str, Any]) -> bool:
    return any(label.lower() == DELETE_LABEL for label in label_names(issue))


def parse_metadata_value(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [strip_quotes(part.strip()) for part in inner.split(",")]

    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    return strip_quotes(value)


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def split_metadata(body: str) -> tuple[dict[str, Any], str]:
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, body.strip()

    metadata: dict[str, Any] = {}
    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            die(f"invalid metadata line: {line}")
        key, raw_value = line.split(":", 1)
        metadata[key.strip()] = parse_metadata_value(raw_value)

    if closing_index is None:
        die("metadata block starts with --- but has no closing ---")

    markdown = "\n".join(lines[closing_index + 1 :]).strip()
    return metadata, markdown


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


def output_path(root_dir: Path, kind: str, issue_number: int) -> Path:
    section = KIND_CONFIG[kind]["section"]
    return root_dir / section / f"issue-{issue_number}.md"


def render_content(issue: dict[str, Any], kind: str) -> str:
    body = issue.get("body") or ""
    metadata, markdown = split_metadata(body.strip())
    config = KIND_CONFIG[kind]

    title = str(issue.get("title") or f"Issue #{issue['number']}")
    front_matter: dict[str, Any] = {
        "title": title,
        "date": metadata.get("date") or issue_date(issue["created_at"]),
    }

    for key in config["metadata_keys"]:
        if key == "date":
            continue
        if key in metadata:
            front_matter[key] = metadata[key]

    if kind == "post" and "summary" not in front_matter:
        front_matter["summary"] = plain_summary(markdown)

    if config["tags"]:
        front_matter["tags"] = content_tags(issue)

    front_matter["github_issue"] = issue["number"]
    front_matter["lastmod"] = issue_datetime(issue["updated_at"])

    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {front_matter_value(value)}")
    lines.extend(["---", ""])

    if config["body"] and markdown:
        lines.extend([markdown, ""])

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 3:
        die("usage: issue_to_hugo_post.py <github-event-json> <hugo-content-root>")

    event_path = Path(sys.argv[1])
    content_root = Path(sys.argv[2])
    issue = load_issue(event_path)
    kind = content_kind(issue)
    path = output_path(content_root, kind, int(issue["number"]))

    if is_deleted(issue):
        if path.exists():
            path.unlink()
            print(f"deleted {path}")
        else:
            print(f"already deleted {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_content(issue, kind), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
