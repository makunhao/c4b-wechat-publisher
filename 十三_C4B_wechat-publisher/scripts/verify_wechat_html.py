#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_wechat_html.py —— 公众号 HTML 合规自检器

为什么要有它
------------
公众号编辑器**不会报错**——它只是**安静地把你没做对的格式扔掉**：
`<style>` 整块消失、外部图片变裂图、`<h1>` 直接吞掉。
你粘贴进去的时候看起来一切正常，**发布之后才发现排版全毁**。

所以转换器必须在"你还在本机"的时候就告诉你合不合格，
而不是等你在手机上预览时才发现。

判据来源
--------
`references/wechat_restrictions.md`（来自 C4B starter kit）：

· 允许标签：p, h2, h3, ul, ol, li, span, img, a, table, tr, th, td, br
· 违禁标签：h1, div, script, style, iframe, video, audio, pre, code
· 违禁属性：class, id, on*（事件）
· 外部资源：图片必须走公众号 CDN（http(s) 外链会被丢）

用法
----
    python verify_wechat_html.py output.html          # 检查文件
    from verify_wechat_html import verify; verify(html)  # 作为库调用

退出码：0 = 合格，1 = 不合格
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ALLOWED_TAGS = {"p", "h2", "h3", "ul", "ol", "li", "span", "img", "a",
                "table", "tr", "th", "td", "br"}
FORBIDDEN_TAGS = {"h1", "div", "script", "style", "iframe", "video",
                  "audio", "pre", "code", "object", "embed"}
FORBIDDEN_ATTRS = {"class", "id"}
# 结构性标签（不属于"正文可粘贴区域"，不参与检查）
STRUCTURAL = {"html", "head", "body", "meta", "title"}


def verify(html: str, strict_images: bool = True) -> tuple[bool, list[str]]:
    """返回 (是否合格, 问题列表)。问题列表为空即合格。"""
    soup = BeautifulSoup(html, "lxml")
    issues: list[str] = []

    # ── 1. 违禁标签 ──────────────────────────────────────────
    for tag in soup.find_all(True):
        name = tag.name.lower()
        if name in STRUCTURAL:
            continue
        if name in FORBIDDEN_TAGS:
            issues.append(f"违禁标签 <{name}>（第 {tag.sourceline or '?'} 行附近）"
                          f"——公众号会整块丢弃或吞掉内容")
        elif name not in ALLOWED_TAGS:
            issues.append(f"未知标签 <{name}> 不在允许列表里"
                          f"（允许：{', '.join(sorted(ALLOWED_TAGS))}）")

    # ── 2. 违禁属性 ──────────────────────────────────────────
    for tag in soup.find_all(True):
        if tag.name.lower() in STRUCTURAL:
            continue
        for attr in tag.attrs:
            if attr in FORBIDDEN_ATTRS:
                issues.append(f"<{tag.name}> 带有违禁属性 {attr}="
                              f"{tag.attrs[attr]!r}——公众号会剥掉 class/id，"
                              f"靠 class 做的样式会全部失效")
            elif attr.startswith("on"):
                issues.append(f"<{tag.name}> 带有事件属性 {attr}——公众号禁止任何脚本")

    # ── 3. <style> 块 / 内联 CSS 之外的样式来源 ───────────────
    for st in soup.find_all("style"):
        issues.append("存在 <style> 块——公众号只接受 inline CSS，"
                      "整块 <style> 会被剥掉")
    if re.search(r"@import|<link[^>]+stylesheet", html, re.I):
        issues.append("存在外部样式表引用（@import / <link rel=stylesheet>）"
                      "——公众号会剥掉")

    # ── 4. 外部图片（会被公众号丢弃 → 裂图） ─────────────────
    if strict_images:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith(("http://", "https://")):
                host = re.sub(r"^https?://([^/]+).*", r"\1", src)
                if "mmbiz.qpic.cn" not in host:      # 公众号 CDN
                    issues.append(f"外部图片 {host} ——公众号只认自己的 CDN"
                                  f"（mmbiz.qpic.cn），外链图会变裂图；"
                                  f"请上传后在编辑器里替换")

    # ── 5. 每个可见元素都要有内联样式（没有 = 用默认样式 = 排版失控） ──
    unstyled = []
    for tag in soup.find_all(True):
        if tag.name.lower() in STRUCTURAL or tag.name in {"br", "img"}:
            continue
        if not tag.get("style"):
            unstyled.append(tag.name)
    if unstyled:
        import collections
        c = collections.Counter(unstyled)
        detail = "、".join(f"<{k}>×{v}" for k, v in c.most_common())
        issues.append(f"以下元素没有内联 style（会退回浏览器默认样式）：{detail}")

    # ── 6. 空段落（粘贴后会出现大段空白） ────────────────────
    empty_p = [p for p in soup.find_all("p") if not p.get_text(strip=True)
               and not p.find("img") and not p.find("br")]
    if empty_p:
        issues.append(f"存在 {len(empty_p)} 个空 <p>（粘贴后会出现成片空白）")

    return (len(issues) == 0), issues


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"找不到文件：{p}", file=sys.stderr)
        return 2
    ok, issues = verify(p.read_text(encoding="utf-8"))
    print("=" * 62)
    print(f"公众号 HTML 合规自检 · {p.name}")
    print("-" * 62)
    if ok:
        print("✓ 合格：无违禁标签 / 属性 / 外部资源，全部元素带内联样式")
        print("=" * 62)
        return 0
    print(f"✗ 不合格：{len(issues)} 个问题")
    for i, it in enumerate(issues, 1):
        print(f"  {i}. {it}")
    print("-" * 62)
    print("修好上面这些再粘贴到公众号编辑器——"
          "否则你会在手机预览时才发现排版全毁。")
    print("=" * 62)
    return 1


if __name__ == "__main__":
    sys.exit(main())
