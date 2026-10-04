# C4B · 公众号文章生成技能 —— 交付包索引

> 作者：十三　｜　挑战：C4B 公众号文章生成技能
> 技能名：**wechat-publisher**（从官方 starter kit 改造）
> **最后更新：2026-10-04**

---

## 〇、状态一句话

| 项 | 状态 |
|---|---|
| 技能本体（转换器 + 合规自检器 + 三主题） | ✅ **完成并实测** |
| 真实文章源文件 + 转换产物 | ✅ **完成，合规自检通过** |
| 知乎 / 纯文本多格式输出 | ✅ 完成 |
| **发布到公众号** | ⏳ **待发布**（需要登录公众号后台手动粘贴，无开放 API） |

> **为什么发布这一栏是空的**：公众号没有个人发布 API，最后一步必须人来点。
> 我把发布前的每一步都做完了，并让"发布"退化成一个机械动作。
> `十三_C4B_文章链接.md` 里写了这一点，**没有编一个链接进去**。

---

## 一、这个技能解决什么

公众号编辑器排版有三个特点：**只接受 inline CSS、违禁标签直接吞、出错不报错**。

第三条最致命——你粘贴时一切正常，**发布后在手机上才发现排版全毁**。

所以这个技能的核心不是"转换"，而是**转换完自动跑合规自检**：
不合格直接报错，把问题留在你还在本机的时候。

---

## 二、实测证据（不是"我觉得能用"）

**① starter 有一个真 bug，被修了：**

```text
输入代码块：def f(): / return 1 / return 2    （3 行）
starter 渲染：'def f():\n    return 1\n    return 2\n'   ← HTML 源码有 \n
浏览器实际： def f(): return 1 return 2                  ← 全在一行
```

原因：starter 用 `p.string = code_text` 且样式里没有 `white-space`，
HTML 会折叠空白。**多行代码在公众号里会变成一行。**
修法：显式 `<br>`（`br` 在公众号允许标签里）。

**② 自检器抓到我自己的 6 个问题（修完才通过）：**

```text
✗ 不合格！
  - 未知标签 <strong> 不在允许列表里     ← 我刚写的 bug：sanitize 之后才注入
  - 未知标签 <thead>/<tbody>            ← markdown 表格默认生成，不在允许列表
  - 没有内联 style：<tr>×5、<ol>×1 …    ← apply_styles 漏了这几个标签
  - 存在 7 个空 <p>                      ← bs4 文档节点语义丢内容
```

**③ 三主题回归全部通过**（tech-blue / warm / ink）。

---

## 三、交付物对照表

| 挑战要求的文件 | 本包文件 | 状态 |
|---|---|---|
| 定制后的技能包 | **`十三_C4B_wechat-publisher.skill`** + 同名源码目录 | ✅ |
| `姓名_C4B_文章链接.md` | **`十三_C4B_文章链接.md`** | ⏳ 待发布（含完整发布步骤） |
| `姓名_C4B_文章源文件.md` | **`十三_C4B_文章源文件.md`** | ✅ 真实文章（含 4 代码块压测换行 bug） |
| `姓名_C4B_output.html` | **`十三_C4B_output.html`** | ✅ 12,119 字节，合规自检通过 |
| `姓名_C4B_教学说明.md` | **`十三_C4B_教学说明.md`** | ✅ |
| `姓名_C4B_AI日志.md`（必须） | **`十三_C4B_AI日志.md`** | ✅ |
| `姓名_C4B_拿来说明.md` | **`十三_C4B_拿来说明.md`** | ✅ |

（多格式产物 `十三_C4B_output_zhihu.md` / `十三_C4B_output_plain.txt` 是技能产出的，一并保留。）

---

## 四、复现

```bash
pip install markdown beautifulsoup4 lxml

# 转换（三平台格式 + 自动摘要 + 合规自检）
python 十三_C4B_wechat-publisher/scripts/convert_to_wechat.py \
    十三_C4B_文章源文件.md 十三_C4B_output.html --summary auto --formats wechat,zhihu,txt

# 只检查某个 HTML 合不合格
python 十三_C4B_wechat-publisher/scripts/verify_wechat_html.py 某文件.html

# 换主题
python 十三_C4B_wechat-publisher/scripts/convert_to_wechat.py 文章.md out.html --theme warm
```

---

## 五、目录结构

```
C4B交付包/
├── README.md                          ← 本文件
├── 十三_C4B_wechat-publisher.skill     ← 技能包（zip，10 文件）
├── 十三_C4B_wechat-publisher/         ← 同一技能的源码
│   ├── SKILL.md
│   ├── scripts/convert_to_wechat.py   ← 主转换器（含强制合规自检）
│   ├── scripts/verify_wechat_html.py  ← 合规自检器（可独立使用）
│   ├── references/{wechat_restrictions,wechat_styles,themes}.md
│   └── examples/sample_article.md     ← starter 样例（保留作回归）
├── 十三_C4B_文章源文件.md              ← 真实文章源文件
├── 十三_C4B_output.html               ← 转换产物（合规通过）
├── 十三_C4B_output_zhihu.md           ← 知乎版
├── 十三_C4B_output_plain.txt          ← 纯文本版
├── 十三_C4B_文章链接.md                ← ⏳ 待发布后回填
├── 十三_C4B_教学说明.md
├── 十三_C4B_AI日志.md
└── 十三_C4B_拿来说明.md
```
