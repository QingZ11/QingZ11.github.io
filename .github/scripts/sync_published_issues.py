#!/usr/bin/env python3
"""Sync all currently published/deleted content issues into Hugo content."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


KINDS = {"kind:post", "kind:blog", "kind:book", "kind:watch", "kind:podcast", "kind:cat-pic"}
STATUSES = {"status:publish", "status:deleted"}


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


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


def issue_labels(issue: dict) -> set[str]:
    return {str(label.get("name", "")).strip().lower() for label in issue.get("labels", []) if label.get("name")}


def should_sync(issue: dict) -> bool:
    labels = issue_labels(issue)
    return bool(labels & KINDS) and bool(labels & STATUSES)


def list_issues(repo: str, token: str) -> list[dict]:
    api_base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    query = urllib.parse.urlencode({"state": "open", "per_page": "100"})
    url = f"{api_base}/repos/{repo}/issues?{query}"
    issues: list[dict] = []
    while url:
        data, link = github_get(url, token)
        if not isinstance(data, list):
            die("GitHub issues API returned an unexpected response")
        issues.extend(issue for issue in data if not issue.get("pull_request"))
        url = next_link(link)
    return issues


def run_converter(converter: Path, issue: dict, content_root: Path) -> None:
    event = {"issue": issue}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as event_file:
        json.dump(event, event_file, ensure_ascii=False)
        event_path = Path(event_file.name)
    try:
        subprocess.run([sys.executable, str(converter), str(event_path), str(content_root)], check=True)
    finally:
        event_path.unlink(missing_ok=True)


def sync_issues(issues: list[dict], content_root: Path) -> int:
    converter = Path(__file__).with_name("issue_to_hugo_post.py")
    syncable_issues = [issue for issue in issues if should_sync(issue)]
    print(f"syncing {len(syncable_issues)} content issues")

    for issue in sorted(syncable_issues, key=lambda item: int(item["number"])):
        labels = ", ".join(sorted(issue_labels(issue)))
        print(f"sync issue #{issue['number']}: {issue.get('title', '')} [{labels}]")
        run_converter(converter, issue, content_root)

    return len(syncable_issues)


def main() -> None:
    if len(sys.argv) != 3:
        die("usage: sync_published_issues.py <repo-owner/name> <hugo-content-root>")

    repo = sys.argv[1]
    content_root = Path(sys.argv[2])
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        die("GITHUB_TOKEN is required")

    sync_issues(list_issues(repo, token), content_root)


if __name__ == "__main__":
    main()
