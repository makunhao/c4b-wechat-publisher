# C4B · 拿来说明

> 作者：十三　｜　挑战：C4B 公众号文章生成技能
> 挑战要求："必须从 starter kit 出发。说明你拿了什么、改了什么、为什么改。"

---

## 一、起点：starter 里到底有什么

解包 `c4b-wechat-publisher-starter.zip`（6 个文件，44 KB）：

| 文件 | 规模 | 内容 |
|---|---|---|
| `SKILL.md` | — | 主指令 |
| `scripts/convert_to_wechat.py` | **383 行** | 转换主脚本 |
| `references/wechat_restrictions.md` | — | **公众号允许/违禁标签的完整清单** ← 最有价值 |
| `references/wechat_styles.md` | — | 样式参考 |
| `examples/sample_article.md` + `sample_output.html` | — | 样例 |

`convert_to_wechat.py` 的实际结构（我读了，不是照文档猜的）：

| 函数 | 做什么 |
|---|---|
| `install_dependencies()` | 自动 pip install |
| `read_markdown()` / `read_docx()` | 两种输入 |
| `sanitize()` | h1→h2、div→p、pre→styled p、blockquote→p、strong/em→span |
| `apply_styles()` | 逐元素内联样式 |
| `clean_attributes()` | 剥 class/id/事件属性 |
| `convert()` / `main()` | 串起来 |

---

## 二、拿了什么（逐条）

| # | 拿的 | 出处 | 怎么用 |
|---|---|---|---|
| 1 | **整体流程**：读源 → md → HTML → sanitize → 内联样式 → 输出 | `convert()` | 原样保留，只是每一步都加强了 |
| 2 | **公众号规则清单** | `references/wechat_restrictions.md` | 原样保留，并**变成自检器的判据来源**（不再只是文档，是可执行的规则） |
| 3 | `sanitize()` 的骨架 | h1→h2 / div→p / pre→p / blockquote→p / strong→span | 保留思路，重写实现（原因见 §3.2） |
| 4 | "逐元素内联样式"的做法 | `apply_styles()` | 保留，补齐了 ul/ol/tr |
| 5 | 属性清洗 | `clean_attributes()` | 并进 `apply_styles()`，少一遍全树遍历 |
| 6 | 样例文章 | `examples/sample_article.md` | 原样保留作回归用例 |
| 7 | 依赖自检 | `install_dependencies()` | 改成**启动前检查**并给出明确 pip 命令（原来是运行中途装） |

---

## 三、改了什么（以及为什么改）

### 3.1 ★修 starter 的真 bug：代码块换行丢失

**这是本次最重要的一条。** starter 的代码块处理是：

```python
p.string = code_text          # 直接把多行文本塞进一个 <p>
p['style'] = STYLES['code_block']   # 样式里没有 white-space
```

HTML 会把 `\n` 折叠成空格。我用一个 3 行的 Python 代码块实测：

```
渲染结果：'def f():\n    return 1\n    return 2\n'   ← HTML 源码里有 \n
浏览器渲染：def f(): return 1 return 2               ← 全在一行
```

**多行代码在公众号里会变成一行。** 对一篇技术文章来说，这是致命的。

**修法**：转义后把 `\n` 显式变成 `<br>`（`br` 在公众号允许标签里，行为确定），
再逐段塞 `NavigableString` 构造节点。

### 3.2 重写 `sanitize()` 里的 DOM 拼接

starter 大量使用这种写法：

```python
p = soup.new_tag('p')
p.string = bq.get_text()          # ← get_text() 会把 <strong> 等内层标记整个抹平
bq.replace_with(p)
```

`get_text()` 丢内层结构——引用块里的加粗会变成纯文本。
我改成"**提升内层 `<p>`**"（markdown 的 blockquote 一定把内容包在 `<p>` 里），
内层的 `<strong>` 留给后面的统一替换处理，不丢信息。

**踩过的坑**：我第一版用 `BeautifulSoup(fragment, "lxml")` 解析片段再 append，
结果 **bs4 的文档节点语义把内容整个丢了**——3 个空引用块。
是被自己写的"空段落检查"抓出来的。改成 `html.parser` / 直接提升节点后才对。

### 3.3 新增：主题系统

starter 的 `STYLES` 是一套写死的字典。我改成 **5 个语义色槽位生成整套样式**：

```python
THEMES["forest"] = _theme("#122117", "#15803d", "#cfe3d4", "#f0fdf4", "#14532d", "森林绿")
```

加一个主题 = 5 个颜色，不是复制 60 行 CSS。
（详见 `references/themes.md`）

### 3.4 新增：合规自检器（`verify_wechat_html.py`，独立脚本）

**这是本技能最想强调的一块。** starter 只有转换，没有检查——
而公众号的特点恰恰是**不报错、安静地毁掉你的排版**。

自检器查 6 类问题，其中 **5、6 两项是 starter 完全没有的**：

| # | 检查项 | starter 有吗 |
|---|---|---|
| 1 | 违禁标签 | 部分（ sanitize 时会处理，但不检查输出） |
| 2 | 违禁属性 | 部分 |
| 3 | `<style>` 块 / 外部样式表 | ❌ 没有 |
| 4 | 外部图片（非公众号 CDN） | ❌ 没有 |
| 5 | **没有内联 style 的元素** | ❌ 没有 |
| 6 | **空 `<p>`** | ❌ 没有 |

**它真的抓到了我的问题**：第一次跑，自检报了 6 个问题——
包括我自己刚写的 `<strong>导读：</strong>`（在 sanitize 之后注入，逃过了替换）、
markdown 表格默认生成的 `<thead>/<tbody>`（不在允许列表）、没给 `<tr>/<ul>/<ol>` 上样式、
以及 3 个空引用块。

**修完之后才通过。** 也就是说：**如果没有自检器，这 6 个问题会被原样粘进公众号。**

### 3.5 新增：多格式输出与自动摘要

- `--formats wechat,zhihu,txt`：知乎支持完整 Markdown，直接给清洗后的源文；纯文本按 42 字折行
- `--summary auto`：取第一段非标题/引用/代码的正文生成导读
- `--theme`：三套主题

### 3.6 修：标题渲染两遍 + 嵌套 html/body

这两个是自检通过之后**我再看输出结构**发现的：
- lxml 解析片段时会自动包一层 `<html><body>`，直接 `decode()` 会输出嵌套的两套结构 → 只取 body 内容
- 源文件的 `# 标题` 既成了 `<title>` 又留在正文 → 标题出现两次 → 从正文拿掉

---

## 四、一句话总结

| | |
|---|---|
| **拿了** | 整体流程、公众号规则清单（并把它从文档变成可执行判据）、sanitize 骨架思路、内联样式做法、样例 |
| **修了** | **代码块换行丢失（starter 真 bug，多行代码变一行）**、`get_text()` 抹平内层标记、bs4 片段拼接丢内容 |
| **加了** | 主题系统（5 色槽位）、**合规自检器（6 类检查，其中 2 类 starter 完全没有）**、多格式输出、自动摘要、标题去重、嵌套结构修复 |
| **没做** | 图片上传（公众号 CDN 无开放 API）、直接发布（需手动粘贴）、数学公式渲染 |
