#!/usr/bin/env python3
"""Local smoke tests for issue_to_hugo_post.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("issue_to_hugo_post.py")
NORMALIZER = Path(__file__).with_name("normalize_hugo_content.py")


def event(kind: str, number: int, title: str, body: str, labels: list[str]) -> dict:
    return {
        "issue": {
            "number": number,
            "title": title,
            "body": body,
            "created_at": "2026-06-25T01:02:03Z",
            "updated_at": "2026-06-25T04:05:06Z",
            "labels": [{"name": f"kind:{kind}"}] + [{"name": label} for label in labels],
        }
    }


def run_case(kind: str, expected_path: str, expected_bits: list[str], body: str, labels: list[str] | None = None) -> None:
    labels = labels or []
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        event_path = root / "event.json"
        content_root = root / "content"
        event_path.write_text(
            json.dumps(event(kind, 100 + len(kind), f"{kind.title()} Title", body, labels), ensure_ascii=False),
            encoding="utf-8",
        )

        subprocess.run(
            ["python3", str(SCRIPT), str(event_path), str(content_root)],
            check=True,
            text=True,
            capture_output=True,
        )

        output_path = content_root / expected_path
        assert output_path.exists(), f"missing output path: {output_path}"
        output = output_path.read_text(encoding="utf-8")
        for bit in expected_bits:
            assert bit in output, f"missing {bit!r} in:\n{output}"


def main() -> None:
    run_case(
        "post",
        "post/issue-104.md",
        ['title: "Post Title"', 'summary: "自定义摘要"', 'tags: ["日记"]', "正文内容"],
        "---\ndate: 2026-06-24\nsummary: 自定义摘要\n---\n\n正文内容",
        ["日记"],
    )
    run_case(
        "blog",
        "blogs/issue-104.md",
        ['external_url: "https://example.com/article"', 'tags: ["随感", "中文"]'],
        "---\nexternal_url: https://example.com/article\nsummary: 一句话备注\n---",
        ["随感", "中文"],
    )
    run_case(
        "book",
        "books/issue-104.md",
        ['cover: "https://example.com/book.jpg"', 'author: "作者名"', 'category: "小说 / 喜欢"'],
        "---\ncover: https://example.com/book.jpg\nauthor: 作者名\ncategory: 小说 / 喜欢\n---",
    )
    run_case(
        "watch",
        "watches/issue-105.md",
        ['timeline: "[日]2026 年 1 月开播"', 'category: "剧情 / 喜欢"'],
        "---\ntimeline: [日]2026 年 1 月开播\ncategory: 剧情 / 喜欢\n---",
    )
    run_case(
        "podcast",
        "podcasts/issue-107.md",
        ['episode: "播客名"', 'category: "科技 / 喜欢"'],
        "---\nepisode: 播客名\ncategory: 科技 / 喜欢\n---",
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        content_root = Path(temp_dir) / "content"
        post_path = content_root / "post" / "bad-tags.md"
        post_path.parent.mkdir(parents=True)
        post_path.write_text(
            "---\ntitle: Bad Tags\ndate: 2026-06-25\ntags: ['日记', '', '/']\n---\n\nBody\n",
            encoding="utf-8",
        )
        subprocess.run(["python3", str(NORMALIZER), str(content_root)], check=True, text=True, capture_output=True)
        output = post_path.read_text(encoding="utf-8")
        assert 'tags: ["日记"]' in output, output
    print("issue_to_hugo_post.py smoke tests passed")


if __name__ == "__main__":
    main()
