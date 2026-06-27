#!/usr/bin/env python3
"""Convert a GitHub issue event into Hugo content."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request


KIND_LABEL_PREFIX = "kind:"
CONTROL_LABEL_PREFIXES = ("kind:", "status:", "type:")
DELETE_LABEL = "status:deleted"
PUBLISH_LABEL = "status:publish"

REQUIRED_METADATA: dict[str, tuple[str, ...]] = {
    "blog": ("external_url",),
    "book": ("cover", "author", "category"),
    "watch": ("cover", "timeline", "category"),
    "podcast": ("episode", "category"),
}

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
    "cat-pic": {
        "section": "pics",
        "metadata_keys": ("date", "cats", "summary"),
        "body": True,
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


def configured_author_logins() -> set[str]:
    raw = os.environ.get("BLOG_AUTHOR_LOGINS", "")
    return {login.strip().lower() for login in raw.split(",") if login.strip()}


def github_get(url: str, token: str) -> tuple[object, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request) as response:
        data = json.load(response)
        link = response.headers.get("Link")
    return data, link


def next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">")
        if start != -1 and end != -1 and end > start:
            return section[start + 1 : end]
    return None


def list_issue_comments(issue: dict[str, Any]) -> list[dict[str, Any]]:
    fixture_comments = issue.get("_comments")
    if isinstance(fixture_comments, list):
        return fixture_comments

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return []

    api_base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    issue_number = int(issue["number"])
    query = urllib.parse.urlencode({"per_page": "100"})
    url = f"{api_base}/repos/{repo}/issues/{issue_number}/comments?{query}"
    comments: list[dict[str, Any]] = []
    while url:
        data, link = github_get(url, token)
        if not isinstance(data, list):
            die("GitHub issue comments API returned an unexpected response")
        comments.extend(data)
        url = next_link(link)
    return comments


def author_comment_bodies(issue: dict[str, Any]) -> list[str]:
    author_logins = configured_author_logins()
    if not author_logins:
        return []

    bodies: list[str] = []
    comments = sorted(list_issue_comments(issue), key=lambda item: str(item.get("created_at", "")))
    for comment in comments:
        user = comment.get("user") or {}
        login = str(user.get("login", "")).strip().lower()
        user_type = str(user.get("type", "")).strip().lower()
        body = str(comment.get("body") or "").strip()
        if not body or not login:
            continue
        if user_type == "bot":
            continue
        if login not in author_logins:
            continue
        bodies.append(body)
    return bodies


def combine_markdown_parts(parts: list[str]) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return "\n\n".join(cleaned)


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


def validate_status_labels(issue: dict[str, Any]) -> None:
    statuses = sorted({label.lower() for label in label_names(issue) if label.lower().startswith("status:")})
    supported_statuses = {PUBLISH_LABEL, DELETE_LABEL}
    unsupported = [status for status in statuses if status not in supported_statuses]
    if unsupported:
        die(f"unsupported status label: {', '.join(unsupported)}")
    if PUBLISH_LABEL in statuses and DELETE_LABEL in statuses:
        die("issue cannot have both status:publish and status:deleted")


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


def content_image_urls(markdown: str) -> list[str]:
    urls: list[str] = []
    patterns = (
        r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)",
        r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>",
        r"https?://[^\s<>\")']+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s<>\")']*)?",
        r"https://github\.com/user-attachments/assets/[A-Za-z0-9_-]+",
    )
    for pattern in patterns:
        for match in re.findall(pattern, markdown, flags=re.IGNORECASE):
            url = match.strip()
            if url and url not in urls:
                urls.append(url)
    return urls


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(is_present(item) for item in value)
    return True


def validate_content(kind: str, metadata: dict[str, Any], markdown: str) -> None:
    missing = [key for key in REQUIRED_METADATA.get(kind, ()) if not is_present(metadata.get(key))]
    if missing:
        die(f"kind:{kind} missing required metadata: {', '.join(missing)}")

    if kind == "post" and not markdown.strip():
        die("kind:post requires Markdown body content")

    if kind == "cat-pic":
        images = metadata.get("images") or content_image_urls(markdown)
        if not images:
            die("kind:cat-pic requires image URLs in metadata images, Markdown image syntax, HTML img src, or plain image URLs")


def output_path(root_dir: Path, kind: str, issue_number: int) -> Path:
    section = KIND_CONFIG[kind]["section"]
    return root_dir / section / f"issue-{issue_number}.md"


def render_content(issue: dict[str, Any], kind: str) -> str:
    body = issue.get("body") or ""
    metadata, markdown = split_metadata(body.strip())
    config = KIND_CONFIG[kind]
    full_markdown = markdown
    if config["body"]:
        full_markdown = combine_markdown_parts([markdown, *author_comment_bodies(issue)])

    validate_content(kind, metadata, full_markdown)

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
        front_matter["summary"] = plain_summary(full_markdown)

    if kind == "cat-pic":
        images = metadata.get("images") or content_image_urls(full_markdown)
        front_matter["images"] = images
        if "summary" not in front_matter:
            front_matter["summary"] = plain_summary(full_markdown)

    if config["tags"]:
        front_matter["tags"] = content_tags(issue)

    front_matter["github_issue"] = issue["number"]
    front_matter["lastmod"] = issue_datetime(issue["updated_at"])

    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {front_matter_value(value)}")
    lines.extend(["---", ""])

    if config["body"] and full_markdown:
        lines.extend([full_markdown, ""])

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 3:
        die("usage: issue_to_hugo_post.py <github-event-json> <hugo-content-root>")

    event_path = Path(sys.argv[1])
    content_root = Path(sys.argv[2])
    issue = load_issue(event_path)
    validate_status_labels(issue)
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
