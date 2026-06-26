#!/usr/bin/env python3
"""Local smoke tests for issue_to_hugo_post.py."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("issue_to_hugo_post.py")
NORMALIZER = Path(__file__).with_name("normalize_hugo_content.py")
SYNC_SCRIPT = Path(__file__).with_name("sync_published_issues.py")


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


def run_script(event_path: Path, content_root: Path) -> None:
    subprocess.run(
        ["python3", str(SCRIPT), str(event_path), str(content_root)],
        check=True,
        text=True,
        capture_output=True,
    )


def run_script_expect_failure(event_path: Path, content_root: Path, expected_error: str) -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(event_path), str(content_root)],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0, "script should fail"
    assert expected_error in result.stderr, result.stderr


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

        run_script(event_path, content_root)

        output_path = content_root / expected_path
        assert output_path.exists(), f"missing output path: {output_path}"
        output = output_path.read_text(encoding="utf-8")
        for bit in expected_bits:
            assert bit in output, f"missing {bit!r} in:\n{output}"


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_published_issues", SYNC_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    run_case(
        "post",
        "post/issue-104.md",
        ['title: "Post Title"', 'summary: "自定义摘要"', 'tags: ["日记"]', "正文内容"],
        "---\ndate: 2026-06-24\nsummary: 自定义摘要\n---\n\n正文内容",
        ["status:publish", "日记"],
    )
    run_case(
        "blog",
        "blogs/issue-104.md",
        ['external_url: "https://example.com/article"', 'tags: ["随感", "中文"]'],
        "---\nexternal_url: https://example.com/article\nsummary: 一句话备注\n---",
        ["status:publish", "随感", "中文"],
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
        ['cover: "https://example.com/watch.jpg"', 'timeline: "[日]2026 年 1 月开播"', 'category: "剧情 / 喜欢"'],
        "---\ncover: https://example.com/watch.jpg\ntimeline: [日]2026 年 1 月开播\ncategory: 剧情 / 喜欢\n---",
    )
    run_case(
        "podcast",
        "podcasts/issue-107.md",
        ['episode: "播客名"', 'category: "科技 / 喜欢"'],
        "---\nepisode: 播客名\ncategory: 科技 / 喜欢\n---",
    )
    run_case(
        "cat-pic",
        "pics/issue-107.md",
        [
            'cats: ["番茄", "葱白"]',
            'images: ["https://github.com/user-attachments/assets/cat-1", "https://example.com/cat-2.jpg"]',
            "今天的说明。",
        ],
        "---\ndate: 2026-06-24\ncats: [番茄, 葱白]\n---\n\n今天的说明。\n\n![番茄](https://github.com/user-attachments/assets/cat-1)\n![葱白](https://example.com/cat-2.jpg)",
        ["status:publish"],
    )
    run_case(
        "cat-pic",
        "pics/issue-107.md",
        ['images: ["https://github.com/user-attachments/assets/cat-html"]'],
        "---\ndate: 2026-06-24\n---\n\n<img width=\"100\" alt=\"番茄\" src=\"https://github.com/user-attachments/assets/cat-html\">",
        ["status:publish"],
    )
    run_case(
        "cat-pic",
        "pics/issue-107.md",
        ['images: ["https://github.com/user-attachments/assets/cat-plain"]'],
        "---\ndate: 2026-06-24\n---\n\nhttps://github.com/user-attachments/assets/cat-plain",
        ["status:publish"],
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        content_root = Path(temp_dir) / "content"
        post_path = content_root / "post" / "bad-tags.md"
        post_path.parent.mkdir(parents=True)
        post_path.write_text(
            "---\ntitle: Bad Tags\ndate: 2026-06-25\ntags: ['日记', '', '/', '/post/202606-1/']\n---\n\nBody\n",
            encoding="utf-8",
        )
        subprocess.run(["python3", str(NORMALIZER), str(content_root)], check=True, text=True, capture_output=True)
        output = post_path.read_text(encoding="utf-8")
        assert 'tags: ["日记"]' in output, output
    with tempfile.TemporaryDirectory() as temp_dir:
        content_root = Path(temp_dir) / "content"
        post_path = content_root / "post" / "bad-multiline-tags.md"
        post_path.parent.mkdir(parents=True)
        post_path.write_text(
            "---\ntitle: Bad Multiline Tags\ndate: 2026-06-25\ntags:\n  - 日记\n  - \n  - /\n  - /post/202606-1/\n---\n\nBody\n",
            encoding="utf-8",
        )
        subprocess.run(["python3", str(NORMALIZER), str(content_root)], check=True, text=True, capture_output=True)
        output = post_path.read_text(encoding="utf-8")
        assert 'tags: ["日记"]' in output, output
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        event_path = root / "event.json"
        content_root = root / "content"
        event_path.write_text(
            json.dumps(event("post", 200, "Deleted Post", "Body", ["日记"]), ensure_ascii=False),
            encoding="utf-8",
        )
        run_script(event_path, content_root)
        output_path = content_root / "post" / "issue-200.md"
        assert output_path.exists(), "post should be created before deletion"

        event_path.write_text(
            json.dumps(event("post", 200, "Deleted Post", "Body", ["日记", "status:deleted"]), ensure_ascii=False),
            encoding="utf-8",
        )
        run_script(event_path, content_root)
        assert not output_path.exists(), "status:deleted should remove the generated post"
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        event_path = root / "event.json"
        content_root = root / "content"
        event_path.write_text(
            json.dumps(event("blog", 300, "Broken Blog", "---\nsummary: 缺链接\n---", ["status:publish"]), ensure_ascii=False),
            encoding="utf-8",
        )
        run_script_expect_failure(event_path, content_root, "kind:blog missing required metadata: external_url")
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        event_path = root / "event.json"
        content_root = root / "content"
        event_path.write_text(
            json.dumps(event("cat-pic", 301, "Broken Cat Pic", "---\ndate: 2026-06-24\n---\n\n没有图片", ["status:publish"]), ensure_ascii=False),
            encoding="utf-8",
        )
        run_script_expect_failure(event_path, content_root, "kind:cat-pic requires image URLs")
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        event_path = root / "event.json"
        content_root = root / "content"
        event_path.write_text(
            json.dumps(event("post", 302, "Conflicting Status", "Body", ["status:publish", "status:deleted"]), ensure_ascii=False),
            encoding="utf-8",
        )
        run_script_expect_failure(event_path, content_root, "issue cannot have both status:publish and status:deleted")
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        event_path = root / "event.json"
        content_root = root / "content"
        event_path.write_text(
            json.dumps(event("post", 303, "Unknown Status", "Body", ["status:archived"]), ensure_ascii=False),
            encoding="utf-8",
        )
        run_script_expect_failure(event_path, content_root, "unsupported status label: status:archived")
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        content_root = root / "content"

        fixture = [
            event("post", 401, "Batch Post", "Batch body", ["status:publish"])["issue"],
            event("post", 402, "Draft Post", "Draft body", [])["issue"],
            event("cat-pic", 403, "Batch Cat", "![cat](https://github.com/user-attachments/assets/batch-cat)", ["status:publish"])["issue"],
        ]
        synced_count = load_sync_module().sync_issues(fixture, content_root)

        assert synced_count == 2, "only published/deleted content issues should sync"
        assert (content_root / "post" / "issue-401.md").exists(), "published post should sync"
        assert not (content_root / "post" / "issue-402.md").exists(), "draft post should not sync"
        assert (content_root / "pics" / "issue-403.md").exists(), "published cat pic should sync"
    print("issue_to_hugo_post.py smoke tests passed")


if __name__ == "__main__":
    main()
