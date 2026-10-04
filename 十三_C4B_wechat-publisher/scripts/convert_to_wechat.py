#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_to_wechat.py —— 公众号文章生成（改造自 C4B starter kit）

从 starter 拿了什么
-------------------
· 整体流程：读源文件 → markdown → HTML → sanitize → 内联样式 → 输出
· `wechat_restrictions.md` 里的全部规则（违禁标签/属性/CSS 要求）
· `sanitize()` 的骨架思路（h1→h2、div→p、blockquote→p、strong→span）
· `apply_styles()` 的"逐元素内联样式"做法

改了什么（详见《拿来说明》）
---------------------------
1. ★修 bug：代码块换行丢失。starter 用 `p.string = code_text`，
   HTML 会把 `\\n` 折叠成空格 → **多行代码渲染成一行**。
   改成显式 `<br>`（`br` 在公众号允许标签列表里，行为确定）。
2. ★主题系统：1 套写死样式 → 3 套主题（tech-blue / warm / ink），`--theme` 选择
3. ★多格式输出：`--formats wechat,zhihu,txt`（同一内容三平台）
4. ★合规自检：转换完自动跑一遍违禁项扫描，**不合格直接退出码 1**
5. ★摘要自动生成：`--summary auto` 取首段
6. 表格：starter 只给 th/td 上样式，**没给 table 外层与隔行**；补齐
7. 首图/封面占位、引导卡样式

依赖：markdown、beautifulsoup4、lxml、python-docx（读 .docx 时才需要）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── 依赖自检（沿用 starter 的做法，但报错更明确） ──────────────
_MISSING = []
for _mod, _pip in (("markdown", "markdown"), ("bs4", "beautifulsoup4"),
                   ("lxml", "lxml")):
    try:
        __import__(_mod)
    except ImportError:
        _MISSING.append(_pip)
try:
    import docx  # noqa: F401
except ImportError:
    _DOCX_OK = False
else:
    _DOCX_OK = True

if _MISSING:
    sys.exit("缺少依赖，请先执行：\n  pip install " + " ".join(_MISSING))

import markdown                                            # noqa: E402
from bs4 import BeautifulSoup                              # noqa: E402


# ══════════════════════════════════════════════════════════════
# 一、主题系统（starter 只有一套写死的 STYLES）
# ══════════════════════════════════════════════════════════════
def _theme(ink: str, accent: str, soft: str, code_bg: str, code_fg: str,
           quote_bg: str, name: str) -> dict:
    """从 5 个语义色生成一整套内联样式。

    好处：加一个新主题 = 加 5 个颜色，不用复制 60 行 CSS。
    """
    return {
        "name": name,
        "body": (f"max-width: 677px; margin: 0 auto; padding: 20px 16px; "
                 f"color: {ink}; font-family: -apple-system, BlinkMacSystemFont, "
                 f"'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;"),
        "h2": (f"font-size: 21px; font-weight: 700; line-height: 1.5; "
               f"color: {ink}; margin: 28px 0 12px 0; "
               f"padding-left: 10px; border-left: 4px solid {accent};"),
        "h3": (f"font-size: 17px; font-weight: 700; line-height: 1.6; "
               f"color: {ink}; margin: 20px 0 8px 0;"),
        "p": (f"font-size: 16px; line-height: 1.8; color: {ink}; "
              f"margin: 12px 0; letter-spacing: 0.3px;"),
        "li": (f"font-size: 16px; line-height: 1.8; color: {ink}; margin: 6px 0;"),
        "strong": f"color: {accent}; font-weight: 700;",
        "em": "font-style: italic;",
        "code_inline": (f"background-color: {code_bg}; color: {code_fg}; "
                        f"font-size: 14px; padding: 2px 5px; border-radius: 3px; "
                        f"font-family: Consolas, Menlo, monospace;"),
        # ★ 代码块必须用 <br> 换行（starter 的 bug：靠 \n 会被浏览器折叠）
        "code_block": (f"background-color: {code_bg}; color: {code_fg}; "
                       f"font-size: 13.5px; line-height: 1.7; padding: 14px 16px; "
                       f"margin: 14px 0; border-radius: 6px; "
                       f"font-family: Consolas, Menlo, monospace; "
                       f"white-space: normal; word-break: break-all;"),
        "code_lang": (f"color: {accent}; font-size: 12px; text-align: right; "
                      f"margin: -10px 0 14px 0;"),
        "blockquote": (f"background-color: {quote_bg}; color: {ink}; "
                       f"padding: 12px 16px; margin: 14px 0; "
                       f"border-left: 4px solid {accent}; border-radius: 0 6px 6px 0;"),
        "table": (f"border-collapse: collapse; margin: 14px 0; font-size: 14px; "
                  f"width: 100%;"),
        "th": (f"background-color: {accent}; color: #ffffff; font-weight: 700; "
               f"padding: 8px 10px; text-align: left; border: 1px solid {accent};"),
        "td": (f"padding: 8px 10px; border: 1px solid {soft}; color: {ink};"),
        "td_alt": f"padding: 8px 10px; border: 1px solid {soft}; color: {ink}; "
                  f"background-color: {quote_bg};",
        "a": f"color: {accent}; text-decoration: none; "
             f"border-bottom: 1px solid {accent};",
        "hr": (f"border: none; height: 1px; background-color: {soft}; "
               f"margin: 24px 0;"),
        "cover": (f"text-align: center; color: {accent}; font-size: 13px; "
                  f"letter-spacing: 2px; margin: 0 0 6px 0;"),
        "summary": (f"background-color: {quote_bg}; color: {ink}; font-size: 15px; "
                    f"line-height: 1.8; padding: 14px 16px; margin: 16px 0; "
                    f"border-radius: 6px;"),
        "footer": (f"text-align: center; color: {soft}; font-size: 13px; "
                   f"margin: 30px 0 6px 0;"),
    }


THEMES = {
    "tech-blue": _theme("#1f2328", "#2563eb", "#d0d7de", "#f6f8fa", "#24292e",
                        "#eff6ff", "技术蓝（适合教程/代码类）"),
    "warm":      _theme("#3f2f1e", "#d97706", "#e7d8c3", "#fbf3e4", "#7c4a03",
                        "#fdf6e9", "暖橙（适合心得/叙事类）"),
    "ink":       _theme("#111111", "#111111", "#d4d4d4", "#f4f4f4", "#111111",
                        "#f7f7f7", "极简黑白（适合随笔/评论）"),
}


# ══════════════════════════════════════════════════════════════
# 二、输入（沿用 starter 的 read_markdown / read_docx 思路）
# ══════════════════════════════════════════════════════════════
def read_source(filepath: Path) -> str:
    if filepath.suffix.lower() in {".md", ".markdown", ".txt"}:
        return filepath.read_text(encoding="utf-8")
    if filepath.suffix.lower() == ".docx":
        if not _DOCX_OK:
            sys.exit("读 .docx 需要：pip install python-docx")
        from docx import Document
        doc = Document(str(filepath))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    sys.exit(f"不支持的源文件类型：{filepath.suffix}（支持 .md/.txt/.docx）")


# ══════════════════════════════════════════════════════════════
# 三、摘要自动生成
# ══════════════════════════════════════════════════════════════
def auto_summary(md_text: str, limit: int = 90) -> str:
    """取第一段非标题、非引用、非代码的正文，截到 limit 字。"""
    for block in re.split(r"\n\s*\n", md_text):
        t = block.strip()
        if not t or t.startswith(("#", ">", "```", "|", "-", "*", "!", "[")):
            continue
        t = re.sub(r"\*\*|__|`|\*", "", t)                 # 去掉行内标记
        t = re.sub(r"\s+", "", t)
        return t[:limit] + ("…" if len(t) > limit else "")
    return ""


# ══════════════════════════════════════════════════════════════
# 四、核心转换
# ══════════════════════════════════════════════════════════════
def md_to_html(md_text: str) -> str:
    exts = ["tables", "fenced_code", "nl2br"]
    return markdown.markdown(md_text, extensions=exts)


def sanitize(html: str, S: dict) -> tuple:
    """公众号兼容化。返回 (soup, stats)——stats 供自检与报告用。"""
    soup = BeautifulSoup(html, "lxml")
    stats = {"h1_downgraded": 0, "div_to_p": 0, "code_blocks": 0,
             "code_inline": 0, "blockquote": 0, "removed": 0}

    for tag_name in ("script", "style", "iframe", "video", "audio", "link"):
        for el in soup.find_all(tag_name):
            el.decompose(); stats["removed"] += 1

    for h1 in soup.find_all("h1"):                          # 公众号保留 h1 给标题
        h1.name = "h2"; stats["h1_downgraded"] += 1
    for d in soup.find_all("div"):
        d.name = "p"; stats["div_to_p"] += 1

    # ★ 代码块：显式 <br> 换行 + 语言标注（修 starter 的换行 bug）
    for pre in soup.find_all("pre"):
        code = pre.find("code")
        if code is not None:
            lang_cls = (code.get("class") or [""])[0]
            lang = lang_cls.split("-")[-1] if lang_cls.startswith("language-") else ""
        else:
            lang = ""
        text = (code.get_text() if code else pre.get_text()).rstrip("\n")
        # 先转义，再把换行变成 <br>（<br> 是公众号允许标签）
        esc = (text.replace("&", "&amp;").replace("<", "&lt;")
                   .replace(">", "&gt;").replace("\n", "<br>"))
        p = soup.new_tag("p")
        p["style"] = S["code_block"]
        # ★ 不用 BeautifulSoup 解析片段（append 一个文档节点会丢内容），
        #   直接按 <br> 切开逐段塞 NavigableString —— 行为完全确定。
        from bs4 import NavigableString
        for i, part in enumerate(esc.split("<br>")):
            if i:
                p.append(soup.new_tag("br"))
            if part:
                p.append(NavigableString(part))
        pre.replace_with(p)
        stats["code_blocks"] += 1
        if lang:
            tag = soup.new_tag("p")
            tag["style"] = S["code_lang"]
            tag.string = f"⟨ {lang} ⟩"
            pre.replace_with(tag) if False else pre.insert_before(tag) if False else None
            p.insert_after(tag)

    # 行内代码
    for code in soup.find_all("code"):
        span = soup.new_tag("span")
        span.string = code.get_text()
        span["style"] = S["code_inline"]
        code.replace_with(span); stats["code_inline"] += 1

    # 引用块
    for bq in soup.find_all("blockquote"):
        inner = bq.find("p")
        if inner is not None:
            # ★ 直接提升内层 <p>（保留其中的 <strong> 等，后面统一替换）。
            #   之前用 BeautifulSoup(inner, ...) 再 append，bs4 的文档节点语义
            #   把内容整个丢了 → 3 个空的引用块，被自检的"空段落"规则抓出来。
            inner["style"] = S["blockquote"]
            bq.replace_with(inner)
        else:
            p = soup.new_tag("p")
            p["style"] = S["blockquote"]
            p.string = bq.get_text()
            bq.replace_with(p)
        stats["blockquote"] += 1

    # 强调：bold 用主题强调色（starter 只有 font-weight）
    for tag in soup.find_all(["strong", "b"]):
        span = soup.new_tag("span")
        span["style"] = S["strong"]
        span.append(BeautifulSoup(tag.decode_contents() or "", "html.parser"))
        tag.replace_with(span)
    for tag in soup.find_all(["em", "i"]):
        span = soup.new_tag("span")
        span["style"] = S["em"]
        span.append(BeautifulSoup(tag.decode_contents() or "", "html.parser"))
        tag.replace_with(span)

    # ★ thead/tbody 不在公众号允许标签列表里（只有 table/tr/th/td）
    #   markdown 的表格默认生成 <thead>/<tbody>，必须拆掉，
    #   否则它们会被公众号剥掉、表头样式跟着失效。
    for wrap in soup.find_all(["thead", "tbody", "tfoot"]):
        wrap.unwrap()

    # 水平线：hr 不在允许列表 → 用样式化 <p> 模拟
    for hr in soup.find_all("hr"):
        p = soup.new_tag("p")
        p["style"] = S["hr"]
        hr.replace_with(p)

    return soup, stats


def apply_styles(soup, S: dict):
    """逐元素内联样式（starter 思路 + 表格隔行底色）。"""
    for tag, key in (("h2", "h2"), ("h3", "h3"), ("p", "p"), ("li", "li"),
                     ("ul", "li"), ("ol", "li"), ("tr", "td")):
        for el in soup.find_all(tag):
            if not el.get("style"):
                el["style"] = S[key]
    for a in soup.find_all("a"):
        a["style"] = S["a"]
    for tb in soup.find_all("table"):
        tb["style"] = S["table"]
        for i, tr in enumerate(tb.find_all("tr")):
            for cell in tr.find_all(["th", "td"]):
                cell["style"] = S["th" if cell.name == "th" else
                                  ("td_alt" if i % 2 == 0 else "td")]
    # 清掉公众号不接受的属性
    for el in soup.find_all(True):
        for attr in list(el.attrs):
            if attr not in ("style", "src", "href", "alt"):
                el.attrs.pop(attr, None)
    return soup


def build_document(soup, S: dict, title: str, summary: str, footer: str) -> str:
    head = (f'<p style="{S["cover"]}">· 本文由 wechat-publisher 技能生成 ·</p>'
            f'<h2 style="{S["h2"]}">{title}</h2>')
    if summary:
        head += (f'<p style="{S["summary"]}">'
                 f'<span style="{S["strong"]}">导读：</span>{summary}</p>')
    foot = f'<p style="{S["footer"]}">{footer}</p>'
    # ★ lxml 解析时会自动包一层 <html><body>，直接 decode() 会输出嵌套的两套
    #   html/body —— 公众号编辑器对这种结构的行为不可预期。只取 body 的内容。
    inner = soup.body.decode_contents() if soup.body else soup.decode()
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f"<title>{title}</title></head>"
            f'<body style="{S["body"]}">{head}{inner}{foot}</body></html>')


# ══════════════════════════════════════════════════════════════
# 五、多格式输出（知乎 / 纯文本）
# ══════════════════════════════════════════════════════════════
def to_zhihu(md_text: str, title: str) -> str:
    """知乎支持完整 Markdown，直接给清洗过的源文。"""
    return f"# {title}\n\n" + md_text.strip() + "\n"


def to_plain(md_text: str, width: int = 42) -> str:
    """纯文本：去标记 + 按宽度折行（公众号转知乎/打印都可用）。"""
    out = []
    for block in re.split(r"\n\s*\n", md_text):
        b = block.strip()
        if not b:
            continue
        if b.startswith("```"):                             # 代码块：保留原样
            out.append(b); continue
        if b.startswith("#"):
            b = b.lstrip("#").strip()
        b = re.sub(r"\*\*|__|`", "", b)
        b = re.sub(r"^[-*] ", "· ", b, flags=re.M)
        out.append("\n".join(b[i:i + width] for i in range(0, len(b), width)))
    return "\n\n".join(out)


# ══════════════════════════════════════════════════════════════
# 六、主流程
# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown/Docx → 公众号 HTML")
    ap.add_argument("input")
    ap.add_argument("output", nargs="?", default="output.html")
    ap.add_argument("--theme", default="tech-blue", choices=list(THEMES),
                    help="排版主题")
    ap.add_argument("--title", default=None, help="覆盖文章标题")
    ap.add_argument("--summary", default=None,
                    help="导读；传 auto 则自动取首段")
    ap.add_argument("--footer", default="— 完 —")
    ap.add_argument("--formats", default="wechat",
                    help="逗号分隔：wechat,zhihu,txt")
    ap.add_argument("--verify", action="store_true", help="转换后自动跑合规自检")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"找不到源文件：{src}")
    S = THEMES[args.theme]
    md_text = read_source(src)

    # 标题：CLI > 文章首个 # 标题
    m = re.match(r"^\s*#\s+(.+)$", md_text, re.M)
    title = args.title or (m.group(1).strip() if m else src.stem)
    if m and not args.title:
        # ★ 标题已提到 <title> 与正文标题区，正文里再渲染一遍会重复
        md_text = md_text[:m.start()] + md_text[m.end():]
    summary = auto_summary(md_text) if args.summary == "auto" else (args.summary or "")

    soup, stats = sanitize(md_to_html(md_text), S)
    soup = apply_styles(soup, S)
    html = build_document(soup, S, title, summary, args.footer)

    outdir = Path(args.output).parent
    outdir.mkdir(parents=True, exist_ok=True)
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    stem = Path(args.output).stem

    written = []
    if "wechat" in formats:
        p = outdir / f"{stem}.html"; p.write_text(html, encoding="utf-8")
        written.append((p, len(html)))
    if "zhihu" in formats:
        p = outdir / f"{stem}_zhihu.md"
        p.write_text(to_zhihu(md_text, title), encoding="utf-8")
        written.append((p, p.stat().st_size))
    if "txt" in formats:
        p = outdir / f"{stem}_plain.txt"
        p.write_text(to_plain(md_text), encoding="utf-8")
        written.append((p, p.stat().st_size))

    print("=" * 62)
    print(f"公众号文章生成 · 主题：{S['name']}")
    print("-" * 62)
    print(f"  标题：{title}")
    if summary:
        print(f"  导读：{summary[:40]}{'…' if len(summary) > 40 else ''}")
    print(f"  代码块 {stats['code_blocks']} 个（已用 <br> 修换行）/ "
          f"行内代码 {stats['code_inline']} / 引用块 {stats['blockquote']}")
    if stats["h1_downgraded"] or stats["div_to_p"] or stats["removed"]:
        print(f"  兼容化：h1→h2 {stats['h1_downgraded']} 处、"
              f"div→p {stats['div_to_p']} 处、移除标签 {stats['removed']} 个")
    print("-" * 62)
    for p, n in written:
        print(f"  ✓ {p.name}（{n:,} 字节）")
    print("=" * 62)

    # ★ 转换完立刻自检（不通过就退出码 1）
    if args.verify or True:
        from verify_wechat_html import verify
        ok, issues = verify(html)
        if ok:
            print("  合规自检：✓ 通过（无违禁标签/属性/外部资源）")
        else:
            print("  合规自检：✗ 不合格！")
            for it in issues:
                print(f"    - {it}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
