---
name: wechat-publisher
description: >
  把 Markdown / Word 文档转换成**可直接粘贴进微信公众号编辑器**的 HTML。
  内置 3 套排版主题、代码块换行修复、多格式输出（公众号 HTML + 知乎 Markdown + 纯文本），
  并且**转换完自动跑合规自检**——不合格直接报错，不会让你粘进去之后才发现排版全毁。
  当你需要写公众号文章、把技术笔记变成推文、或者要保证排版在公众号里不崩时使用。
  触发短语（中文）：公众号文章 / 公众号排版 / 转公众号格式 / 推文排版 /
  文章转 HTML / 公众号代码块 / 微信推文 / 生成公众号稿。
  Trigger phrases (English): wechat article / wechat publish / convert to wechat html /
  wechat formatting / official account article.
  也适用于：任何"Markdown → 内联 CSS 的 HTML"的转换场景。
---

# wechat-publisher · 公众号文章生成

> 一句话：**输入 Markdown/Word，输出能直接粘进公众号编辑器的 HTML——
> 并且在粘贴之前就告诉你排版会不会崩。**

---

## 为什么需要它

公众号编辑器有三个特点，让它成为排版的地狱：

1. **只接受 inline CSS**——`<style>` 整块会被剥掉
2. **违禁标签直接吞**——`<h1>` 没收当文章标题、`<div>` 不可靠、`<pre>`/`<code>` 不在允许列表
3. **不报错**——你粘贴时一切正常，**发布后在手机上才发现排版全毁**

第三条最致命：**你没有任何反馈渠道知道自己做错了**。
所以本技能在转换完之后**自动跑一遍合规自检**，不合格直接退出码 1。

---

## 快速开始

```bash
# ① 最常用：一篇文章，三平台格式，自动摘要
python scripts/convert_to_wechat.py 文章.md output.html --summary auto --formats wechat,zhihu,txt

# ② 换主题
python scripts/convert_to_wechat.py 文章.md output.html --theme warm

# ③ 只想检查一篇 HTML 合不合格
python scripts/verify_wechat_html.py output.html
```

依赖：`pip install markdown beautifulsoup4 lxml`（读 .docx 再加 `python-docx`）

---

## 输出什么

| 格式 | 文件 | 用途 |
|---|---|---|
| `wechat` | `output.html` | 浏览器打开 → Ctrl+A → Ctrl+C → 粘贴进公众号编辑器 |
| `zhihu` | `output_zhihu.md` | 知乎支持完整 Markdown，直接粘贴 |
| `txt` | `output_plain.txt` | 折行纯文本，用于其他平台或校对 |

---

## 三套主题

| 主题 | 适合 | 强调色 |
|---|---|---|
| `tech-blue` | 教程 / 代码类 | 蓝 |
| `warm` | 心得 / 叙事类 | 橙 |
| `ink` | 随笔 / 评论 | 黑 |

加一个新主题 = 在 `THEMES` 里加 5 个语义色（正文/强调/分隔/代码底/引用底），
不需要复制 60 行 CSS。

---

## 合规自检查什么

`scripts/verify_wechat_html.py` 扫描 6 类问题：

| # | 检查项 | 为什么 |
|---|---|---|
| 1 | 违禁标签（h1/div/script/style/iframe/pre/code…） | 公众号会整块丢弃或吞掉 |
| 2 | 违禁属性（class/id/事件） | 剥掉之后靠 class 做的样式全部失效 |
| 3 | `<style>` 块 / 外部样式表 | 只接受 inline CSS |
| 4 | 外部图片（非 `mmbiz.qpic.cn`） | 公众号只认自己的 CDN，外链变裂图 |
| 5 | **没有内联 style 的元素** | 会退回浏览器默认样式 = 排版失控 |
| 6 | 空 `<p>` | 粘贴后出现成片空白 |

**第 5、6 条是本技能自己加的**——starter 没查这两项，而它们恰恰是最容易踩的。

---

## 目录结构

```
wechat-publisher/
├── SKILL.md                        ← 本文件
├── scripts/
│   ├── convert_to_wechat.py        ← 主转换器（含合规自检调用）
│   └── verify_wechat_html.py       ← 合规自检器（可独立使用）
├── references/
│   ├── wechat_restrictions.md      ← 公众号规则（来自 starter）
│   ├── wechat_styles.md            ← 样式参考（来自 starter）
│   └── themes.md                   ← 主题色板与适用场景
└── examples/
    └── sample_article.md           ← starter 自带样例
```

---

## 已知限制

| 限制 | 说明 |
|---|---|
| 不上传图片 | 公众号图片必须走它自己的 CDN，本工具不做上传；`<img>` 外链会被自检标出来 |
| 不直接发布 | 公众号没有开放的个人发布 API；本工具产出 copy-paste ready 的 HTML，最后一步是手动粘贴 |
| 数学公式 | 不处理 LaTeX 渲染（公众号不支持 MathJax）；如需公式请先转成图片 |
| 高亮/脚注 | Markdown 的 `==高亮==` 与脚注语法不支持 |
