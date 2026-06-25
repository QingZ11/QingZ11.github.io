---
title: "更新博客主题 08.08"
date: 2024-08-08
summary: "Hugo 远比我想的复杂，我远比我想的更不喜欢钻研。"
tags: ["日常记录", "hugo"]
---

本来打算花 1 个小时更新下主题，然后再更新下博客，结果从八号到九号，横跨了了一个零点和一点，到现在才弄好。

其实想测试下这个博客是否会如自己设想地那般更新。

-----

这是个下划线，这是来自 8 月 9 号的更新：果然链接生成的 url 还是以 localhost 为开头，似乎和 toml 的变量命名规则有关系，baseURL 和 BaseURL 是 2 个不同的变量，但是在同等命名情况下，languageCode 和 LanguageCode 变量似乎又是通用的。不解。

【后续更新】

同命令大小毫无关系，而是 hugo 构建网站时，需要通过 `env HUGO_ENV="production" hugo -t github-style` 命令来实现 url 转换，修正了 url，我的 GA 统计也正常了。上面命令的 `github-style` 是本博客采用的 hugo 主题名。

## 每日一照

这是今日的晚饭，白灼？水煮小青菜 & 韭菜炒虾干。

![image](https://github.com/user-attachments/assets/71955ca0-a19a-49fe-b749-7712982ee8dd)
