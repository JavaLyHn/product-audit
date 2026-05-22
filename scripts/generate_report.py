"""Generate report.md and report.html from audit workspace.

Reads:
  <workspace>/audit-meta.json
  <workspace>/raw/findings.jsonl
  <workspace>/figs/*.png

Writes:
  <workspace>/report.md
  <workspace>/report.html (optional, if --formats includes html)
"""

import argparse
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


REPORT_TEMPLATE_MD = """# {product_name} 产品深度体验报告

> **本报告聚焦：产品**功能层**的可理解性与完整性 — 不评 UI 美学**

## 报告信息

| 项 | 内容 |
|---|---|
| 产品名称 | {product_name} |
| 产品 URL | {url} |
| 体验时间 | {completed_at} |
| 体验人 | {experimenter} |
| 体验环境 | {environment} |
| 评测模板 | `{template}` |
| 深度档位 | `{depth}` |
| 主测点数 | {test_points_count}（含 {background_count} 个递归背景测点） |
| LLM 调用 | {llm_calls_used} / {llm_calls_budget} |
| 报告语言 | {language} |
| 报告版本 | v1.15 (auto-generated; v1.11 实体身份验证 + v1.12 URL 探测 + v1.13 精简结构 + **v1.15 §5 第三方社区反馈** Reddit/PH/HN/G2) |
| 工具 | product-audit Skill |

---

## 目录

- [1. Executive Summary](#1-executive-summary)
  - [1.1 一句话判定](#11-一句话判定)
  - [1.2 整体兑现度](#12-整体兑现度)
  - [1.3 风险与机会 Top 3](#13-风险与机会-top-3)
  - [1.4 立即可做的 Quick Wins](#14-立即可做的-quick-wins)
  - [1.5 综合评分（5 分制 × 6 维度）⭐](#15-综合评分5-分制--6-维度)
- [2. 产品概览](#2-产品概览)
  - [2.1 基础信息](#21-基础信息)
  - [2.2 测点速览](#22-测点速览)
  - [2.3 产品 / 公司背景信息（递归发现）](#23-产品--公司背景信息递归发现)
  - [2.4 产品战略抽象（X 化 叙事）⭐](#24-产品战略抽象x-化-叙事)
  - [2.5 公司基本信息（web search 自动补充）⭐](#25-公司基本信息web-search-自动补充-)
- [3. 体验方法论](#3-体验方法论)
  - [3.1 测试用例矩阵](#31-测试用例矩阵)
  - [3.2 评分与严重度分级（功能层）](#32-评分与严重度分级功能层)
  - [3.3 限制与边界声明](#33-限制与边界声明)
- [4. 体验流程记录](#4-体验流程记录)
  - [4.1 官网 Narrative 综合（叙事手法 + 关键词图谱）⭐](#41-官网-narrative-综合叙事手法--关键词图谱)
  - [4.2 测点流程详情（按模块聚合）](#42-测点流程详情按模块聚合)
- [5. 第三方社区反馈（非官方）⭐](#5-第三方社区反馈非官方)
- [6. 总结](#6-总结)
  - [6.1 一句话评价](#61-一句话评价)
  - [6.2 最大优点 Top 3](#62-最大优点-top-3)
  - [6.3 最大风险 Top 3](#63-最大风险-top-3)
  - [6.4 用户增长漏斗推断（官网作用域）⭐](#64-用户增长漏斗推断官网作用域-)

---

## 1. Executive Summary

### 1.1 一句话判定

{one_line_verdict}

### 1.2 整体兑现度

{overall_score_table}

### 1.3 风险与机会 Top 3

#### 🔴 Top 3 风险（功能层）

{top_risks}

#### 🚀 Top 3 机会 / 优势

{top_opportunities}

### 1.4 立即可做的 Quick Wins

{quick_wins_summary}

### 1.5 综合评分（5 分制 × 6 维度）

> 跨全部测点的产品级综合评分，由 synthesis-pass LLM 调用产出（见 §3.1 体验方法论）。

{scorecard_section}

---

## 2. 产品概览

### 2.1 基础信息

- **URL**: {url}
- **首屏标题 / Slogan**: {first_title}
- **评测模板分类**: {template}

### 2.2 测点速览

本次审计覆盖 {test_points_count} 个测点，其中 **{background_count} 个**来自递归背景信息挖掘（详见 §2.3）。详细列表见 §4。

{login_coverage_note}

### 2.3 产品 / 公司背景信息（递归发现）

> 本节通过对 help / docs / resources / 跨子域 `help.X.com` 等内容枢纽**递归挖掘**得到，
> 旨在抽出产品方自己写的 "What is X / Getting Started / Overview" 类介绍页内容，
> 还原产品方对自家产品的**官方定义**。

{background_section}

### 2.4 产品战略抽象（X 化 叙事）

> 跨全部测点 + 背景递归的综合分析，由 synthesis-pass LLM 调用从 4-6 个不同角度
> 抽取产品的战略本质，**对齐人工产品分析报告 §2 章节的写法**。

{strategic_abstractions_section}

### 2.5 公司基本信息（web search 自动补充）⭐

> 由 synthesis-pass LLM 调用 **WebSearch 工具**主动搜索 Crunchbase / TechCrunch /
> LinkedIn / 公司新闻稿等外部公开信息，补足审计本身看不到的事实数据（成立时间 /
> 融资轮次 / 团队规模 / 创始人背景 / 近期动态）。每条信息标注来源。

{company_info_section}

---

## 3. 体验方法论

### 3.1 测试用例矩阵

本次评测使用 **{template}** 模板的 **{depth}** 深度档位，共执行 {test_points_count} 个测试点。

执行流程：

1. **浏览器操作**（Playwright 驱动） — 导航 / 点击 / 截图
2. **Phase 0**：发现首页 nav / footer 全部子页（同源 + 跨子域 hub）
3. **主测点循环**：对每个测点优先**真跳转**到 Phase 0 发现的子页
4. **Auto-explore**：主测点跑完后自动遍历剩余未访问的 nav 子页
5. **Phase 0++（v1.4 新增）：递归背景挖掘** — 进入 help / docs / resources 等内容枢纽（含 `help.X.com` 跨子域），BFS 二次发现 "What is X / Getting Started / Overview" 类介绍页面并捕获
6. **LLM 功能解读**（Claude） — 对每个测点的截图 + 页面文本做产品**功能层**结构化观察（不评 UI）
7. **Phase final（v1.5-v1.9）：Synthesis pass** — 全部测点跑完后追加 **5 次**跨测点综合 LLM 调用：
   - §2.4 战略 X 化叙事（产品本质的 4-6 个抽象方向）
   - §1.5 综合评分（6 维度 5 分制）
   - §4.1 官网 Narrative 综合（关键词图谱 + 叙事手法）
   - §6.4 官网用户增长漏斗推断（**官网作用域**, v1.9 起不再含登录后数据）
   - §2.5 公司基本信息（WebSearch + WebFetch — 融资 / 团队 / 上线 / 来源引用，v1.8 + v1.11 身份验证）
   - §5 第三方社区反馈（WebSearch Reddit / Product Hunt / Hacker News / G2，**v1.15 新增**）
   - ~~原 §4.1 综合产品级风险~~（v1.9 已移除）
8. **归档**（JSONL + JSON） — 持久化到 `raw/findings.jsonl` + `raw/synthesis.json`

### 3.2 评分与严重度分级（功能层）

- **P1** 严重: 关键功能描述缺失 / 误导
- **P2** 中等: 功能信息不完整
- **P3** 轻微: 功能细节可改进
- **✅** 正面: 功能介绍清晰有力

### 3.3 限制与边界声明

- 本报告由 AI 半自动生成，关键决策建议结合人工 review
- 截图基于审计时刻状态，产品后续更新可能使报告过时
- **焦点是产品功能可理解性**，不评视觉 / UI / 移动端适配

---

## 4. 体验流程记录

### 4.1 官网 Narrative 综合（叙事手法 + 关键词图谱）

> 由 synthesis-pass LLM 从所有营销 / 介绍页观察中抽取，**先 top-down 看叙事**，
> 再看 §4.2 模块细节。对齐人工产品分析报告 §3.5 章节。

{narrative_summary_section}

### 4.2 测点流程详情（按模块聚合）

> 全部测点按 URL 路径**模块化聚合**：AI 能力 / 解决方案 / 商业化 / 集成 等。
> 每个模块下列出该模块覆盖的页面 + 每个测点的 LLM 功能观察。

{findings_body}

---

## 5. 第三方社区反馈（非官方）⭐

> ⚠️ **本章信息来源是非官方第三方平台**（Reddit / Product Hunt / Hacker News / G2 等）。
> 由 synthesis-pass LLM 调用 **WebSearch 工具**主动搜索社区真实用户讨论，
> 对照 §4.1 官网 Narrative 找出**官方叙事 vs 用户实感**的 gap。
> 内容含主观偏见、过时信息或个别极端观点；决策时建议结合 §2.5 官方信息 + §4 实测综合判断。

{community_feedback_section}

---

## 6. 总结

### 6.1 一句话评价

{one_line_verdict}

### 6.2 最大优点 Top 3

{top_opportunities}

### 6.3 最大风险 Top 3

{top_risks}

### 6.4 用户增长漏斗推断（官网作用域）⭐

> 基于 pricing / signup / demo / 背景介绍页的观察，**推断**产品的官网层增长漏斗、
> 评估分叉、价格心智锚点、可见的 Aha 承诺等。**作用域：到访客转化为注册/试用用户为止**。
> v1.9：不再分析团队扩散、登录后留存等需要 dashboard 数据的环节。

{growth_funnel_section}

---

*生成时间: {generated_at}*
"""


def load_workspace(workspace: Path) -> tuple[dict, list[dict]]:
    """Load metadata and findings from a workspace."""
    meta = json.loads((workspace / "audit-meta.json").read_text())
    findings = []
    findings_file = workspace / "raw" / "findings.jsonl"
    if findings_file.exists():
        for line in findings_file.read_text().splitlines():
            if line.strip():
                findings.append(json.loads(line))
    return meta, findings


def categorize_findings(findings: list[dict]) -> dict:
    """Split findings into P1/P2/P3/G buckets based on observation prefixes."""
    buckets = {"P1": [], "P2": [], "P3": [], "G": [], "neutral": []}
    for f in findings:
        for obs in f.get("observations", []):
            obs_lower = obs.lower()
            if "p1" in obs_lower[:8] or "🔴" in obs:
                buckets["P1"].append((f["test_point_id"], obs))
            elif "p2" in obs_lower[:8] or "🟡" in obs:
                buckets["P2"].append((f["test_point_id"], obs))
            elif "p3" in obs_lower[:8] or "⚪" in obs:
                buckets["P3"].append((f["test_point_id"], obs))
            elif "✅" in obs or "🟢" in obs or obs_lower.startswith(("g-", "g:")):
                buckets["G"].append((f["test_point_id"], obs))
            else:
                buckets["neutral"].append((f["test_point_id"], obs))
    return buckets


# v1.6 A2: Module clustering — group test points by URL path semantically.
# Each tuple: (regex, label, emoji). First match wins. Findings without a
# resolved URL go to "未找到的测点", B* findings go to "产品官方介绍".
import re as _re_mod
MODULE_PATTERNS = [
    (_re_mod.compile(r"^/$|^$"),                                                          "首页",                "🏠"),
    (_re_mod.compile(r"/(pricing|plans?)\b", _re_mod.IGNORECASE),                         "定价 / 商业化",       "💰"),
    (_re_mod.compile(r"/(signup|sign[-_]up|get[-_]started|start|trial|free|onboard)\b", _re_mod.IGNORECASE), "注册 / 试用入口", "🚪"),
    (_re_mod.compile(r"/(demo|request[-_]demo|contact[-_]sales|book[-_]a[-_]demo)", _re_mod.IGNORECASE),     "Demo / 销售对接", "📞"),
    (_re_mod.compile(r"/(login|sign[-_]in|signin)\b", _re_mod.IGNORECASE),                "登录入口",             "🔑"),
    (_re_mod.compile(r"/(about|company|team|story|mission|manifesto)\b", _re_mod.IGNORECASE), "公司 / 团队",       "🏢"),
    (_re_mod.compile(r"/(careers?|jobs?)\b", _re_mod.IGNORECASE),                         "招聘",                 "👥"),
    (_re_mod.compile(r"/(contact|support)(?!.*sales)", _re_mod.IGNORECASE),               "联系 / 客服",         "📧"),
    (_re_mod.compile(r"/(customers?|case[-_]stud|stories)\b", _re_mod.IGNORECASE),        "客户案例",            "⭐"),
    (_re_mod.compile(r"/(solutions?|use[-_]?cases?|industries)\b", _re_mod.IGNORECASE),   "解决方案 / 场景",     "🎯"),
    (_re_mod.compile(r"/(ai|agent|assistant|employee|bot|copilot|bdr|sdr)[-_]", _re_mod.IGNORECASE), "AI 能力 / Agent", "🤖"),
    (_re_mod.compile(r"/(integrations?|integrate|connect|api|developer|sdk)\b", _re_mod.IGNORECASE), "集成 / API", "🔌"),
    (_re_mod.compile(r"/(security|trust|compliance|privacy)\b", _re_mod.IGNORECASE),      "安全 / 信任",         "🔒"),
    (_re_mod.compile(r"/(blog|news|insights?|press|media)\b", _re_mod.IGNORECASE),        "博客 / 内容",         "📰"),
    (_re_mod.compile(r"/(docs?|documentation|help|guide|wiki|kb|knowledge|faq)", _re_mod.IGNORECASE), "文档 / 帮助", "📖"),
    (_re_mod.compile(r"/(features?|product|how[-_]?it[-_]?works?)\b", _re_mod.IGNORECASE), "产品功能 / 介绍",    "✨"),
    (_re_mod.compile(r"/(meeting|calendar|schedul)", _re_mod.IGNORECASE),                 "日程 / 会议",         "📅"),
    (_re_mod.compile(r"/(404|not[-_]found)", _re_mod.IGNORECASE),                         "404 错误处理",        "❌"),
]
# Ordered priority for rendering — high-information modules first
MODULE_RENDER_ORDER = [
    "首页", "AI 能力 / Agent", "产品功能 / 介绍", "解决方案 / 场景",
    "客户案例", "定价 / 商业化", "注册 / 试用入口", "Demo / 销售对接",
    "集成 / API", "安全 / 信任", "日程 / 会议",
    "公司 / 团队", "招聘", "博客 / 内容", "文档 / 帮助",
    "联系 / 客服", "登录入口", "404 错误处理",
    "产品官方介绍（递归发现）",
    "登录后 Workspace（dashboard）",  # v1.7: render last in §4.2 — separator between public & private
    "其他", "未找到的测点",
]


def classify_module(finding: dict) -> tuple:
    """Return (module_label, emoji) for a finding.

    Strategy:
      1. B* test point IDs → 产品官方介绍 (recursive discovery)
      2. Empty URL or link_not_found → 未找到的测点
      3. URL has a real path (not /) → match against URL patterns
      4. URL still on homepage (text_scroll outcome) → match test_point_name
         against the same patterns (so "Pricing page" → 定价 even though it
         scrolled on homepage and URL stayed /).
      5. No match → 其他
    """
    tp_id = finding.get("test_point_id", "")
    if tp_id.startswith("B"):
        return ("产品官方介绍（递归发现）", "📚")
    # v1.7: L* test points are the logged-in dashboard / workspace audit
    if tp_id.startswith("L") and (len(tp_id) > 1 and tp_id[1:].isdigit()):
        return ("登录后 Workspace（dashboard）", "🔐")

    # link_not_found findings carry a homepage URL but their observations say
    # "[Link not found]". Pull them into a dedicated bucket so the module list
    # isn't polluted by failed lookups.
    obs_joined = " ".join(finding.get("observations", []))
    if "[Link not found]" in obs_joined or "Link not found]" in obs_joined:
        return ("未找到的测点", "⚠️")

    url = finding.get("url", "")
    if not url:
        return ("其他", "📌")

    try:
        from urllib.parse import urlparse
        path = urlparse(url).path or "/"
    except Exception:
        return ("其他", "📌")

    # When the test point landed on a real sub-page, classify by URL path
    if path and path != "/" and path != "":
        for regex, label, emoji in MODULE_PATTERNS:
            if regex.search(path):
                return (label, emoji)
        return ("其他", "📌")

    # URL is homepage (likely text_scroll outcome) — classify by test point name
    # so "Pricing page" → 定价, "Agent inventory" → AI 能力, etc.
    name = finding.get("test_point_name", "")
    name_path_proxy = "/" + name.lower().replace(" ", "-")  # convert "Pricing page" → "/pricing-page"
    for regex, label, emoji in MODULE_PATTERNS:
        if regex.search(name_path_proxy):
            return (label, emoji)
    # Truly homepage (C1 5-second test, footer audit) — keep as 首页
    if tp_id in ("C1", "C5") or "homepage" in name.lower() or "footer" in name.lower():
        return ("首页", "🏠")
    return ("其他", "📌")


def cluster_findings_by_module(findings: list) -> "OrderedDict":
    """Group findings into modules via classify_module, then order by MODULE_RENDER_ORDER."""
    from collections import OrderedDict
    by_module = OrderedDict()
    for f in findings:
        label, emoji = classify_module(f)
        if label not in by_module:
            by_module[label] = {"emoji": emoji, "findings": []}
        by_module[label]["findings"].append(f)

    # Reorder according to MODULE_RENDER_ORDER (anything not in the list goes at the end)
    ordered = OrderedDict()
    for label in MODULE_RENDER_ORDER:
        if label in by_module:
            ordered[label] = by_module.pop(label)
    # Catch any unexpected labels
    for label, data in by_module.items():
        ordered[label] = data
    return ordered


def render_findings_body(findings: list, workspace: Path) -> str:
    """Render the §4.2 体验流程详情 section, grouped by module (v1.6 A2)."""
    clusters = cluster_findings_by_module(findings)
    if not clusters:
        return "_无测点数据_"

    lines = []
    for module_label, data in clusters.items():
        emoji = data["emoji"]
        module_findings = data["findings"]
        lines.append(f"\n### {emoji} {module_label}（{len(module_findings)} 个测点）\n")

        # Quick-scan: list all URLs covered by this module
        urls = []
        for f in module_findings:
            u = f.get("url", "")
            if u and u not in urls:
                urls.append(u)
        if urls:
            lines.append("**该模块覆盖页面**:\n")
            for u in urls:
                lines.append(f"- `{u}`")
            lines.append("")

        # Per-test-point details
        for f in module_findings:
            lines.append(f"#### {f['test_point_id']}: {f['test_point_name']}\n")
            if f.get("url"):
                lines.append(f"**URL:** {f['url']}")
            if f.get("screenshot"):
                lines.append(f"\n![{f['test_point_id']}](./{f['screenshot']})\n")
            lines.append("**观察：**\n")
            for obs in f.get("observations", []):
                lines.append(f"- {obs}")
            lines.append("")
    return "\n".join(lines)


def render_issues_section(buckets: dict) -> str:
    """(DEPRECATED v1.13) Render the §4 problem inventory grouped by severity."""
    sections = []
    for sev, label in [("P1", "🔴 P1 严重"), ("P2", "🟡 P2 中等"), ("P3", "⚪ P3 轻微")]:
        if buckets[sev]:
            sections.append(f"### {label}（{len(buckets[sev])}）\n")
            for tp_id, obs in buckets[sev]:
                sections.append(f"- **[{tp_id}]** {obs}")
            sections.append("")
    if not sections:
        sections.append("_本轮未识别到明确分级的问题。所有观察均为中性/正面。请结合人工审核。_")
    return "\n".join(sections)


def render_executive_summary(meta: dict, findings: list[dict], buckets: dict) -> str:
    """One-paragraph executive summary."""
    p_count = sum(len(buckets[sev]) for sev in ["P1", "P2", "P3"])
    g_count = len(buckets["G"])
    return (
        f"本次评测目标产品 **{meta['url']}**，使用 **{meta['template']}** 模板在 "
        f"**{meta['depth']}** 深度档位下执行 **{meta['test_points_executed']}** 个测试点。\n\n"
        f"共识别问题 {p_count} 个（P1: {len(buckets['P1'])} / P2: {len(buckets['P2'])} / "
        f"P3: {len(buckets['P3'])}），正面发现 {g_count} 个。\n\n"
        f"详见 §4 完整流程记录。"
    )


def render_screenshots_index(findings: list[dict]) -> str:
    """Render the appendix screenshots index."""
    lines = []
    for f in findings:
        if f.get("screenshot"):
            lines.append(f"- `{f['screenshot']}` — {f['test_point_id']}: {f['test_point_name']}")
    return "\n".join(lines) if lines else "_无截图_"


def load_competitor_data(workspace: Path) -> Optional[dict]:
    """Load raw/competitors.json if it exists."""
    comp_file = workspace / "raw" / "competitors.json"
    if not comp_file.exists():
        return None
    try:
        return json.loads(comp_file.read_text())
    except Exception:
        return None


def _render_dict_table(rows: list[dict]) -> str:
    """Render a list of dicts (with same keys) as a Markdown table."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    md = ["| " + " | ".join(headers) + " |",
          "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        cells = [str(row.get(h, "")).replace("\n", " ").replace("|", "\\|") for h in headers]
        md.append("| " + " | ".join(cells) + " |")
    return "\n".join(md)


def render_competitor_section(workspace: Path, meta: dict) -> str:
    """Render the §6 横向对标 section from raw/competitors.json."""
    data = load_competitor_data(workspace)
    if data is None:
        return (
            "_本次未运行竞品调研（未找到 `raw/competitors.json`）。_\n\n"
            "如需补充竞品分析，请运行：\n"
            "```bash\n"
            f"python scripts/research_competitors.py --workspace {workspace.name} "
            "--competitors 'comp1.com,comp2.com'\n"
            "```"
        )

    if data.get("skipped"):
        return f"_竞品调研已跳过。原因: {data.get('reason', '未知')}。_"

    sections = []
    competitors = data.get("competitors", [])
    comparison = data.get("comparison", {})

    # 6.1 测试方法
    sections.append("### 6.1 竞品调研方法")
    sections.append(
        f"本次对比的目标产品是 **{data.get('target_url', meta['url'])}**，"
        f"对照 {len([c for c in competitors if not c.get('error')])} 个竞品。\n\n"
        f"调研深度：**{data.get('depth', 'n/a')}**。"
        f"调研方式：Claude 知识库 + 公开网页搜索"
        f"{'（含首页/定价页截图）' if any(c.get('screenshot') for c in competitors) else ''}。\n\n"
        "⚠️ 限制声明：竞品数据来自公开信息和 AI 推断，未对每个竞品进行完整的 audit 流程。"
        "若需高保真对比，请对每个竞品分别运行 product-audit 后人工合并。"
    )

    # 6.2 N+1 产品形态速览
    sections.append("\n### 6.2 N+1 产品形态速览")
    rows = []
    rows.append({
        "产品": f"**{meta['url']}**（target）",
        "定位": "（见 §1 产品概览）",
        "目标用户": "（见 §1 产品概览）",
        "核心壁垒": "（见 §3 体验流程）",
    })
    for c in competitors:
        if c.get("error"):
            continue
        rows.append({
            "产品": c.get("name", "Unknown"),
            "定位": c.get("positioning", "—"),
            "目标用户": c.get("target_user", "—"),
            "核心壁垒": c.get("unique_strength", "—"),
        })
    sections.append(_render_dict_table(rows))

    # 6.3 产物层 / 能力层对比
    cap_rows = comparison.get("capability_comparison_table") or []
    if cap_rows:
        sections.append("\n### 6.3 能力层对比")
        sections.append(_render_dict_table(cap_rows))

    # 6.4 形态对比表
    form_rows = comparison.get("form_comparison_table") or []
    if form_rows:
        sections.append("\n### 6.4 形态对比")
        sections.append(_render_dict_table(form_rows))

    # 6.5 评分对比
    score_rows = comparison.get("score_table") or []
    if score_rows:
        sections.append("\n### 6.5 综合评分对比（5 分制）")
        sections.append(_render_dict_table(score_rows))

    # 6.6 关键启示
    insights = comparison.get("insights") or {}
    if insights:
        sections.append("\n### 6.6 关键启示")
        learn = insights.get("target_should_learn") or []
        if learn:
            sections.append("\n**目标产品应当从竞品学习：**")
            for item in learn:
                sections.append(f"- {item}")
        moat = insights.get("target_moat") or []
        if moat:
            sections.append("\n**目标产品的不可复制护城河：**")
            for item in moat:
                sections.append(f"- {item}")
        scenario = insights.get("user_scenario_split")
        if scenario:
            sections.append(f"\n**用户场景分流：**\n\n> {scenario}")

    # 6.6b 评分矩阵图（Mermaid quadrant + bar chart）
    quad_chart = _render_score_quadrant(meta, score_rows)
    if quad_chart:
        sections.append("\n### 6.6b 综合定位矩阵（可视化）")
        sections.append(quad_chart)

    bar_chart = _render_score_bar_chart(meta, score_rows)
    if bar_chart:
        sections.append("\n### 6.6c 综合评分对比（可视化）")
        sections.append(bar_chart)

    # 6.7 竞品调研引用（含每家截图）
    sections.append("\n### 6.7 竞品调研细节（每竞品速览 + 截图）")
    for c in competitors:
        if c.get("error"):
            sections.append(f"\n#### {c.get('name', 'Unknown')}\n_调研失败: {c.get('error')}_")
            continue
        sections.append(f"\n#### {c.get('name', 'Unknown')}")
        if c.get("url"):
            sections.append(f"**URL:** {c['url']}")
        # Multi-screenshot support (v1.1): show all screenshots
        shots = c.get("screenshots") or ([{"page": "homepage", "file": c["screenshot"]}]
                                          if c.get("screenshot") else [])
        for shot in shots:
            page_label = shot.get("page", "screenshot")
            file = shot.get("file", "")
            if file:
                sections.append(f"\n**{page_label.capitalize()}:**\n")
                sections.append(f"![{c.get('name')} - {page_label}](./figs/{file})\n")
        if c.get("category"):
            sections.append(f"- **类别:** {c['category']}")
        if c.get("positioning"):
            sections.append(f"- **定位:** {c['positioning']}")
        if c.get("target_user"):
            sections.append(f"- **目标用户:** {c['target_user']}")
        if c.get("key_features"):
            sections.append("- **核心功能:**")
            for kf in c.get("key_features", []):
                sections.append(f"  - {kf}")
        if c.get("pricing_model"):
            sections.append(f"- **定价模式:** {c['pricing_model']}")
        if c.get("unique_strength"):
            sections.append(f"- **独家优势:** {c['unique_strength']}")
        if c.get("weakness_vs_target"):
            sections.append(f"- **vs 目标产品劣势:** {c['weakness_vs_target']}")

    return "\n".join(sections)


def _render_score_quadrant(meta: dict, score_rows: list[dict]) -> str:
    """Render a Mermaid quadrantChart from score data.

    Picks 2 representative dimensions for axes (first 2 non-comprehensive rows).
    """
    if not score_rows or len(score_rows) < 2:
        return ""

    # Identify dimension rows (exclude "综合" row) and find product names
    rows = [r for r in score_rows if "综合" not in str(r.get("维度", ""))]
    if len(rows) < 2:
        return ""

    # First row's keys (excluding "维度") are the products
    first = rows[0]
    products = [k for k in first.keys() if k != "维度"]
    if not products:
        return ""

    # Pick 2 axes from the dimension rows — first two
    x_dim = rows[0].get("维度", "维度1")
    y_dim = rows[1].get("维度", "维度2")

    def _parse_score(v) -> float:
        s = str(v).replace("*", "").replace("⭐", "").strip()
        try:
            return float(s) / 5.0  # normalize to 0-1
        except Exception:
            return 0.5

    lines = ["```mermaid", "quadrantChart"]
    lines.append(f"    title \"竞品定位矩阵：{x_dim} × {y_dim}\"")
    lines.append(f"    x-axis \"{x_dim} (低)\" --> \"{x_dim} (高)\"")
    lines.append(f"    y-axis \"{y_dim} (低)\" --> \"{y_dim} (高)\"")
    lines.append("    quadrant-1 \"全能型\"")
    lines.append("    quadrant-2 \"偏 X\"")
    lines.append("    quadrant-3 \"待改进\"")
    lines.append("    quadrant-4 \"偏 Y\"")
    for p in products:
        x = _parse_score(rows[0].get(p, 2.5))
        y = _parse_score(rows[1].get(p, 2.5))
        # Mark target with [] visually
        label = p.replace("https://", "").replace("http://", "").rstrip("/")[:30]
        lines.append(f"    \"{label}\": [{x:.2f}, {y:.2f}]")
    lines.append("```")
    return "\n".join(lines)


def _render_score_bar_chart(meta: dict, score_rows: list[dict]) -> str:
    """Render a Mermaid xychart for综合 score per product."""
    if not score_rows:
        return ""

    # Find the "综合" row (last) or compute from others
    comp_row = None
    for r in score_rows:
        if "综合" in str(r.get("维度", "")):
            comp_row = r
            break

    if not comp_row:
        # Compute avg from all dim rows
        dim_rows = [r for r in score_rows if "维度" in r]
        if not dim_rows:
            return ""
        comp_row = {"维度": "综合平均"}
        products = [k for k in dim_rows[0].keys() if k != "维度"]
        for p in products:
            scores = []
            for r in dim_rows:
                try:
                    s = float(str(r.get(p, "")).replace("*", "").replace("⭐", "").strip())
                    scores.append(s)
                except Exception:
                    pass
            comp_row[p] = round(sum(scores)/len(scores), 1) if scores else 0

    products = [k for k in comp_row.keys() if k != "维度"]
    if not products:
        return ""

    labels = [p.replace("https://", "").replace("http://", "").rstrip("/")[:20] for p in products]
    values = []
    for p in products:
        try:
            v = float(str(comp_row[p]).replace("*", "").replace("⭐", "").strip())
            values.append(round(v, 1))
        except Exception:
            values.append(0)

    lines = ["```mermaid", "xychart-beta"]
    lines.append(f"    title \"综合评分对比 (5 分制)\"")
    quoted_labels = ", ".join(f'"{l}"' for l in labels)
    lines.append(f"    x-axis [{quoted_labels}]")
    lines.append(f"    y-axis \"评分\" 0 --> 5")
    lines.append(f"    bar [{', '.join(str(v) for v in values)}]")
    lines.append("```")
    return "\n".join(lines)


def _render_one_line_verdict(meta: dict, buckets: dict) -> str:
    """Generate a one-line summary verdict."""
    p1, p2, p3 = len(buckets["P1"]), len(buckets["P2"]), len(buckets["P3"])
    g = len(buckets["G"])
    severity = "存在严重问题" if p1 > 0 else ("整体可用但有改进空间" if p2 > 3 else "整体表现稳健")
    return (
        f"目标产品 **{meta['url']}** 在 **{meta['template']}** 模板的 **{meta['depth']}** "
        f"档位评测下{severity}：识别问题 {p1+p2+p3} 个（P1 {p1} / P2 {p2} / P3 {p3}），"
        f"正面发现 {g} 个。详见 §4 体验流程详情。"
    )


def _render_overall_score_table(meta: dict, buckets: dict, background_count: int) -> str:
    """Generate the §1.2 兑现度 table (v1.10 surfaces login-mode coverage status)."""
    total = meta["test_points_executed"]
    p1, p2, p3 = len(buckets["P1"]), len(buckets["P2"]), len(buckets["P3"])
    rows = ["| 维度 | 兑现度 / 状态 |", "|---|---|"]
    rows.append(f"| 测点覆盖 | ✅ {total} / {meta.get('test_points_planned', total)} 点 |")
    rows.append(f"| 递归背景测点 | {'✅ ' + str(background_count) + ' 个介绍页（§2.3）' if background_count else '⚠️ 未发现 — 产品可能无 help/docs/resources 区域'} |")

    # v1.10 HARD RULE: surface login coverage status in the score table
    login_detected = meta.get("login_detected", False)
    login_mode_run = meta.get("login_mode_run", False)
    login_skipped = meta.get("login_skipped_by_user", False)
    n_dashboard = meta.get("login_mode_new_test_points", 0)
    if login_detected:
        if login_mode_run:
            rows.append(f"| 登录态覆盖 | ✅ 已捕获 + {n_dashboard} 个 dashboard 测点（§4.2 🔐 模块） |")
        elif login_skipped:
            rows.append(f"| 登录态覆盖 | ⚠️ **用户显式跳过** — 本报告为公开页 only（partial coverage） |")
        else:
            rows.append(f"| 登录态覆盖 | ❌ **缺失！** v1.10 HARD RULE 未满足：检测到登录入口但未跑 login-mode |")
    else:
        rows.append(f"| 登录态覆盖 | ➖ 未检测到登录入口（rule N/A）|")

    rows.append(f"| 严重问题 (P1) | {'❌ 有 ' + str(p1) + ' 个' if p1 else '✅ 无'} |")
    rows.append(f"| 中等问题 (P2) | {'⚠️ ' + str(p2) + ' 个' if p2 else '✅ 无'} |")
    rows.append(f"| 轻微问题 (P3) | {'⚪ ' + str(p3) + ' 个' if p3 else '✅ 无'} |")
    rows.append(f"| LLM 预算使用 | {meta['llm_calls_used']} / {meta['llm_calls_budget']} |")
    return "\n".join(rows)


def _render_top_risks(buckets: dict, n: int = 3) -> str:
    """Top N risks, drawn from P1 first then P2."""
    pool = buckets["P1"] + buckets["P2"]
    if not pool:
        return "_本轮未识别到明确分级的风险。建议结合人工审核。_"
    items = pool[:n]
    return "\n".join(f"{i+1}. **[{tp_id}]** {obs}" for i, (tp_id, obs) in enumerate(items))


def _render_top_opportunities(buckets: dict, n: int = 3) -> str:
    """Top N opportunities from positive findings (G bucket)."""
    pool = buckets["G"]
    if not pool:
        return "_本轮未自动识别明显正面发现。详细见 §4 完整流程记录。_"
    items = pool[:n]
    return "\n".join(f"{i+1}. **[{tp_id}]** {obs}" for i, (tp_id, obs) in enumerate(items))


def _render_quick_wins_summary(buckets: dict) -> str:
    """Quick wins from P2/P3 (easy fixes)."""
    pool = buckets["P2"] + buckets["P3"]
    if not pool:
        return "_本轮未识别到 Quick Wins 候选。_"
    rows = ["| # | 改进 | 来源 |", "|---|---|---|"]
    for i, (tp_id, obs) in enumerate(pool[:6], 1):
        rows.append(f"| QW-{i} | {obs[:100]} | [{tp_id}] |")
    return "\n".join(rows)


def _render_action_list(buckets: dict, severity: str) -> str:
    """Render bulleted list of issues for §7.4."""
    pool = buckets.get(severity, [])
    if not pool:
        return "├── _无_"
    lines = []
    for tp_id, obs in pool[:5]:
        short = obs[:80] + "..." if len(obs) > 80 else obs
        lines.append(f"├── [{tp_id}] {short}")
    return "\n".join(lines)


def _render_meta_advice(meta: dict, buckets: dict, background_count: int) -> str:
    """Skeleton meta-advice section."""
    advice = [
        f"1. **关注 P1 功能描述问题的优先处理** — 当前 {len(buckets['P1'])} 个严重的功能性清晰度问题需要尽快闭环",
        f"2. **完善产品介绍信息层** — 参考 §2.3 已发现的 {background_count} 个背景介绍页，确保所有官方介绍渠道一致、互相印证",
        f"3. **持续审计** — 建议每季度运行一次 product-audit 跟踪产品功能介绍演进",
    ]
    return "\n".join(advice)


def load_synthesis(workspace: Path) -> dict:
    """Read raw/synthesis.json (v1.5+). Returns empty dict if absent."""
    f = workspace / "raw" / "synthesis.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except Exception:
        return {}


def _render_scorecard_section(synthesis: dict) -> str:
    raw = (synthesis or {}).get("scorecard", "").strip()
    if not raw:
        return ("_本次未生成综合评分（synthesis pass 未运行或 LLM 预算耗尽）。_\n\n"
                "_重跑：`python3 audit.py ... ` 会在末尾自动追加 synthesis pass。_")
    return raw


def _render_strategic_abstractions_section(synthesis: dict) -> str:
    raw = (synthesis or {}).get("strategic_abstractions", "").strip()
    if not raw:
        return ("_本次未生成战略抽象（synthesis pass 未运行或 LLM 预算耗尽）。_")
    return raw


def _render_consolidated_risks_section(synthesis: dict) -> str:
    raw = (synthesis or {}).get("consolidated_risks", "").strip()
    if not raw:
        return ("_本次未生成综合风险归纳（synthesis pass 未运行或 LLM 预算耗尽）。"
                "见 §4 体验流程详情。_")
    return raw


def _render_narrative_summary_section(synthesis: dict) -> str:
    raw = (synthesis or {}).get("narrative_summary", "").strip()
    if not raw:
        return ("_本次未生成官网 Narrative 综合（synthesis pass 未运行或 LLM 预算耗尽）。_")
    return raw


def _render_growth_funnel_section(synthesis: dict) -> str:
    raw = (synthesis or {}).get("growth_funnel", "").strip()
    if not raw:
        return ("_本次未生成用户增长漏斗推断（synthesis pass 未运行或 LLM 预算耗尽）。_")
    return raw


def _render_community_feedback_section(synthesis: dict) -> str:
    """v1.15: render §5 第三方社区反馈 (Reddit / PH / HN / G2 — non-official)."""
    raw = (synthesis or {}).get("community_feedback", "").strip()
    if not raw:
        return ("_本次未生成第三方社区反馈（synthesis pass 未运行 / LLM 预算耗尽 / "
                "WebSearch 工具不可用）。建议人工到 Reddit / Product Hunt / HN / G2 核实。_")
    return raw


def _render_company_info_section(synthesis: dict) -> str:
    raw = (synthesis or {}).get("company_info", "").strip()
    if not raw:
        return ("_本次未生成公司基本信息（synthesis pass 未运行 / LLM 预算耗尽 / "
                "web search 工具不可用）。_")
    return raw


def _render_login_coverage_note(meta: dict) -> str:
    """v1.10: surface login-mode coverage status prominently in §2.2."""
    login_detected = meta.get("login_detected", False)
    login_mode_run = meta.get("login_mode_run", False)
    login_skipped = meta.get("login_skipped_by_user", False)
    indicators = meta.get("login_indicators", [])
    n_dashboard = meta.get("login_mode_new_test_points", 0)

    if not login_detected:
        return "> 🟢 未检测到登录入口；本报告即为完整覆盖。"
    if login_mode_run:
        return (f"> 🔐 **登录态覆盖：已完成**。检测到登录入口并捕获了 dashboard session，"
                f"追加 **{n_dashboard} 个 L\\* 测点**（详见 §4.2 🔐 登录后 Workspace 模块）。")
    if login_skipped:
        indicator_summary = "、".join(
            i.get("text") or i.get("host") or i.get("path", "?")
            for i in indicators[:3]
        )
        return (f"> ⚠️ **登录态覆盖：用户显式跳过**（`login_skipped_by_user=true`）。\n"
                f"> 检测到的登录入口：{indicator_summary}。\n"
                f"> 本报告仅为**公开页 partial coverage**——dashboard / workspace 内部能力未覆盖。"
                f"§4.2 🔐 模块为空。")
    # Detected but neither run nor skipped — HARD RULE violation
    indicator_summary = "、".join(
        i.get("text") or i.get("host") or i.get("path", "?")
        for i in indicators[:3]
    )
    return (
        f"> ❌ **登录态覆盖：缺失 — v1.10 HARD RULE 未满足！**\n"
        f"> 检测到登录入口（{indicator_summary}）但未跑 `--login-mode`。\n"
        f"> 此报告**不应作为完整评测**对待。请按以下步骤补齐：\n"
        f"> 1. `python3 capture_login.py --url <dashboard URL> --output <ws>/.auth/storage_state.json`\n"
        f"> 2. `python3 audit.py --url <dashboard URL> --template ... --depth ... --workspace <ws> "
        f"--storage-state <ws>/.auth/storage_state.json --login-mode`\n"
        f"> 3. `python3 generate_report.py --workspace <ws> --formats md,html`"
    )


def _render_background_section(findings: list) -> str:
    """Render the §2.3 product/company background section from B* test points."""
    bg_findings = [f for f in findings if f.get("test_point_id", "").startswith("B")]
    if not bg_findings:
        return (
            "_本次未通过递归挖掘发现产品 / 公司的官方介绍页面。可能产品没有 help / docs / "
            "resources 板块，或这些板块下没有显式的 \"What is X / Getting Started\" 入口。_\n\n"
            "_如需扩大递归深度，可改用 `--depth deep` 重跑（最多 15 个背景介绍页）。_"
        )

    lines = [
        f"通过 help / docs / resources 内容枢纽**递归挖掘**得到 **{len(bg_findings)}** "
        f"个产品/公司的官方介绍页面：\n"
    ]
    for f in bg_findings:
        lines.append(f"#### {f['test_point_id']}: {f['test_point_name']}\n")
        if f.get("url"):
            lines.append(f"**URL:** {f['url']}\n")
        if f.get("screenshot"):
            lines.append(f"![{f['test_point_id']}](./{f['screenshot']})\n")
        lines.append("**结构化背景信息（LLM 提取）：**\n")
        for obs in f.get("observations", []):
            lines.append(f"- {obs}")
        lines.append("")
    return "\n".join(lines)


def generate_md_report(workspace: Path) -> str:
    """Generate the markdown report content."""
    import platform

    meta, findings = load_workspace(workspace)
    buckets = categorize_findings(findings)
    background_count = sum(1 for f in findings if f.get("test_point_id", "").startswith("B"))
    synthesis = load_synthesis(workspace)

    # Build environment string
    env_str = f"{platform.system()} {platform.release()} / Python {platform.python_version()}"

    body = REPORT_TEMPLATE_MD.format(
        product_name=meta["url"].replace("https://", "").replace("http://", "").rstrip("/"),
        url=meta["url"],
        completed_at=meta["completed_at"],
        template=meta["template"],
        depth=meta["depth"],
        test_points_count=meta["test_points_executed"],
        background_count=background_count,
        llm_calls_used=meta["llm_calls_used"],
        llm_calls_budget=meta["llm_calls_budget"],
        language=meta["language"],
        first_title=findings[0]["raw_text_excerpt"][:80] if findings else "(no title)",
        experimenter=meta.get("experimenter", "product-audit Skill（自动化）"),
        environment=env_str,
        one_line_verdict=_render_one_line_verdict(meta, buckets),
        overall_score_table=_render_overall_score_table(meta, buckets, background_count),
        top_risks=_render_top_risks(buckets),
        top_opportunities=_render_top_opportunities(buckets),
        quick_wins_summary=_render_quick_wins_summary(buckets),
        scorecard_section=_render_scorecard_section(synthesis),
        login_coverage_note=_render_login_coverage_note(meta),
        background_section=_render_background_section(findings),
        strategic_abstractions_section=_render_strategic_abstractions_section(synthesis),
        company_info_section=_render_company_info_section(synthesis),
        narrative_summary_section=_render_narrative_summary_section(synthesis),
        findings_body=render_findings_body(findings, workspace),
        growth_funnel_section=_render_growth_funnel_section(synthesis),
        community_feedback_section=_render_community_feedback_section(synthesis),
        # v1.13: issues_section + screenshots_index removed (原 §4 问题清单 + 附录 deleted)
        generated_at=datetime.now().isoformat(),
    )
    return body


def _render_recommendations(buckets: dict) -> str:
    """Quick recommendations based on found issues."""
    recs = []
    if buckets["P1"]:
        recs.append("**优先处理 P1 级问题** — 这些会阻断核心用户流程：")
        for tp_id, obs in buckets["P1"][:5]:
            recs.append(f"- [{tp_id}] {obs}")
    if buckets["P2"]:
        recs.append("\n**P2 中期改进** — 影响用户体验印象：")
        for tp_id, obs in buckets["P2"][:5]:
            recs.append(f"- [{tp_id}] {obs}")
    if not recs:
        recs.append("_本轮未自动识别出明确问题。建议结合 §4 完整流程记录做人工审核。_")
    return "\n".join(recs)


def _render_summary(meta: dict, buckets: dict) -> str:
    return (
        f"本次评测共执行 {meta['test_points_executed']} 个测试点，覆盖 {meta['template']} 模板。\n\n"
        f"关键数据：\n"
        f"- 问题总数：P1 {len(buckets['P1'])} / P2 {len(buckets['P2'])} / P3 {len(buckets['P3'])}\n"
        f"- 正面发现：{len(buckets['G'])}\n"
        f"- LLM 预算使用：{meta['llm_calls_used']} / {meta['llm_calls_budget']}"
    )


def generate_html_report(workspace: Path, md_content: str) -> str:
    """Generate HTML report with embedded screenshots and proper Markdown→HTML rendering."""
    import re

    # Step 1: Replace markdown image refs with base64 data URIs (do this on MD first)
    def img_to_data_uri(match):
        alt = match.group(1)
        rel_path = match.group(2).lstrip("./")
        img_file = workspace / rel_path
        if img_file.exists():
            data = base64.b64encode(img_file.read_bytes()).decode()
            return f"![{alt}](data:image/png;base64,{data})"
        return match.group(0)

    md_with_imgs = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", img_to_data_uri, md_content)

    # Step 2: Convert Markdown → HTML using python-markdown with rich extensions
    try:
        import markdown
        md = markdown.Markdown(extensions=[
            "tables",         # GitHub-style tables
            "fenced_code",    # ```code``` blocks
            "toc",            # auto-generate TOC IDs for headers (enables anchor links)
            "nl2br",          # newlines → <br> in paragraphs (good for terse audit findings)
            "sane_lists",     # better list handling
            "admonition",     # > callout blocks
        ])
        body_html = md.convert(md_with_imgs)
        # Convert fenced code blocks tagged "mermaid" into <div class="mermaid"> so mermaid.js picks them up
        import re as _re
        body_html = _re.sub(
            r'<pre><code class="language-mermaid">(.*?)</code></pre>',
            r'<div class="mermaid">\1</div>',
            body_html,
            flags=_re.DOTALL,
        )
        # Unescape HTML entities inside mermaid blocks (python-markdown escapes them)
        def _unescape_mermaid(m):
            content = m.group(1)
            content = (content
                       .replace("&amp;", "&")
                       .replace("&lt;", "<")
                       .replace("&gt;", ">")
                       .replace("&quot;", '"')
                       .replace("&#39;", "'"))
            return f'<div class="mermaid">{content}</div>'
        body_html = _re.sub(
            r'<div class="mermaid">(.*?)</div>',
            _unescape_mermaid,
            body_html,
            flags=_re.DOTALL,
        )
    except ImportError:
        # Graceful degradation: wrap in <pre> if markdown lib missing
        body_html = f"<pre style='white-space:pre-wrap;'>{md_with_imgs}</pre>"

    # Step 3: Wrap with clean, modern document styling + Mermaid for matrix charts
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product Audit Report</title>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
</script>
<style>
  :root {{
    --fg: #1a1a1a;
    --fg-muted: #666;
    --accent: #0a3a6e;
    --accent-light: #e8eef5;
    --bg: #fafbfc;
    --code-bg: #f3f4f6;
    --border: #e0e0e0;
    --risk: #d63031;
    --warn: #f5a623;
    --good: #00b894;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue",
                 system-ui, "Segoe UI", Roboto, sans-serif;
    max-width: 980px;
    margin: 0 auto;
    padding: 2rem 2.5rem 4rem;
    line-height: 1.7;
    color: var(--fg);
    background: var(--bg);
    font-size: 15px;
  }}

  h1, h2, h3, h4, h5, h6 {{
    color: var(--accent);
    margin-top: 2em;
    margin-bottom: 0.6em;
    line-height: 1.3;
    font-weight: 600;
  }}
  h1 {{ font-size: 2.2em; margin-top: 0.5em; border-bottom: 3px solid var(--accent); padding-bottom: 0.4em; }}
  h2 {{ font-size: 1.7em; border-bottom: 1px solid var(--border); padding-bottom: 0.35em; margin-top: 2.5em; }}
  h3 {{ font-size: 1.3em; }}
  h4 {{ font-size: 1.1em; color: var(--fg); }}

  p {{ margin: 0.6em 0; }}

  a {{ color: var(--accent); text-decoration: none; border-bottom: 1px dotted var(--accent); }}
  a:hover {{ border-bottom-style: solid; }}

  ul, ol {{ padding-left: 1.5em; margin: 0.6em 0; }}
  li {{ margin: 0.25em 0; }}

  table {{
    border-collapse: collapse;
    margin: 1.2em 0;
    width: 100%;
    font-size: 0.93em;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}
  th, td {{
    border: 1px solid var(--border);
    padding: 0.55em 0.8em;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    background: var(--accent-light);
    font-weight: 600;
    color: var(--accent);
  }}
  tr:nth-child(even) td {{ background: #fafafa; }}

  code {{
    background: var(--code-bg);
    padding: 0.15em 0.45em;
    border-radius: 4px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.9em;
    color: #c7254e;
  }}
  pre {{
    background: var(--code-bg);
    padding: 1em 1.2em;
    border-radius: 6px;
    overflow-x: auto;
    border: 1px solid var(--border);
    line-height: 1.5;
  }}
  pre code {{ background: transparent; padding: 0; color: var(--fg); }}

  blockquote {{
    border-left: 4px solid var(--accent);
    background: var(--accent-light);
    padding: 0.7em 1.2em;
    margin: 1.2em 0;
    color: var(--fg);
    border-radius: 0 4px 4px 0;
  }}
  blockquote p:first-child {{ margin-top: 0; }}
  blockquote p:last-child {{ margin-bottom: 0; }}

  hr {{ border: none; border-top: 1px solid var(--border); margin: 2.5em 0; }}

  img {{
    max-width: 100%;
    height: auto;
    border: 1px solid var(--border);
    border-radius: 6px;
    margin: 1em 0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  }}

  .mermaid {{
    background: white;
    padding: 1.5em;
    border-radius: 6px;
    margin: 1.5em 0;
    border: 1px solid var(--border);
    text-align: center;
    overflow-x: auto;
  }}
  .mermaid svg {{ max-width: 100%; height: auto; }}

  /* TOC styling */
  ul:has(> li > a) {{ background: white; padding: 1em 1.5em 1em 2em; border: 1px solid var(--border); border-radius: 6px; }}

  /* Severity emoji visual cues */
  /* When body text contains 🔴 P1 — highlight risk; 🟡 P2 — medium; ⚪/✅ — neutral/good */
  /* Currently kept as inline emoji; CSS does not need to do more */

  /* Section anchor offset for sticky scroll */
  h2, h3 {{ scroll-margin-top: 1em; }}

  @media print {{
    body {{ background: white; max-width: 100%; padding: 1em; }}
    img {{ max-width: 90%; }}
    h1, h2 {{ page-break-after: avoid; }}
    table, pre, blockquote {{ page-break-inside: avoid; }}
  }}

  @media (max-width: 720px) {{
    body {{ padding: 1rem; font-size: 14px; }}
    table {{ font-size: 0.85em; }}
    th, td {{ padding: 0.4em 0.5em; }}
  }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
    return html


def cleanup_workspace(workspace: Path) -> None:
    """v1.13: keep ONLY figs/ + report.md + report.html. Remove everything else.

    This is destructive — once cleanup runs, you cannot regenerate the report
    from raw data. Use --keep-raw to skip cleanup.

    Specifically removes:
      - raw/  (findings.jsonl + synthesis.json)
      - .auth/  (storage_state.json from capture_login)
      - audit-meta.json  (run metadata)

    Preserved:
      - figs/  (all screenshots)
      - report.md
      - report.html
    """
    import shutil
    removed = []
    for sub in ["raw", ".auth"]:
        d = workspace / sub
        if d.exists() and d.is_dir():
            shutil.rmtree(d)
            removed.append(sub + "/")
    meta = workspace / "audit-meta.json"
    if meta.exists():
        meta.unlink()
        removed.append("audit-meta.json")
    if removed:
        print(f"🧹 Cleaned: {', '.join(removed)} (kept figs/ + report.md + report.html only)")


def main():
    parser = argparse.ArgumentParser(description="Generate audit report")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--formats", default="md,html", help="Comma-separated: md, html")
    parser.add_argument("--keep-raw", action="store_true",
                        help="v1.13: SKIP cleanup. By default, after generating report.md "
                             "+ report.html, raw/, .auth/, and audit-meta.json are DELETED "
                             "to leave the workspace with only figs/ + md + html. Use this "
                             "flag if you need to regen the report later from raw data.")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not (workspace / "audit-meta.json").exists():
        print(f"❌ No audit-meta.json in {workspace}. Run audit.py first.")
        return 1

    formats = [f.strip() for f in args.formats.split(",")]

    md_content = generate_md_report(workspace)

    if "md" in formats:
        md_path = workspace / "report.md"
        md_path.write_text(md_content)
        print(f"✅ Wrote {md_path}")

    if "html" in formats:
        html_content = generate_html_report(workspace, md_content)
        html_path = workspace / "report.html"
        html_path.write_text(html_content)
        print(f"✅ Wrote {html_path}")

    # v1.13: default cleanup — keep only figs/ + report.md + report.html
    if not args.keep_raw:
        cleanup_workspace(workspace)
    else:
        print(f"📁 Kept raw data (--keep-raw set)")

    print(f"\n📦 Workspace: {workspace}")
    return 0


if __name__ == "__main__":
    exit(main())
