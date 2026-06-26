# Issue Content Format

GitHub Issues will act as the content input layer for the Hugo site.

Each content issue uses one `kind:*` label to choose the target content type. Other labels become Hugo tags when the target type supports tags.

GitHub issue templates are available for each content type. Templates add the `kind:*` label only; add `status:publish` when the issue is ready to publish.

## Control Labels

Use exactly one of these labels on each content issue:

- `kind:post`
- `kind:blog`
- `kind:book`
- `kind:watch`
- `kind:podcast`
- `kind:cat-pic`

Control labels are not written into Hugo `tags`.

## Status Labels

Use one of these labels to control whether an issue is published:

- `status:publish`
- `status:deleted`

Only issues with both `kind:*` and `status:publish` are generated or updated. This lets you edit an issue as a draft without triggering a site rebuild on every save.

`status:deleted` removes the generated file for the issue, such as:

```text
content/post/issue-<number>.md
```

Closing an issue does not delete content. This is intentional, because issue close can also mean "finished" or "no longer discussing". Use `status:deleted` when the published content should disappear.

Remove `status:deleted`, add `status:publish`, and edit or relabel the issue again to recreate the content.

Do not use `status:publish` and `status:deleted` at the same time. If both are present, the Action fails before changing content.

## Issue Body Shape

An issue body may start with a YAML metadata block:

```markdown
---
date: 2026-06-25
summary: "Optional summary"
---

Markdown body starts here.
```

The issue title is used as the Hugo `title`.

If `date` is omitted, the issue creation date is used.

If `summary` is omitted for `kind:post`, the first plain-text paragraph is used as the summary.

## Main Post

Label:

```text
kind:post
status:publish
日记
```

Body:

```markdown
---
date: 2026-06-25
summary: "今天的一句话摘要。"
---

正文从这里开始。

## 小标题

继续写文章。
```

Output:

```text
content/post/issue-<number>.md
```

Generated front matter:

```yaml
title: "<issue title>"
date: 2026-06-25
summary: "今天的一句话摘要。"
tags: ["日记"]
github_issue: <number>
```

## Blog Link

Label:

```text
kind:blog
status:publish
随感
中文
```

Body:

```markdown
---
date: 2026-06-25
external_url: "https://example.com/article"
summary: "一句可选备注。"
---
```

Output:

```text
content/blogs/issue-<number>.md
```

Generated front matter:

```yaml
title: "<issue title>"
date: 2026-06-25
external_url: "https://example.com/article"
summary: "一句可选备注。"
tags: ["随感", "中文"]
github_issue: <number>
```

## Book

Label:

```text
kind:book
status:publish
```

Body:

```markdown
---
date: 2026-06-25
external_url: "https://weread.qq.com/web/reader/example"
cover: "https://example.com/book-cover.jpg"
author: "作者名"
category: "小说 / 喜欢"
---
```

Output:

```text
content/books/issue-<number>.md
```

Generated front matter:

```yaml
title: "<issue title>"
date: 2026-06-25
external_url: "https://weread.qq.com/web/reader/example"
cover: "https://example.com/book-cover.jpg"
author: "作者名"
category: "小说 / 喜欢"
github_issue: <number>
```

## Watch

Label:

```text
kind:watch
status:publish
```

Body:

```markdown
---
date: 2026-06-25
external_url: "https://movie.douban.com/subject/example/"
cover: "https://example.com/poster.jpg"
timeline: "[日]2026 年 1 月开播"
category: "剧情 / 喜欢"
---
```

Output:

```text
content/watches/issue-<number>.md
```

Generated front matter:

```yaml
title: "<issue title>"
date: 2026-06-25
external_url: "https://movie.douban.com/subject/example/"
cover: "https://example.com/poster.jpg"
timeline: "[日]2026 年 1 月开播"
category: "剧情 / 喜欢"
github_issue: <number>
```

## Podcast

Label:

```text
kind:podcast
status:publish
```

Body:

```markdown
---
date: 2026-06-25
external_url: "https://www.xiaoyuzhoufm.com/episode/example"
cover: "https://example.com/podcast-cover.jpg"
episode: "播客名"
category: "科技 / 喜欢"
---
```

Output:

```text
content/podcasts/issue-<number>.md
```

Generated front matter:

```yaml
title: "<issue title>"
date: 2026-06-25
external_url: "https://www.xiaoyuzhoufm.com/episode/example"
cover: "https://example.com/podcast-cover.jpg"
episode: "播客名"
category: "科技 / 喜欢"
github_issue: <number>
```

## Cat Pic

Cat pics publish into the Pics page without adding image files to this repository. Use GitHub issue attachments or other public image URLs.

Label:

```text
kind:cat-pic
status:publish
```

Body:

```markdown
---
date: 2026-06-25
cats: ["番茄", "葱白"]
---

今天的说明。

![番茄](https://github.com/user-attachments/assets/example-1)
![葱白](https://github.com/user-attachments/assets/example-2)
```

Output:

```text
content/pics/issue-<number>.md
```

Generated front matter:

```yaml
title: "<issue title>"
date: 2026-06-25
cats: ["番茄", "葱白"]
summary: "今天的说明。"
images: ["https://github.com/user-attachments/assets/example-1", "https://github.com/user-attachments/assets/example-2"]
github_issue: <number>
```

You may also provide images directly in metadata:

```markdown
---
date: 2026-06-25
images: ["https://example.com/cat-1.jpg", "https://example.com/cat-2.jpg"]
---
```

If both metadata `images` and Markdown image syntax are present, metadata `images` wins.

## Reserved Metadata Keys

These keys are reserved for the issue sync script:

- `date`
- `summary`
- `external_url`
- `cover`
- `author`
- `category`
- `timeline`
- `episode`
- `cats`

Unknown metadata keys may be preserved later, but should not be relied on until implemented.

## Publish Validation

When `status:publish` is present, the sync script validates required fields before writing Hugo content:

- `kind:post`: Markdown body content is required.
- `kind:blog`: `external_url` is required.
- `kind:book`: `cover`, `author`, and `category` are required.
- `kind:watch`: `cover`, `timeline`, and `category` are required.
- `kind:podcast`: `episode` and `category` are required.
- `kind:cat-pic`: at least one image URL is required, either in `images` metadata or Markdown image syntax.

If validation fails, the Action fails before publishing so the old online content remains unchanged.

## Cost Control Behavior

The publishing workflow skips the Hugo build and Pages publish steps when the issue event does not change generated source content. This covers cases such as editing an already deleted issue, or saving a published issue without changing the rendered Markdown.
