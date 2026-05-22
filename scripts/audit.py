"""Main audit orchestration script.

Invoked by SKILL.md. Drives the Browser Agent + LLM loop:
- Loads a template
- Iterates its test points within the depth budget
- For each test point: action + screenshot + LLM interpretation
- Persists findings to raw/findings.jsonl
- Calls generate_report.py at the end

Usage:
    python audit.py --url URL --template TEMPLATE --depth DEPTH \\
                    --workspace DIR --language LANG
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ====== Recursive Background-Info Discovery (v1.4) ======
# When the main audit + auto-explore is done, drill into "content hubs"
# (help / docs / resources) to find pages that explicitly introduce the
# product/company. The classic example: artisan.co → Resources → Help Center
# → Getting Started → "What Is Artisan? A Quick Overview".
#
# Two regex layers:
#   HUB_PATH_REGEX        — matches paths like /help, /docs, /resources, etc.
#                            (also matched against hub subdomains like help.X)
#   BACKGROUND_LINK_REGEX — matches link texts/paths that signal
#                            "this is an intro page" (What is X / Getting
#                            Started / Overview / Welcome / Intro).
HUB_PATH_REGEX = re.compile(
    r"/(help|docs?|documentation|resources?|learn|guide[s]?|wiki|"
    r"knowledge|support|faq|kb|tutorial[s]?|academy|university)",
    re.IGNORECASE,
)

HUB_SUBDOMAIN_REGEX = re.compile(
    r"^(help|docs?|support|learn|wiki|knowledge|kb|guide|tutorials?|academy|university)\.",
    re.IGNORECASE,
)

BACKGROUND_LINK_REGEX = re.compile(
    r"(what\s*is|what['s\s]+(it|that)|overview|introduction|introducing|"
    r"getting\s*started|intro(duction)?\s+to|"
    r"about\s+(this|the|us|the\s+product)|quick\s*overview|product\s*tour|"
    r"how\s*it\s*works?|how\s*does.{1,10}work|"
    r"welcome|first\s*steps?|onboarding|getting\s*to\s*know|"
    r"begin(ner)?['s\s]+guide|start\s*here|product\s*introduction|"
    r"what\s+can.{1,20}(do|build)|"
    r"是什么|快速了解|快速入门|新手指南|产品介绍|平台介绍|开始使用)",
    re.IGNORECASE,
)

# Budget per depth: how many background-intro pages to capture
BACKGROUND_BUDGET = {"express": 0, "standard": 6, "deep": 15}
# How many distinct hubs to descend into (each hub may yield N intro pages)
HUB_DESCENT_BUDGET = {"express": 0, "standard": 4, "deep": 8}
# Max recursion depth WITHIN a hub. Real example: help.artisan.co →
# "Getting Started" collection (depth 1) → "What Is Artisan? A Quick
# Overview" article (depth 2). So depth=2 is the minimum useful value.
RECURSION_DEPTH = {"express": 0, "standard": 2, "deep": 3}

# Import the local browser wrapper (relative import handled by sys.path)
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from browser import BrowserSession  # noqa: E402
from llm import call as llm_call, is_available as llm_available, backend_name  # noqa: E402


# Depth tier budgets (tool calls = LLM interpretation calls)
DEPTH_BUDGET = {
    "express": {"max_test_points": 15, "max_llm_calls": 50, "report_target_words": 2000},
    "standard": {"max_test_points": 30, "max_llm_calls": 200, "report_target_words": 6500},
    "deep": {"max_test_points": 60, "max_llm_calls": 500, "report_target_words": 15000},
}


# Centralized test point catalog. Each entry: id → {name, action, ...args, min_depth}
ALL_TEST_POINTS: dict = {
    # ====== Common test points (C1-C8) — all templates include ======
    "C1": {"name": "Homepage 5-second test", "action": "navigate", "url_suffix": "/", "min_depth": "express"},
    "C2": {"name": "Pricing page", "action": "find_link", "link_text": "pricing|定价|價格", "min_depth": "express"},
    "C3": {"name": "Sign-up flow (no submit)", "action": "find_link", "link_text": "sign up|signup|get started|start free|注册|免费试用|开始", "min_depth": "express"},
    "C4": {"name": "Login page", "action": "find_link", "link_text": "log in|login|sign in|登录|登入", "min_depth": "standard"},
    "C5": {"name": "Footer audit", "action": "scroll_bottom", "min_depth": "express"},
    "C7": {"name": "Help / Documentation", "action": "find_link", "link_text": "help|docs|documentation|support|帮助|文档", "min_depth": "standard"},
    "C8": {"name": "404 error handling", "action": "try_404", "min_depth": "standard"},

    # ====== SaaS-specific (S1-S15) ======
    "S1": {"name": "Features / Product page", "action": "find_link", "link_text": "features|product|product tour|功能|产品", "min_depth": "express"},
    "S2": {"name": "Use cases / Industry", "action": "find_link", "link_text": "use case|industries|solutions|应用场景|行业", "min_depth": "standard"},
    "S3": {"name": "Integrations page", "action": "find_link", "link_text": "integration|connect|集成|连接", "min_depth": "express"},
    "S4": {"name": "Customer / logo wall", "action": "find_link", "link_text": "customers|clients|case studies|客户|案例", "min_depth": "express"},
    "S5": {"name": "Case studies / Testimonials", "action": "find_link", "link_text": "case stud|testimonials|stories|案例|客户故事", "min_depth": "standard"},
    "S6": {"name": "Blog / Resources", "action": "find_link", "link_text": "blog|resources|insights|博客|资源", "min_depth": "standard"},
    "S7": {"name": "About / Company", "action": "find_link", "link_text": "about|company|关于|公司", "min_depth": "express"},
    "S8": {"name": "Careers", "action": "find_link", "link_text": "careers|jobs|招聘", "min_depth": "deep"},
    "S9": {"name": "API / Developer docs", "action": "find_link", "link_text": "api|developer|docs.|开发者", "min_depth": "standard"},
    "S12": {"name": "Trust / Security page", "action": "find_link", "link_text": "security|trust|compliance|安全|信任", "min_depth": "standard"},
    "S14": {"name": "Customer support channels", "action": "find_link", "link_text": "contact|support|帮助|联系", "min_depth": "standard"},

    # ====== Multi-Agent-specific (M1-M15) ======
    "M1": {"name": "Agent inventory / team page", "action": "find_link", "link_text": "agents|employees|team|ai team|workforce", "min_depth": "express"},
    "M2": {"name": "Agent profile (sample)", "action": "find_link", "link_text": "meet|introducing|navigator|alice|sophia|ava|ai bdr", "min_depth": "standard"},
    "M3": {"name": "Use cases / Workflows", "action": "find_link", "link_text": "use case|workflow|how it works|功能演示", "min_depth": "express"},
    "M5": {"name": "Skills / Capabilities", "action": "find_link", "link_text": "skills|capabilities|tools|integrations", "min_depth": "standard"},
    "M6": {"name": "Channel deployment (Telegram/WhatsApp/Slack)", "action": "find_link", "link_text": "channel|deploy|integrations", "min_depth": "standard"},

    # ====== AI-Tool-specific (A1-A5) ======
    "A1": {"name": "Main input / chat interface", "action": "find_link", "link_text": "try|demo|chat|start|开始体验", "min_depth": "express"},
    "A2": {"name": "Example prompts / Templates", "action": "find_link", "link_text": "examples|templates|gallery|示例", "min_depth": "standard"},
    "A3": {"name": "Tool capabilities disclosure", "action": "find_link", "link_text": "capabilities|tools|what it can do|功能", "min_depth": "standard"},

    # ====== E-commerce-specific (E1-E10) ======
    "E1": {"name": "Product browse / categories", "action": "find_link", "link_text": "shop|browse|catalog|商品|分类", "min_depth": "express"},
    "E2": {"name": "Product detail page", "action": "find_link", "link_text": "shop|product|see all|view all", "min_depth": "standard"},
    "E5": {"name": "Cart page", "action": "find_link", "link_text": "cart|basket|购物车", "min_depth": "standard"},
    "E9": {"name": "Shipping / Delivery info", "action": "find_link", "link_text": "shipping|delivery|配送|物流", "min_depth": "standard"},
    "E10": {"name": "Returns / Refunds policy", "action": "find_link", "link_text": "return|refund|退货|退款", "min_depth": "standard"},
}


# Per-template test point selection
TEMPLATE_TEST_POINTS = {
    "saas": ["C1", "C2", "C3", "C4", "C5", "C7", "C8",
             "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S12", "S14"],
    "multi-agent": ["C1", "C2", "C3", "C4", "C5", "C7", "C8",
                    "M1", "M2", "M3", "M5", "M6",
                    "S1", "S3", "S4", "S7", "S9", "S12", "S14"],
    "ai-tool": ["C1", "C2", "C3", "C4", "C5", "C7", "C8",
                "A1", "A2", "A3", "S1", "S4", "S6", "S9", "S12"],
    "ecommerce": ["C1", "C2", "C3", "C4", "C5", "C7", "C8",
                  "E1", "E2", "E5", "E9", "E10", "S4", "S14"],
}


def _depth_order(depth: str) -> int:
    return {"express": 0, "standard": 1, "deep": 2}.get(depth, 0)


@dataclass
class Finding:
    """One observation from one test point."""
    test_point_id: str
    test_point_name: str
    timestamp: str
    url: str
    screenshot: Optional[str]
    observations: list[str]
    severity: Optional[str]  # P0/P1/P2/P3/G/None
    raw_text_excerpt: str


def load_template(template_name: str, depth: str) -> dict:
    """Build the actual ordered list of test points for a given template + depth.

    Pulls from TEMPLATE_TEST_POINTS (per-template IDs) and ALL_TEST_POINTS (definitions),
    then filters by `min_depth` to respect the depth tier budget.
    """
    if template_name not in TEMPLATE_TEST_POINTS:
        print(f"⚠️  Template '{template_name}' not found, falling back to 'saas'")
        template_name = "saas"

    requested_depth_level = _depth_order(depth)
    test_points = []
    for tp_id in TEMPLATE_TEST_POINTS[template_name]:
        defn = ALL_TEST_POINTS.get(tp_id)
        if not defn:
            continue
        if _depth_order(defn.get("min_depth", "express")) > requested_depth_level:
            continue
        # Build a flat dict with id + name + action + extra args
        tp = {"id": tp_id, **defn}
        test_points.append(tp)

    return {
        "name": template_name,
        "test_points": test_points,
        "report_sections": ["overview", "issues", "recommendations"],
    }


def interpret_with_llm(screenshot_path: Path, page_text: str, test_point: dict) -> list[str]:
    """Ask Claude to interpret a test point — FUNCTIONAL audit focus.

    Returns a list of observation strings. If LLM is unavailable, returns a
    placeholder noting manual review needed.

    This prompt deliberately steers Claude AWAY from UI/visual critique
    (button placement, color, layout aesthetics, mobile responsiveness) and
    TOWARD product-feature understanding: what does the product DO, what
    capabilities are demonstrated, how does it solve user problems.
    """
    if not llm_available():
        return [f"[LLM unavailable — manual review of {screenshot_path.name} needed]"]

    prompt = (
        f"你正在进行**产品功能**审计（不是 UI 评测）。聚焦产品**做什么、能做什么、解决什么问题**。\n\n"
        f"测点: {test_point['name']} (ID: {test_point['id']})\n"
        f"页面文本节选:\n{page_text[:2200]}\n\n"
        f"请提供 3-5 条关于**产品功能层**的中文观察，覆盖以下角度（不必每条都写，挑最有信息量的）：\n"
        f"1. 这个页面**揭示了产品的什么功能 / 能力 / 工作流**？\n"
        f"2. 它**解决用户什么具体问题**？典型使用场景是什么？\n"
        f"3. 关键功能细节（**输入 / 输出 / 集成 / 适用场景 / 工作机制**）是否说明清楚？\n"
        f"4. 用户读完这一页，**能否理解\"这个产品能为我做什么\"**？\n"
        f"5. **功能信息缺口** — 想了解但页面没说的功能关键点是什么？\n\n"
        f"严重度标记（**仅针对功能性清晰度**问题）：\n"
        f"- **P1** 严重: 关键功能描述缺失 / 误导（例: \"P1 未说明 AI agent 如何接入 CRM\"）\n"
        f"- **P2** 中等: 功能信息不完整（例: \"P2 缺少集成清单\"）\n"
        f"- **P3** 轻微: 功能细节可改进（例: \"P3 不同套餐的功能差异未说明\"）\n"
        f"- **✅** 正面: 功能介绍清晰有力（例: \"✅ 用具体场景演示了 AI BDR 工作流\"）\n\n"
        f"❌ **严禁评论以下话题**（这不是 UI / UX 评测）：\n"
        f"- 界面美观度、字体大小、按钮样式、颜色搭配、布局对称、留白\n"
        f"- 移动端 / 桌面端 UI 适配\n"
        f"- \"界面简洁\"\"设计现代\"\"视觉吸引\"等审美评价\n\n"
        f"只返回 bulleted list（用 -、* 或数字开头），不要前言。"
    )

    text = llm_call(prompt, max_tokens=1024)
    if text.startswith("["):  # error message
        return [text]
    return [line.strip().lstrip("-*•1234567890. ") for line in text.split("\n")
            if line.strip().startswith(("-", "*", "•", "1", "2", "3", "4", "5"))][:5] or [text[:300]]


def interpret_background_with_llm(screenshot_path: Path, page_text: str, test_point: dict) -> list[str]:
    """Specialized prompt for background / company-intro pages (B* test points).

    These pages are typically reached by recursive descent into help/docs/resources
    and explicitly introduce what the product/company IS. We extract structured
    background info rather than evaluating UI.
    """
    if not llm_available():
        return [f"[LLM unavailable — manual review of {screenshot_path.name} needed]"]

    prompt = (
        f"这是产品/公司的**背景介绍页面**（通过 help/docs/resources 递归挖出来的）。"
        f"目标是**结构化提取产品背景信息**，不是评测页面。\n\n"
        f"页面: {test_point['name']}\n"
        f"页面文本节选:\n{page_text[:3500]}\n\n"
        f"请提供 4-6 条中文观察，覆盖以下角度（挑页面真正讲到的写，没讲到就不写）：\n"
        f"1. **产品 / 公司一句话定义** — 该页面如何定义这个产品 / 公司？尽可能引用页面原文。\n"
        f"2. **核心功能能力** — 列出页面提及的产品核心功能 / 能力（最多 5 个，简明列表）。\n"
        f"3. **目标用户与场景** — 该页面描述的目标用户、典型使用场景。\n"
        f"4. **差异化主张 / 独家叙事** — 有没有强调与同类产品的差异？品牌核心叙事？\n"
        f"5. **关键术语 / 概念** — 产品独有术语（如 \"AI BDR\"、\"AI Employee\"、\"Workflow Agent\"），各自含义。\n"
        f"6. **理解缺口** — 用户读完后仍然不清楚的关键点。\n\n"
        f"用 **✅** 前缀标记清晰有力的背景信息，**P3** 前缀标记可改进的描述。\n"
        f"❌ 不要评论 UI 设计、视觉风格、移动端体验。\n"
        f"只返回 bulleted list（用 -、* 或数字开头），不要前言。"
    )

    text = llm_call(prompt, max_tokens=1200)
    if text.startswith("["):
        return [text]
    return [line.strip().lstrip("-*•1234567890. ") for line in text.split("\n")
            if line.strip().startswith(("-", "*", "•", "1", "2", "3", "4", "5", "6"))][:6] or [text[:400]]


def synthesis_pass(findings: list, workspace: Path, llm_calls_used: int,
                   max_llm_calls: int) -> tuple:
    """After all test points complete, do **6** cross-test synthesis LLM calls (v1.15).

    Produces:
      1. strategic_abstractions — 4-6 "X 化" narratives (§2.4)
      2. scorecard — 6-dim scoring on 5pt scale (§1.5)
      [3. consolidated_risks — REMOVED in v1.9]
      4. narrative_summary — keyword map + narrative techniques (§4.1)
      5. growth_funnel — 官网作用域 funnel, excludes L* (§6.4)
      6. company_info — WebSearch for funding/team (§2.5, v1.8 + v1.11 identity verify)
      7. community_feedback — WebSearch Reddit/PH/HN/G2 (§5, v1.15) — NON-OFFICIAL

    All output strings get saved to raw/synthesis.json. Returns (synthesis_dict,
    new_llm_calls_used). Returns (None, llm_calls_used) if budget is exhausted.
    """
    if max_llm_calls - llm_calls_used < 6:
        print(f"   ⚠️  synthesis skipped — LLM budget too low ({llm_calls_used}/{max_llm_calls}, "
              f"needs 6 free calls — v1.15 added synthesis #7 community_feedback)")
        return None, llm_calls_used

    if not llm_available():
        print("   ⚠️  synthesis skipped — LLM unavailable")
        return None, llm_calls_used

    # Build compact context from all findings, separating main vs background
    main_findings_blocks = []
    background_blocks = []
    p_observations = []  # for risk consolidation
    for f in findings:
        tp_id = f.get("test_point_id", "?")
        tp_name = f.get("test_point_name", "")
        url = f.get("url", "")
        obs_list = f.get("observations", [])
        block = f"[{tp_id}] {tp_name} ({url})\n" + "\n".join(f"  - {o}" for o in obs_list)
        if tp_id.startswith("B"):
            background_blocks.append(block)
        else:
            main_findings_blocks.append(block)
        for obs in obs_list:
            obs_low = obs.lower()[:10]
            if any(t in obs_low for t in ["p1", "p2", "p3"]) or any(t in obs[:6] for t in ["🔴", "🟡", "⚪"]):
                p_observations.append(f"[{tp_id}] {obs}")

    main_findings_text = "\n\n".join(main_findings_blocks)[:9000]
    background_text = "\n\n".join(background_blocks)[:3500]
    p_text = "\n".join(p_observations)[:11000]

    synthesis = {}

    # ===== 1. Strategic abstractions ("X 化" narratives) =====
    print("   ⚡ synthesis #1: strategic abstractions (X 化 叙事)...")
    prompt_strategic = (
        "你正在对一个产品做**战略层**综合分析。基于完整审计数据，"
        "请抽取 **4-6 个**「产品正在 X 化」形式的战略抽象方向。\n\n"
        "这是行业惯例：分析师会从产品的方向、定位、商业化、协作模式等角度，"
        "抽出 4-6 个 'X 化' 标签来概括产品本质。\n\n"
        "**参考示例（Moxt 人工分析）**：\n"
        "- AI Team 化（AI 不是工具，是团队成员）\n"
        "- Workspace 化（围绕 workspace 而不是 chat）\n"
        "- Shared Memory 化\n"
        "- Slack 工作流化（嵌入 Slack 生态）\n"
        "- Credits 商业化\n\n"
        "**参考示例（Artisan 人工分析）**：\n"
        "- AI Employee 化\n- AI SDR 化\n- Workflow 化\n- Persona 化\n- Autonomous 化\n\n"
        "=== 产品主审计观察 ===\n" + main_findings_text + "\n\n"
        "=== 产品方官方介绍（递归发现的背景页面）===\n" + background_text + "\n\n"
        "请输出 **4-6 条**战略抽象，每条严格按以下格式：\n\n"
        "### N. <X 化的名称>\n"
        "**核心叙事**: 1 句话概括\n"
        "**支撑证据**: \n"
        "- [测点ID] 证据 1\n- [测点ID] 证据 2\n- (可选) [测点ID] 证据 3\n"
        "**对用户/产品的含义**: 1 句话说明这个 X 化对用户意味着什么\n\n"
        "**严格要求**：\n"
        "- 标题用 **中文 + (English term)** 双语，例如「AI Employee 化 (AI Employee-ification)」\n"
        "- 每条必须有真实测点 ID 引用作为证据（不允许编造）\n"
        "- 不要重复同一概念（避免出现「AI Employee 化」和「AI 员工化」两个相似项）\n\n"
        "只返回这 4-6 条，不要前言、不要结论。"
    )
    text1 = llm_call(prompt_strategic, max_tokens=2200)
    synthesis["strategic_abstractions"] = text1
    llm_calls_used += 1

    # ===== 2. Multi-dim scorecard (5pt scale, 6 dimensions) =====
    print("   ⚡ synthesis #2: 6-dim 综合评分 (5 分制)...")
    prompt_scorecard = (
        "你正在为产品做**综合评分**。基于完整审计数据，对以下 6 个维度按 5 分制评分。\n\n"
        "**评分标准**：\n"
        "- 5.0 / 5.0 = 行业顶级 / 完美\n"
        "- 4.0 / 5.0 = 优秀 / 显著好于平均\n"
        "- 3.0 / 5.0 = 合格 / 行业平均水平\n"
        "- 2.0 / 5.0 = 偏弱 / 有明显缺陷\n"
        "- 1.0 / 5.0 = 差 / 严重不足\n"
        "- 精确到 **0.5 分**\n\n"
        "**6 个评分维度**（不要新增、不要漏）：\n"
        "1. **产品方向清晰度** — 产品要做什么 / 不做什么 是否一目了然\n"
        "2. **Narrative 表达力** — 价值主张和叙事是否有力、可信\n"
        "3. **信息架构（IA）** — 信息层级、导航、子页组织是否清晰\n"
        "4. **功能广度与深度** — 功能覆盖面是否够、关键功能是否解释深入\n"
        "5. **AI / 核心能力可信度** — 产品声称的 AI / 核心能力是否有可信证据支撑\n"
        "6. **商业化清晰度** — 定价模式、套餐分层、计费单位是否清晰\n\n"
        "=== 产品审计观察 ===\n" + main_findings_text + "\n\n"
        "=== 产品方官方介绍 ===\n" + background_text + "\n\n"
        "**严格输出格式**（只返回这个 markdown table）：\n\n"
        "| 维度 | 评分 | 1-2 句话说明（引用具体 [测点ID]） |\n"
        "|---|---:|---|\n"
        "| 产品方向清晰度 | X.X / 5 | ... |\n"
        "| Narrative 表达力 | X.X / 5 | ... |\n"
        "| 信息架构（IA） | X.X / 5 | ... |\n"
        "| 功能广度与深度 | X.X / 5 | ... |\n"
        "| AI / 核心能力可信度 | X.X / 5 | ... |\n"
        "| 商业化清晰度 | X.X / 5 | ... |\n"
        "| **综合平均** | **X.X / 5** | **1 句话综合判定** |\n\n"
        "不要前言、不要分析、只返回表格。"
    )
    text2 = llm_call(prompt_scorecard, max_tokens=1500)
    synthesis["scorecard"] = text2
    llm_calls_used += 1

    # ===== 3. (REMOVED v1.9) Consolidated product-level risks =====
    # The "综合性产品级风险" synthesis has been removed by user request.
    # Rationale: too prescriptive/editorial — the report should surface raw
    # observations + structural analysis, not redo what the §4 detailed
    # P1/P2/P3 inventory already provides. §0.3 Top 3 风险 already gives a
    # short factual highlight from buckets, which is sufficient.
    # The function _render_consolidated_risks_section remains in generate_report.py
    # but is no longer called by the template.

    # ===== 4. Narrative summary (v1.6) — 官网叙事手法 + 关键词图谱 =====
    # Filter findings to marketing-y URLs (homepage, about, solutions, customers,
    # ai-*, features, product) so the LLM doesn't get distracted by pricing/signup.
    marketing_url_re = re.compile(
        r"(^/$|^$|/about|/features?\b|/product\b|/why|/solutions?\b|/customers?\b|"
        r"/case[-_]stud|/use[-_]?cases?|/(ai|agent|assistant|employee|bot|copilot)[-_]|"
        r"/team|/story|/manifesto|/mission)",
        re.IGNORECASE,
    )
    marketing_blocks = []
    for block, finding in zip(main_findings_blocks, [f for f in findings if not f.get("test_point_id", "").startswith("B")]):
        url = finding.get("url", "")
        if not url:
            continue
        # Strip origin to get path
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path or "/"
        except Exception:
            path = url
        if marketing_url_re.search(path):
            marketing_blocks.append(block)
    marketing_text = "\n\n".join(marketing_blocks)[:8500]

    print("   ⚡ synthesis #4: 官网 Narrative 综合 (叙事手法 + 关键词图谱)...")
    prompt_narrative = (
        "你正在分析产品**官网的叙事手法**。基于以下营销页 / 介绍页观察，"
        "总结产品官方的叙事风格、关键词图谱和叙事手法。\n\n"
        "**这是行业惯例的 §3.5 章节**：分析师会从官网的语言、用词、修辞、"
        "示例选择中，反推产品方想要建立什么样的认知。\n\n"
        "**参考输出范式（来自 Artisan 人工分析）**：\n"
        "- 关键词图谱：Future of Work / AI Presence / Sales Workspace / Modern / Minimal\n"
        "- 叙事手法：否定式定位（\"isn't just another...\"）+ 数字背书 + 拟人化命名\n\n"
        "=== 营销页 / 介绍页观察 ===\n" + marketing_text + "\n\n"
        "=== 产品方官方介绍 ===\n" + background_text + "\n\n"
        "请严格按以下结构输出（markdown）：\n\n"
        "#### 关键词图谱\n\n"
        "| 关键词 / 短语 | 频次或权重 | 在哪类页面出现 | 想建立的认知 |\n"
        "|---|---|---|---|\n"
        "| (6-10 个最有信号的关键词，按权重排序) |\n\n"
        "#### 叙事手法分析\n\n"
        "列出 3-5 个该产品使用的叙事手法，每条格式：\n\n"
        "**1. 手法名称（中英双语）**\n"
        "- 具体表现：引用一句原文 [测点ID]\n"
        "- 效果意图：1 句话\n\n"
        "#### 整体叙事评价\n\n"
        "1-2 句话总结：这个产品想让用户**感觉**它是什么？这种叙事的可信度如何？\n\n"
        "不要前言、不要 '以下是分析' 这种话，直接出内容。"
    )
    text4 = llm_call(prompt_narrative, max_tokens=2000)
    synthesis["narrative_summary"] = text4
    llm_calls_used += 1

    # ===== 5. Growth funnel inference (v1.6, v1.9 restricted to 官网 only) =====
    # v1.9 change: funnel analysis is now scoped to MARKETING-LAYER only:
    #   - Marketing pages whose URL matches pricing/signup/demo/onboard hints
    #   - All B* background pages (still public help content, not behind login)
    #   - EXPLICITLY EXCLUDES L* dashboard findings (user said: "只是官网的漏斗分析")
    growth_url_re = re.compile(
        r"(/pricing|/plans?|/signup|/sign[-_]up|/get[-_]started|/start\b|"
        r"/trial|/free|/demo|/request|/onboard|/billing|/upgrade|/invite|/team)",
        re.IGNORECASE,
    )
    growth_blocks = []
    # Build a parallel array of (block, finding) for ONLY non-B*, non-L* findings
    marketing_findings = [f for f in findings
                          if not f.get("test_point_id", "").startswith("B")
                          and not (f.get("test_point_id", "").startswith("L")
                                   and f.get("test_point_id", "")[1:].isdigit())]
    # Re-derive marketing-only blocks (main_findings_blocks includes L*; we need to exclude them)
    marketing_only_blocks = []
    for f in marketing_findings:
        tp_id = f.get("test_point_id", "?")
        tp_name = f.get("test_point_name", "")
        url = f.get("url", "")
        obs_list = f.get("observations", [])
        block_text = f"[{tp_id}] {tp_name} ({url})\n" + "\n".join(f"  - {o}" for o in obs_list)
        marketing_only_blocks.append((block_text, f))

    for block, finding in marketing_only_blocks:
        url = finding.get("url", "")
        if not url:
            continue
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path or "/"
        except Exception:
            path = url
        if growth_url_re.search(path):
            growth_blocks.append(block)
    # Also include all B* (background pages often describe activation/onboarding)
    growth_blocks.extend(background_blocks)
    growth_text = "\n\n".join(growth_blocks)[:8500]

    print("   ⚡ synthesis #5: 用户增长漏斗推断 (官网作用域 — 不含 dashboard)...")
    prompt_growth = (
        "你正在**推断**一个产品的**官网作用域**用户增长漏斗。**只基于公开页面**"
        "（pricing / signup / demo / onboarding 表单 / 背景介绍页）的观察，"
        "推断这个产品的：\n\n"
        "1. **用户增长路径**：从看到官网到成为注册用户 / 试用用户的关键节点\n"
        "2. **激活机制**：访客可见的 \"Aha moment\" 信号（基于页面叙述，不依赖 dashboard 数据）\n"
        "3. **商业化转化路径**：免费 → 付费的关键决策点（pricing 页 + 套餐结构）\n"
        "4. **触发购买 / 试用的钩子**：免费额度 / Demo 表单 / 试用入口的设计\n\n"
        "⚠️ **重要作用域限制**：\n"
        "- **只用官网 + 公开介绍页数据**，不要引用任何 L\\* 编号的登录态测点\n"
        "- 不要分析\"团队扩散 / 邀请成员 / 多席位\"等需要登录后才能观察的环节\n"
        "- 不要推断\"长期留存机制\"等需要看 dashboard / billing / settings 才能判断的内容\n"
        "- 这是**未注册访客视角**的漏斗——只到 signup / demo / trial 入口为止\n\n"
        "**注意**：这是\"推断\"，不是事实复述。明确标注哪些是页面直接陈述、哪些是你的推断。\n\n"
        "=== Pricing / Signup / Demo / Background 观察（仅官网） ===\n" + growth_text + "\n\n"
        "请严格按以下结构输出（markdown）：\n\n"
        "#### 官网增长漏斗推断图\n\n"
        "```\n"
        "Stage 1: <名称> (e.g. 落地页认知)\n"
        "    ↓ 关键触点: <来自 [测点ID] 的证据>\n"
        "Stage 2: <名称> (e.g. 评估页 / 定价对比)\n"
        "    ↓ 关键触点: ...\n"
        "Stage 3-N: ... (终止于注册 / Demo 申请 / 试用入口)\n"
        "```\n\n"
        "**作用域**：只到访客**完成转化进入产品**为止（注册 / Demo 表单提交 / 试用启动）。"
        "登录后的 onboarding / activation / 留存请勿包含。\n\n"
        "#### 关键漏斗节点详解\n\n"
        "对每个 Stage 写一段（**3-5 个 Stage**）：\n\n"
        "**Stage N: <名称>**\n"
        "- 页面陈述：（直接观察到的） [测点ID]\n"
        "- 我的推断：（基于陈述的推论）\n"
        "- 潜在流失点：用户可能在这一步流失的原因\n\n"
        "#### 转化设计观察\n\n"
        "- **入口设计**：Demo 表单 vs 自助试用 vs 立即注册 的对比与权衡\n"
        "- **价格 / 套餐心智锚点**：访客读完 pricing 页后会怎样判断成本\n"
        "- **可见的 Aha 承诺**：官网用什么话语承诺 \"用了之后会发生什么\"（不是登录后真实体验）\n\n"
        "#### 漏斗设计的强弱判断（仅官网层面）\n\n"
        "用 ✅ / ⚠️ / ❌ 列 3-5 条评价。\n\n"
        "不要前言。**严禁**引用 L* 测点或任何登录后的内容。"
    )
    text5 = llm_call(prompt_growth, max_tokens=2400)
    synthesis["growth_funnel"] = text5
    llm_calls_used += 1

    # ===== 6. Company basic info via web search (v1.8) =====
    # Pull factual context (founding / funding / team) from external sources
    # since the audit itself only sees the company's own marketing pages.
    # This aligns with §1.1 of human-authored product analysis reports.
    print("   ⚡ synthesis #6: 公司基本信息 (web search — 融资 / 团队 / 上线时间)...")

    # Extract company domain from audit-meta.json or first finding
    from urllib.parse import urlparse
    product_url = ""
    meta_path = workspace / "audit-meta.json"
    if meta_path.exists():
        try:
            product_url = json.loads(meta_path.read_text()).get("url", "")
        except Exception:
            pass
    if not product_url:
        for f in findings:
            if f.get("url"):
                product_url = f["url"]
                break

    try:
        parsed = urlparse(product_url)
        netloc = (parsed.hostname or product_url).replace("www.", "")
        # Trim down to eTLD+1: dashboard.artisan.co → artisan.co
        domain_parts = netloc.split(".")
        company_domain = ".".join(domain_parts[-2:]) if len(domain_parts) >= 2 else netloc
    except Exception:
        company_domain = product_url

    # Pull product-name hints from background pages (most authoritative source)
    product_name_hints = ""
    for f in findings:
        if f.get("test_point_id", "").startswith("B"):
            obs = " ".join(f.get("observations", []))
            if obs:
                product_name_hints += obs[:600] + "\n"
        if len(product_name_hints) > 2000:
            break

    prompt_company = (
        "你需要为产品审计报告生成 §1.5 公司基本信息章节。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "⚠️  最重要的事 — 实体身份验证 (v1.11)\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "**很多产品名称会重名或相似**。例如 'Pika' 可能指：\n"
        "  - pika.me / pika.art / Pika Labs (AI 视频生成)\n"
        "  - Pikachu / Pika Networks / Pika Capital 等数十个无关实体\n\n"
        "**你绝对不能**在没有验证身份之前，把任何融资 / 团队 / 上线时间归属到\n"
        "本次审计的产品上。错误归属比无信息更糟糕，因为它误导决策者。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "目标产品（这是你唯一应该写的实体；其他重名的不要混入）：\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        f"- 主域名: **{company_domain}**\n"
        f"- 完整 URL: {product_url}\n\n"
        f"产品方自家页面观察（用于提取真实公司名 / 产品概念，作为身份锚点）：\n"
        f"---\n{product_name_hints[:1800]}\n---\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "强制执行的 4 步身份验证流程\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "**Step 1: 提取身份锚点**\n"
        "从产品自家页面观察中识别：\n"
        "  - 真实公司名（看 footer / about / privacy 等）\n"
        "  - 真实产品概念（页面对自己的定义，例如 'AI BDR' / 'AI 视频生成器'）\n"
        "  - 域名（已给定: " + company_domain + "）\n\n"
        "**Step 2: 域名锚定搜索（必须用 site: 操作符 + 域名 exact-match）**\n"
        "优先级（按顺序尝试）：\n"
        f"  1. `site:{company_domain}`  ← 直接抓官网\n"
        f"  2. `\"{company_domain}\" funding` / `\"{company_domain}\" series A B`\n"
        f"  3. `\"{company_domain}\" linkedin company` / `\"{company_domain}\" crunchbase`\n"
        f"  4. `\"{company_domain}\" founder` / `\"{company_domain}\" CEO`\n\n"
        "**禁用**：纯名称搜索（如 'Pika funding'）——会拉回错的公司。\n"
        "如果一定要用名称搜，必须配合产品概念限定（如 'Pika AI agent funding' 而非 'Pika funding'）。\n\n"
        "**Step 3: 身份交叉验证**\n"
        "搜到的候选公司必须满足以下至少一个匹配条件才能采信：\n"
        f"  ✅ Crunchbase / LinkedIn / Twitter 公司页面**显式列出** `{company_domain}` 作为官网链接\n"
        f"  ✅ 公司新闻稿 / TechCrunch 报道中**引用** `{company_domain}` 这个 URL\n"
        f"  ✅ 创始人 LinkedIn / GitHub / Twitter bio **链接到** `{company_domain}`\n"
        "  ⚠️  如果搜到的公司「名称匹配但官网链接是别的域名」（如 pika.art 不等于 pika.me）：\n"
        "     这是**不同的公司**，丢掉这些信息。\n\n"
        "**Step 4: 如果无法确认实体身份**\n"
        "如果 Step 3 全部失败（搜索结果指向多个候选 / 找不到与本域名挂钩的资料），\n"
        "**不要编造任何 fact**。改为输出以下 \"需要用户确认\" 模板：\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "格式 A — 身份确认通过（Step 3 至少 1 个 ✅ 信号）\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "#### ✅ 实体身份已确认\n\n"
        f"经过域名 + 产品描述 + LinkedIn/Crunchbase 交叉验证，本次审计对象 `{company_domain}` 对应：\n"
        "**<公司全名>**（来源: <具体 URL 锚链接到本域名的证据>）\n\n"
        "#### 公司基础事实表\n\n"
        "| 项 | 内容 | 置信度 | 来源 |\n"
        "|---|---|---|---|\n"
        "| 公司名称 | ... | ✅ 直接 | <url> |\n"
        "| 成立年份 | ... | ✅/⚠️ | <url> |\n"
        "| 总部地点 | ... | ✅/⚠️ | <url> |\n"
        "| 产品上线 | ... | ✅/⚠️ | <url> |\n"
        "| 当前阶段 | Seed / Series A / B / C / Public / 未公开 | ✅/⚠️ | <url> |\n"
        "| 融资总额 | $X M+ | ✅/⚠️ | <url> |\n"
        "| 团队规模 | ~N 人 | ⚠️ (估算来源差异大) | <url> |\n"
        "| 行业类别 | ... | ✅ | <url> |\n\n"
        "**置信度图例**：✅ = 来源直接锚链接到 {domain} / ⚠️ = 间接推断或来源不一致 / ❌ = 不要写这行，应写 '未找到'\n\n"
        "#### 融资历史\n\n"
        "| 轮次 | 时间 | 金额 | 领投 + 主要参与方 | 来源指向本域名? |\n"
        "|---|---|---|---|---|\n"
        "| Seed | ... | ... | ... | ✅/⚠️ |\n"
        "| Series A | ... | ... | ... | ✅/⚠️ |\n\n"
        "#### 创始人 / 核心团队背景\n\n"
        "对核心创始人和高管（最多 4-5 人）逐条列：\n"
        "- **姓名** (职位) — 上一份工作 / 学历 / 任何相关背景 [来源]\n"
        "  - 验证：该人 LinkedIn 个人页或新闻是否提到 `{company_domain}`？(✅/⚠️)\n\n"
        "#### 近期重大动态（最近 6-12 个月）\n\n"
        "- 日期: 事件 [来源] (验证: 报道是否提到本域名? ✅/⚠️)\n"
        "- (3-5 条最重要的)\n\n"
        "#### 综合判断\n\n"
        "用 1-2 段话总结：公司当前阶段、资本与团队优势 / 短板、值得关注的方向。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "格式 B — 身份无法确认（Step 3 失败）\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "#### ⚠️ 实体身份未能确认 — 需要用户手动核实\n\n"
        f"WebSearch 未能找到把 `{company_domain}` 与某一具体公司**显式挂钩**的资料。\n"
        "可能是该产品比较新 / 公开报道少 / 名称与多家公司重叠。\n\n"
        "**搜索过程发现的候选实体**（仅供参考，未确认与本域名的关系）：\n\n"
        "| 候选实体 | 域名 | 主要业务 | 与本审计域名的匹配度 | 来源 |\n"
        "|---|---|---|---|---|\n"
        "| <候选 1> | <域名> | ... | ⚠️ 名称匹配但域名不同 | <url> |\n"
        "| <候选 2> | ... | ... | ❌ 不匹配 | <url> |\n\n"
        "**请用户核实**：请确认 `{company_domain}` 对应的公司主体，或提供以下任一信息以重跑：\n"
        "- 公司 LinkedIn URL\n"
        "- Crunchbase profile URL  \n"
        "- 公司在 TechCrunch / VentureBeat 的报道 URL\n"
        "- 创始人姓名 + LinkedIn\n\n"
        "本节将留作空白；建议人工回填后再发布报告。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "其他严格要求\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "- 不要前言（如「以下是分析」）\n"
        "- 搜索证据请用 markdown 链接形式 [name](url)\n"
        "- 单条信息找不到时写「未找到 / 未公开」而不是省略整行\n"
        "- 训练截止时间之后融资可能有变化，必须以 WebSearch 实时结果为准\n"
    ).replace("{domain}", company_domain).replace("{company_domain}", company_domain)
    # Web search calls can take 60-240s — bump timeout + pre-approve WebSearch/WebFetch
    # so the headless `claude -p` doesn't get blocked on permission prompts.
    text6 = llm_call(
        prompt_company,
        max_tokens=4000,
        timeout=300,
        allowed_tools=["WebSearch", "WebFetch"],
    )
    synthesis["company_info"] = text6
    llm_calls_used += 1

    # ===== 7. Community feedback via web search (v1.15) =====
    # Pull NON-OFFICIAL third-party discussion (Reddit / Product Hunt /
    # Hacker News / G2 / Trustpilot) to surface real-user signal that
    # the company's own pages won't show. Same identity-anchoring rigor
    # as v1.11: domain-locked queries, real URL citations, no fabrication.
    print("   ⚡ synthesis #7: 第三方社区反馈 (Reddit / Product Hunt / HN / G2 — 非官方)...")
    prompt_community = (
        "你需要为产品审计报告生成 §5 第三方社区反馈章节。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "⚠️  这一节的特殊性质：信息来源是**非官方第三方平台**\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "和 §2.5 公司基本信息一样必须用 WebSearch 主动搜索，但**搜索范围限定在用户社区 /\n"
        "评论站**，不是公司新闻稿 / 官方融资报道。这一节专门展示**真实用户怎么说**，\n"
        "对照官方叙事 (§4.1 Narrative) 找出 gap。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "目标产品（仅搜这一个实体，避免重名混入）\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        f"- 主域名: **{company_domain}**\n"
        f"- 完整 URL: {product_url}\n\n"
        f"产品自家页面观察（用于提取真实产品概念作为搜索锚点）：\n"
        f"---\n{product_name_hints[:1500]}\n---\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "搜索策略 — 用域名 + 平台名锚定（避免拉到重名公司讨论）\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "**优先级（按可信度从高到低）**：\n\n"
        f"1. **Reddit** (任何 subreddit)\n"
        f"   - `\"{company_domain}\" site:reddit.com`\n"
        f"   - `site:reddit.com {company_domain.split('.')[0]}` 含产品概念限定\n\n"
        f"2. **Product Hunt**\n"
        f"   - `site:producthunt.com \"{company_domain}\"`\n"
        f"   - `\"{company_domain}\" \"product hunt\" launch`\n\n"
        f"3. **Hacker News**\n"
        f"   - `site:news.ycombinator.com \"{company_domain}\"`\n"
        f"   - 关注 Show HN / Ask HN 类型讨论\n\n"
        f"4. **G2 / Trustpilot / Capterra**（验证过的评价）\n"
        f"   - `site:g2.com \"{company_domain}\"` 或产品名\n"
        f"   - `site:trustpilot.com \"{company_domain}\"`\n\n"
        f"5. **可选：Twitter/X**（搜公开讨论 thread，注意时效性）\n\n"
        "**严格要求**：\n"
        "1. 必须用 WebSearch 主动搜索 — 不要凭知识库猜测\n"
        "2. **禁用裸名称搜索** — 若公司名通用（如 Pika），用 `产品名 + 产品概念` 限定\n"
        "3. 每条 finding 必须有**真实 URL 引用**（Reddit thread / PH page / HN comment 链接）\n"
        "4. 不能合并相似讨论编造一个共识 — 要保留个体讨论的原文 / 引用\n"
        "5. 搜不到讨论时输出 Format B 模板，**不要编造**\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "Format A — 找到社区讨论时的输出\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "#### 5.1 调研范围与方法\n\n"
        "简要说明：搜了哪些平台、找到多少条相关 thread / comment、覆盖时间窗。\n"
        "用 1 段话 + 列表形式。\n\n"
        "#### 5.2 核心议题（按讨论频次）\n\n"
        "| 议题 | 讨论方向（正面/负面/中性）| 出现频次 | 主要来源平台 |\n"
        "|---|---|---|---|\n"
        "| (3-6 条最常被讨论的议题) |\n\n"
        "#### 5.3 正面评价 / 用户喜欢的点\n\n"
        "3-5 条真实正面用户反馈，每条严格按以下格式：\n\n"
        "- **来源**: [平台 thread title](URL) — `u/username` 或 `用户名`, 日期\n"
        "  - **原文引用**: > 「...」\n"
        "  - **关键词**: ...\n\n"
        "#### 5.4 负面 / 批评 / 担忧\n\n"
        "同样 3-5 条真实负面或质疑反馈，格式同上。\n\n"
        "#### 5.5 与官方叙事的差异（vs §4.1 Narrative）\n\n"
        "用 1-2 段话指出：\n"
        "- 第三方讨论的产品形象，与官方 Narrative §4.1 描绘的形象，哪里**一致**，哪里有 **gap**\n"
        "- 若有重大 gap（如官网说 '行业标杆' 但 Reddit 大量抱怨），明确写出\n\n"
        "#### ⚠️ 信息来源声明\n\n"
        "本节所有内容来自**非官方第三方平台**（Reddit / Product Hunt / HN / G2 等）。\n"
        "内容可能含主观偏见、过时信息、个别用户的极端观点。\n"
        "决策时建议结合 §2.5 公司官方信息 + §4 实测观察综合判断。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "Format B — 未找到显著社区讨论时（v1.16: 极简）\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "#### ⚠️ 未找到显著社区讨论\n\n"
        f"WebSearch 在 Reddit / Product Hunt / Hacker News / G2 等平台未找到 `{company_domain}` 的\n"
        "显著用户讨论。本节为 null finding — 不代表产品质量好或差。\n\n"
        "**严格要求**：Format B 只输出上面这一段话，不要列重名公司、搜索 query 表、"
        "可能原因列表、人工核实链接等任何额外信息。保持极简。\n\n"
        "════════════════════════════════════════════════════════════════════════\n"
        "其他要求\n"
        "════════════════════════════════════════════════════════════════════════\n\n"
        "- 不要前言（如「以下是分析」）\n"
        "- 直接输出 markdown\n"
        "- 优先深度引用 2-3 个有信号的 thread，而不是肤浅扫一堆\n"
        "- 用户引用应该用 markdown blockquote (> ...) 而非直接句号断句\n"
    )
    text7 = llm_call(
        prompt_community,
        max_tokens=4500,
        timeout=400,
        allowed_tools=["WebSearch", "WebFetch"],
    )
    synthesis["community_feedback"] = text7
    llm_calls_used += 1

    # Save to disk so report can be regenerated without re-audit
    (workspace / "raw" / "synthesis.json").write_text(
        json.dumps(synthesis, ensure_ascii=False, indent=2)
    )
    print(f"   ✅ synthesis saved → raw/synthesis.json (6 LLM calls used, v1.15)")

    return synthesis, llm_calls_used


def _navigate_with_fallback(session: BrowserSession, url: str, total_budget_ms: int = 45000) -> bool:
    """Navigate with a fallback chain: domcontentloaded → load → commit.

    Slow marketing sites (and Zendesk-style help portals) often exceed
    a single timeout. Try cheaper wait states progressively. Returns True
    if any strategy succeeded.
    """
    half = max(total_budget_ms // 2, 12000)
    third = max(total_budget_ms // 3, 8000)
    for wait_for, timeout_ms in [("domcontentloaded", half), ("load", half), ("commit", third)]:
        try:
            session.navigate(url, wait_for=wait_for, timeout_ms=timeout_ms)
            return True
        except Exception:
            continue
    return False


# ====== HARD RULE (v1.10): Login-Interface Detection ======
# If the product has a login UI, the skill MUST run login-mode after the
# public audit. This function surfaces login indicators so generate_report
# and the orchestrating Claude can enforce the rule.
LOGIN_DETECT_REGEX = re.compile(
    r"(\blog[\s_-]?in\b|\bsign[\s_-]?in\b|\bsign[\s_-]?on\b|"
    r"\bmember[\s_-]?login\b|登录|登陆|"
    r"/login\b|/signin\b|/sign[-_]in\b|/auth\b|/oauth)",
    re.IGNORECASE,
)
APP_SUBDOMAIN_REGEX = re.compile(
    r"^(app|dashboard|admin|portal|account|my|workspace|console|hub)\.",
    re.IGNORECASE,
)


def detect_login_interface(nav_links: list, cross_subdomain_hubs: list,
                            session=None, base_url: str = "") -> tuple:
    """Scan Phase 0 outputs for login signals (v1.12: + URL probing).

    Returns (has_login, indicators). Three detection layers:
      1. Nav-link text / path matching login patterns (regex scan)
      2. Cross-subdomain hubs matching app/dashboard subdomain patterns
      3. (v1.12 NEW) Direct URL probing of common login paths — catches
         JS-driven CTAs (e.g. Kuse) and unlinked login pages (e.g. Okara)
         that don't appear as <a href> in the DOM nav scan.

    If session + base_url are provided, layer 3 will probe ~6 common URLs.
    """
    indicators = []

    # Layer 1: nav-link text or path matching login patterns
    for nl in nav_links:
        text = nl.get("text", "") or ""
        path = nl.get("path", "") or ""
        if LOGIN_DETECT_REGEX.search(text) or LOGIN_DETECT_REGEX.search(path):
            indicators.append({
                "kind": "nav-link",
                "text": text[:60],
                "path": path,
                "href": nl.get("href"),
            })

    # Layer 2: cross-subdomain hubs that smell like app subdomains
    for ch in cross_subdomain_hubs:
        host = ch.get("host", "") or ""
        if APP_SUBDOMAIN_REGEX.match(host):
            indicators.append({
                "kind": "app-subdomain",
                "host": host,
                "href": ch.get("href"),
                "text": ch.get("text", ""),
            })

    # Layer 3 (v1.12): URL probe — handles JS-driven CTAs + unlinked login pages
    if session is not None and base_url:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        netloc = parsed.hostname or ""
        base_host = netloc.replace("www.", "")
        parts = base_host.split(".")
        base_domain = ".".join(parts[-2:]) if len(parts) >= 2 else base_host
        origin = f"{parsed.scheme}://{netloc}"

        # Order: cheapest first (same-origin path probes), then expensive (subdomain DNS)
        probe_urls = [
            (f"{origin}/login", "path-probe"),
            (f"{origin}/signin", "path-probe"),
            (f"{origin}/sign-in", "path-probe"),
            (f"{origin}/auth", "path-probe"),
            (f"https://app.{base_domain}/", "subdomain-probe"),
            (f"https://dashboard.{base_domain}/", "subdomain-probe"),
        ]
        seen_in_l1l2 = {ind.get("href") for ind in indicators}
        for probe_url, kind in probe_urls:
            if probe_url in seen_in_l1l2:
                continue  # already caught by layer 1/2
            try:
                session.navigate(probe_url, wait_for="domcontentloaded", timeout_ms=10000)
                title = session.page.title() or ""
                is_404 = ("404" in title.lower() or "not found" in title.lower())
                if is_404:
                    continue
                # Real page found
                indicators.append({
                    "kind": kind,
                    "url": probe_url,
                    "title": title[:80],
                })
                # Quick stop if we found something solid
                if len(indicators) >= 5:
                    break
            except Exception:
                continue

    return (len(indicators) > 0, indicators[:10])


def discover_nav_links(session: BrowserSession, base_url: str) -> list:
    """At audit start, walk the homepage and collect all linkable sub-pages.

    Returns a list of {text, href, source} dicts representing real navigable URLs.
    These are later matched against test point patterns so we directly visit
    the sub-page (rather than just scrolling around the homepage).
    """
    if not _navigate_with_fallback(session, base_url, total_budget_ms=45000):
        print("    ⚠️  homepage navigation exhausted all fallbacks — nav discovery skipped")
        return [], []

    # Settle for any post-load layout (SPAs often hydrate after DCL)
    time.sleep(3.0)

    try:
        result = session.page.evaluate("""
            (baseUrl) => {
                const sameOrigin = [];
                const seenPaths = new Set();
                const crossSub = [];
                const seenCross = new Set();

                const baseUrlObj = new URL(baseUrl);
                const origin = baseUrlObj.origin;
                const baseHost = baseUrlObj.hostname.replace(/^www\\./, '');
                const parts = baseHost.split('.');
                const baseDomain = parts.length >= 2 ? parts.slice(-2).join('.') : baseHost;

                const hubPath = /\\/(help|docs?|documentation|resources?|learn|guide[s]?|wiki|knowledge|support|faq|kb|tutorial[s]?|academy|university)\\b/i;
                const hubSubdomain = /^(help|docs?|support|learn|wiki|knowledge|kb|guide|tutorials?|academy|university)\\./i;

                function addSameOrigin(el, source) {
                    if (!el || !el.href) return;
                    let href;
                    try { href = new URL(el.href, baseUrl).href; } catch(e) { return; }
                    if (!href.startsWith(origin)) return;
                    const path = href.replace(origin, '').split('#')[0].split('?')[0];
                    if (path === '' || path === '/') return;
                    if (seenPaths.has(path)) return;
                    seenPaths.add(path);
                    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
                    if (!text || text.length > 80) return;
                    sameOrigin.push({ text, href, path, source });
                }

                // === Same-origin nav / footer / main ===
                document.querySelectorAll(
                    'nav a[href], header a[href], [role="navigation"] a[href], ' +
                    '[class*="nav"] a[href], [class*="menu"] a[href]'
                ).forEach(a => addSameOrigin(a, 'nav'));
                document.querySelectorAll('footer a[href]').forEach(a => addSameOrigin(a, 'footer'));
                document.querySelectorAll('main a[href], section a[href]').forEach(a => {
                    const t = (a.innerText || '').trim();
                    if (t && t.length <= 30) addSameOrigin(a, 'main');
                });

                // === Cross-subdomain hubs (e.g. help.artisan.co, docs.X.com) ===
                document.querySelectorAll('a[href]').forEach(a => {
                    if (!a.href) return;
                    let url; try { url = new URL(a.href, baseUrl); } catch(e) { return; }
                    const host = url.hostname.replace(/^www\\./, '');
                    if (host !== baseDomain && !host.endsWith('.' + baseDomain)) return;
                    const isHubSub = hubSubdomain.test(host);
                    const isHubPath = hubPath.test(url.pathname);
                    if (!isHubSub && !isHubPath) return;
                    const cleanUrl = url.origin + url.pathname;
                    if (cleanUrl === origin + '/' || cleanUrl === origin) return;
                    if (seenCross.has(cleanUrl)) return;
                    seenCross.add(cleanUrl);
                    const text = (a.innerText || a.textContent || a.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
                    if (text.length > 120) return;
                    crossSub.push({
                        href: cleanUrl,
                        text: text,
                        path: url.pathname,
                        host: host,
                        source: isHubSub ? 'cross-subdomain' : 'same-origin-hub'
                    });
                });

                return { sameOrigin: sameOrigin, crossSub: crossSub };
            }
        """, base_url)
        return result.get("sameOrigin", [])[:40], result.get("crossSub", [])[:15]
    except Exception as e:
        print(f"    ⚠️  nav discovery JS error: {str(e)[:120]}")
        return [], []


def _match_nav_link(nav_links: list, patterns: list) -> dict:
    """Find best nav_link whose text matches any of the patterns (case-insensitive)."""
    if not nav_links or not patterns:
        return None
    import re as _re
    for pattern in patterns:
        regex = _re.compile(pattern, _re.IGNORECASE)
        # Prefer nav source over main source (higher signal)
        for source_priority in ["nav", "main", "footer"]:
            for link in nav_links:
                if link.get("source") != source_priority:
                    continue
                if regex.search(link.get("text", "")) or regex.search(link.get("path", "")):
                    return link
    return None


# Fallback hub patterns: when no /help|/docs|/resources found, these are
# the next-best places where product-introduction content tends to live.
FALLBACK_HUB_REGEX = re.compile(
    r"/(about|features?|product|how[\-_]?it[\-_]?works?|"
    r"solutions?|use[\-_]?cases?|why\b|story|manifesto|mission|"
    r"company|team|blog|news|insights?|learn)",
    re.IGNORECASE,
)


def discover_fallback_hubs(known_nav_links: list, visited_urls: set, max_n: int = 3) -> list:
    """When primary hub discovery returns 0, downgrade to these alternative
    sources of product-intro content (in rough priority order):
      /about > /features|/product > /how-it-works > /solutions > /blog
    Returns up to max_n candidates.
    """
    PRIORITY = [
        r"/about\b",                          # #1: company/product about page
        r"/(features?|product)\b",            # #2: feature/product page
        r"/how[\-_]?it[\-_]?works?",          # #3: how-it-works
        r"/(solutions?|use[\-_]?cases?)\b",   # #4: solutions
        r"/(why|story|manifesto|mission)\b",  # #5: brand narrative
        r"/(company|team)\b",                 # #6: company
        r"/(blog|news|insights?|learn)\b",    # #7: blog (last resort)
    ]
    candidates = []
    seen = set()
    for prio_re in PRIORITY:
        rx = re.compile(prio_re, re.IGNORECASE)
        for nl in known_nav_links:
            path = nl.get("path", "")
            href = nl.get("href", "")
            if not href or href in visited_urls or href in seen:
                continue
            if rx.search(path):
                seen.add(href)
                candidates.append({
                    "href": href,
                    "source": "fallback",
                    "text": nl.get("text", ""),
                    "path": path,
                })
                if len(candidates) >= max_n:
                    return candidates
    return candidates


def discover_hub_candidates(known_nav_links: list, cross_subdomain_hubs: list,
                             visited_urls: set) -> list:
    """Filter & merge pre-captured hub candidates from Phase 0.

    No browser navigation here — both inputs were gathered during the original
    homepage load in discover_nav_links. This avoids the slow re-navigate
    on sites with weak connection / large bundle.

    Returns ordered list of {href, source, text} candidates. Excludes any
    URL already visited by main loop / auto-explore.
    """
    candidates = []
    seen_hrefs = set()

    # Layer 1: same-origin nav links whose path matches HUB_PATH_REGEX
    for nl in known_nav_links:
        path = nl.get("path", "")
        if not HUB_PATH_REGEX.search(path):
            continue
        href = nl.get("href", "")
        if href in seen_hrefs or href in visited_urls:
            continue
        seen_hrefs.add(href)
        candidates.append({
            "href": href,
            "source": "nav",
            "text": nl.get("text", ""),
            "path": path,
        })

    # Layer 2: cross-subdomain hubs (captured during Phase 0)
    for c in cross_subdomain_hubs:
        if c["href"] in seen_hrefs or c["href"] in visited_urls:
            continue
        seen_hrefs.add(c["href"])
        candidates.append(c)

    return candidates


def discover_background_links(session: BrowserSession, hub_url: str,
                                already_visited: set) -> list:
    """At a hub page, find sub-pages that look like product introductions.

    Allows same eTLD+1 traversal (so help.artisan.co/getting-started/
    can link to itself or back to www.artisan.co/about).
    """
    if not _navigate_with_fallback(session, hub_url, total_budget_ms=50000):
        print(f"      ⚠️  could not load hub {hub_url} — all fallback waits exhausted")
        return []
    time.sleep(3.0)  # SPAs / help portals (Zendesk, Intercom) often hydrate slowly

    try:
        all_links = session.page.evaluate("""
            (baseUrl) => {
                const result = [];
                const seen = new Set();
                const baseUrlObj = new URL(baseUrl);
                const baseHost = baseUrlObj.hostname.replace(/^www\\./, '');
                const parts = baseHost.split('.');
                const baseDomain = parts.length >= 2 ? parts.slice(-2).join('.') : baseHost;
                document.querySelectorAll('a[href]').forEach(a => {
                    if (!a.href) return;
                    let url; try { url = new URL(a.href, baseUrl); } catch(e) { return; }
                    const host = url.hostname.replace(/^www\\./, '');
                    if (host !== baseDomain && !host.endsWith('.' + baseDomain)) return;
                    const cleanUrl = url.origin + url.pathname;
                    if (cleanUrl === baseUrl.split('?')[0].split('#')[0]) return;
                    if (seen.has(cleanUrl)) return;
                    seen.add(cleanUrl);
                    const text = (a.innerText || a.textContent || a.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
                    if (!text || text.length > 150) return;
                    result.push({ href: cleanUrl, text: text, path: url.pathname });
                });
                return result;
            }
        """, hub_url)
    except Exception:
        return []

    # Filter to background-intro patterns AND skip already-visited
    matches = []
    for link in all_links:
        if link["href"] in already_visited:
            continue
        text = link.get("text", "")
        path = link.get("path", "")
        if BACKGROUND_LINK_REGEX.search(text) or BACKGROUND_LINK_REGEX.search(path):
            matches.append(link)
    return matches


def execute_test_point(session: BrowserSession, test_point: dict, base_url: str,
                        nav_links: list = None) -> dict:
    """Execute a single test point. Returns raw data captured."""
    action = test_point["action"]
    raw = {"action": action, "screenshot": None, "url": None, "text": ""}
    nav_links = nav_links or []

    try:
        if action == "navigate":
            try:
                meta = session.navigate(base_url + test_point.get("url_suffix", ""))
                raw["url"] = meta["url"]
                raw["load_ms"] = meta["load_ms"]
            except Exception as e:
                # Page may have partially loaded — record warning but continue to screenshot
                raw["navigate_warning"] = str(e)[:200]
                raw["url"] = session.page.url
        elif action == "find_link":
            import re as _re_pat
            patterns = [p.strip() for p in test_point["link_text"].split("|") if p.strip()]
            outcome = None  # navigation | nav_match | anchor | section_scroll | text_scroll | not_found

            # Phase 0: direct navigation to matched nav-discovered sub-page (most reliable)
            matched_nav = _match_nav_link(nav_links, patterns)
            if matched_nav:
                try:
                    meta = session.navigate(matched_nav["href"], wait_for="domcontentloaded", timeout_ms=20000)
                    time.sleep(1.0)  # settle
                    raw["url"] = meta["url"]
                    raw["matched_pattern"] = matched_nav.get("text", "")
                    raw["matched_via"] = f"nav_discovery ({matched_nav.get('source', '?')})"
                    raw["nav_type"] = "nav_match"
                    outcome = "nav_match"
                    print(f"    ✓ resolved via nav_discovery → {matched_nav['path']}")
                except Exception as e:
                    raw["nav_match_error"] = str(e)[:200]

            # First navigate back to home for fallback strategies (only if Phase 0 didn't already navigate)
            if outcome is None:
                try:
                    session.navigate(base_url, timeout_ms=15000)
                except Exception:
                    pass
            url_before = session.page.url

            # Phase 1: try real cross-page <a> link click (skip if Phase 0 already worked)
            if outcome is None:
                for pattern in patterns:
                    try:
                        locator = session.page.locator(
                            f"a:text-matches('(?i){pattern}', 'i')"
                        ).first
                        if locator.count() == 0:
                            continue
                        href = (locator.get_attribute("href") or "").strip()
                        # Skip pure anchors here — handled in Phase 2 with explicit scroll
                        if href.startswith("#") or href == "" or "javascript:" in href:
                            continue
                        locator.click(timeout=3000)
                        session.page.wait_for_load_state("networkidle", timeout=10000)
                        url_after = session.page.url
                        if url_after.split("#")[0] != url_before.split("#")[0]:
                            raw["url"] = url_after
                            raw["matched_pattern"] = pattern
                            raw["nav_type"] = "real_navigation"
                            outcome = "navigation"
                            break
                    except Exception:
                        continue

            # Phase 2: scroll to a heading/section containing keyword
            # (prefer h2/h3 over arbitrary text — they're real sections, not nav links)
            if outcome is None:
                for pattern in patterns:
                    for selector_template in [
                        "h1:text-matches('(?i){p}', 'i')",
                        "h2:text-matches('(?i){p}', 'i')",
                        "h3:text-matches('(?i){p}', 'i')",
                        "section[id*='{p_lower}']",
                        "[id*='{p_lower}']",
                    ]:
                        try:
                            sel = selector_template.format(p=pattern, p_lower=pattern.lower().replace(" ", "-"))
                            loc = session.page.locator(sel).first
                            if loc.count() == 0:
                                continue
                            handle = loc.element_handle()
                            if handle is None:
                                continue
                            # Force scroll regardless of current visibility
                            session.page.evaluate(
                                "el => el.scrollIntoView({block: 'center', behavior: 'instant'})",
                                handle,
                            )
                            time.sleep(0.4)
                            raw["url"] = session.page.url
                            raw["matched_pattern"] = pattern
                            raw["matched_selector"] = sel
                            raw["nav_type"] = "section_scroll"
                            outcome = "section_scroll"
                            break
                        except Exception:
                            continue
                    if outcome:
                        break

            # Phase 3: fallback — iterate ALL text matches and find one whose scroll
            # actually moves the viewport (skips fixed navbar matches that don't scroll)
            if outcome is None:
                for pattern in patterns:
                    try:
                        regex = _re_pat.compile(pattern, _re_pat.IGNORECASE)
                        all_matches = session.page.get_by_text(regex)
                        match_count = min(all_matches.count(), 8)
                        if match_count == 0:
                            continue
                        for i in range(match_count):
                            try:
                                pre_y = session.page.evaluate("window.scrollY")
                                m = all_matches.nth(i)
                                handle = m.element_handle()
                                if handle is None:
                                    continue
                                session.page.evaluate(
                                    "el => el.scrollIntoView({block: 'center', behavior: 'instant'})",
                                    handle,
                                )
                                time.sleep(0.4)
                                post_y = session.page.evaluate("window.scrollY")
                                # Strict: only accept if viewport actually scrolled at least 200px
                                # (avoids accepting fixed-navbar / above-fold matches that don't move)
                                if abs(post_y - pre_y) > 200:
                                    raw["url"] = session.page.url
                                    raw["matched_pattern"] = pattern
                                    raw["nav_type"] = "text_scroll"
                                    raw["scroll_delta_px"] = post_y - pre_y
                                    raw["match_index"] = i
                                    outcome = "text_scroll"
                                    break
                            except Exception:
                                continue
                        if outcome:
                            break
                    except Exception:
                        continue

            # Phase 4: nothing worked
            if outcome is None:
                raw["link_not_found"] = test_point["link_text"]
                raw["url"] = session.page.url
                raw["nav_type"] = "not_found"
                raw["skip_screenshot"] = True
                print(f"    ⚠️  link/section not found: {test_point['link_text'][:60]}")
            else:
                print(f"    ✓ resolved via {outcome}")
        elif action == "scroll_bottom":
            # Improved: handle multiple scroll containers + verify scroll happened
            pre_y = session.page.evaluate("window.scrollY")
            session.page.evaluate("""
                () => {
                    // Try window scroll (typical case)
                    window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'});
                    // Also scroll any custom scrollable containers (some sites use main/div with overflow)
                    document.querySelectorAll('main, [class*="scroll"], [style*="overflow"]').forEach(el => {
                        if (el.scrollHeight > el.clientHeight) {
                            el.scrollTop = el.scrollHeight;
                        }
                    });
                }
            """)
            time.sleep(0.8)  # allow any lazy-load to settle
            post_y = session.page.evaluate("window.scrollY")
            raw["scroll_delta_px"] = post_y - pre_y
            raw["url"] = session.page.url
            # If scroll didn't actually move (very short page or scroll-locked), mark as such
            if post_y < 100 and pre_y < 100:
                raw["scroll_warning"] = "page too short or scroll-locked — footer screenshot may equal homepage"
        elif action == "mobile_view":
            # Switch viewport to mobile (iPhone 13: 375x812) and reload
            session.page.set_viewport_size({"width": 375, "height": 812})
            url_to_use = base_url + test_point.get("url_suffix", "/")
            meta = session.navigate(url_to_use, timeout_ms=20000)
            raw["url"] = meta["url"]
            raw["viewport"] = "375x812 (mobile)"
        elif action == "try_404":
            # Navigate to a deliberately-bad URL
            bad_url = base_url.rstrip("/") + "/this-page-should-not-exist-product-audit-test-1234"
            try:
                meta = session.navigate(bad_url, wait_for="domcontentloaded", timeout_ms=15000)
                raw["url"] = meta["url"]
                raw["status"] = meta.get("status")
            except Exception as e:
                raw["error_navigate"] = str(e)
                raw["url"] = bad_url
        elif action == "explore":
            # Auto-explore: navigate directly to a discovered nav URL (used in Standard/Deep)
            explore_url = test_point.get("explore_url")
            if not explore_url:
                raw["error"] = "no explore_url provided"
            else:
                try:
                    meta = session.navigate(explore_url, wait_for="domcontentloaded", timeout_ms=20000)
                    time.sleep(1.0)
                    raw["url"] = meta["url"]
                    raw["load_ms"] = meta["load_ms"]
                    raw["nav_type"] = "explore"
                except Exception as e:
                    # Fall back to load wait_until
                    try:
                        meta = session.navigate(explore_url, wait_for="load", timeout_ms=25000)
                        time.sleep(1.0)
                        raw["url"] = meta["url"]
                        raw["nav_type"] = "explore"
                    except Exception as e2:
                        raw["navigate_warning"] = f"{str(e)[:100]} | retry: {str(e2)[:100]}"
                        raw["url"] = session.page.url

        # Take screenshot unless explicitly skipped (find_link with no match)
        if not raw.get("skip_screenshot"):
            import re as _re_sanitize
            raw_slug = test_point["id"].lower() + "-" + test_point["name"].lower()
            slug = _re_sanitize.sub(r"[^a-z0-9\-_]+", "-", raw_slug)
            slug = _re_sanitize.sub(r"-+", "-", slug).strip("-")[:50]
            path = session.screenshot(slug)
            raw["screenshot"] = str(path.relative_to(session.workspace))
        raw["text"] = session.get_text()

    except Exception as e:
        raw["error"] = str(e)

    return raw


# Links we MUST NOT click during login-mode audit — clicking them logs us out
LOGOUT_LINK_REGEX = re.compile(
    r"(logout|log[-_\s]?out|signout|sign[-_\s]?out|sign[-_\s]?off|"
    r"退出登录|退出)",
    re.IGNORECASE,
)


def run_login_mode(args):
    """Logged-in audit: load saved session, traverse dashboard nav, append L* findings.

    Differs from main() in that:
      - No template — dashboards aren't covered by saas/multi-agent/ai-tool/ecommerce
      - No background dive — dashboards rarely have help portals
      - Appends to existing workspace's findings.jsonl (preserves marketing audit)
      - Logout links are filtered out so we don't kill our own session mid-audit
      - After audit, re-runs synthesis_pass on FULL findings (marketing + dashboard)
    """
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"❌ Workspace doesn't exist: {workspace}")
        print(f"   Run the regular (marketing) audit first, then append login-mode data.")
        return 1

    if not args.storage_state:
        print("❌ --login-mode requires --storage-state PATH")
        return 1
    storage_state_path = Path(args.storage_state).resolve()
    if not storage_state_path.exists():
        print(f"❌ Storage state not found: {storage_state_path}")
        print(f"   Run capture_login.py first to generate it.")
        return 1

    (workspace / "raw").mkdir(exist_ok=True)

    # Load existing findings (marketing audit) — append mode
    existing_findings = []
    findings_jsonl = workspace / "raw" / "findings.jsonl"
    if findings_jsonl.exists():
        for line in findings_jsonl.read_text().splitlines():
            if line.strip():
                try:
                    existing_findings.append(json.loads(line))
                except Exception:
                    pass
    print(f"📂 Existing workspace: {len(existing_findings)} findings loaded (will append L* test points)")

    # Compute next L* id
    next_l = 1
    existing_l_nums = []
    for f in existing_findings:
        tp_id = f.get("test_point_id", "")
        if tp_id.startswith("L") and tp_id[1:].isdigit():
            existing_l_nums.append(int(tp_id[1:]))
    if existing_l_nums:
        next_l = max(existing_l_nums) + 1
        print(f"   (existing L* findings detected — next id will be L{next_l})")

    # LLM budget reuse from depth tier
    budget = DEPTH_BUDGET.get(args.depth, DEPTH_BUDGET["standard"])
    max_llm_calls = budget["max_llm_calls"]

    # Read existing meta to track cumulative LLM usage
    existing_llm_used = 0
    meta_path = workspace / "audit-meta.json"
    if meta_path.exists():
        try:
            existing_llm_used = json.loads(meta_path.read_text()).get("llm_calls_used", 0)
        except Exception:
            pass
    llm_calls = existing_llm_used

    print(f"🔐 LOGIN MODE")
    print(f"   Dashboard URL: {args.url}")
    print(f"   Storage state: {storage_state_path}")
    print(f"   LLM budget: {llm_calls}/{max_llm_calls} already used (will keep adding)")
    print()

    if llm_available():
        print(f"✅ LLM ready (backend: {backend_name()})")
    else:
        print("⚠️  No LLM backend available — screenshots only")

    session = BrowserSession(workspace=workspace, headless=not args.debug,
                              storage_state=storage_state_path)
    new_findings: list = []

    try:
        # Phase 0: dashboard nav discovery (no cross-subdomain hubs — dashboards
        # are usually self-contained)
        print("🔍 Discovering dashboard nav + sub-pages...")
        nav_links, _cross = discover_nav_links(session, args.url)
        # Filter out logout links and pages we'd been on already during marketing audit
        marketing_urls = {f.get("url", "") for f in existing_findings if f.get("url")}
        filtered_nav = []
        for nl in nav_links:
            text = nl.get("text", "")
            path = nl.get("path", "")
            href = nl.get("href", "")
            if LOGOUT_LINK_REGEX.search(text) or LOGOUT_LINK_REGEX.search(path):
                continue
            if href in marketing_urls:
                # Already audited in marketing phase
                continue
            filtered_nav.append(nl)
        print(f"   Found {len(nav_links)} total nav links, {len(filtered_nav)} new "
              f"(excluding logout + already-audited)")
        for nl in filtered_nav[:10]:
            print(f"     • [{nl.get('source','?')}] {nl.get('text','?')[:35]:35s} → {nl.get('path','?')}")
        if len(filtered_nav) > 10:
            print(f"     ... and {len(filtered_nav) - 10} more")

        # L{next_l}: capture the entry page itself (dashboard home / /manage-ava)
        entry_id = f"L{next_l}"
        entry_name = f"Dashboard 入口: {args.url.split('/')[-1] or 'home'}"
        entry_tp = {
            "id": entry_id,
            "name": entry_name,
            "action": "navigate",
            "url_suffix": "",
        }
        print(f"\n[{entry_id}] {entry_name}")
        raw = execute_test_point(session, entry_tp, args.url, nav_links=nav_links)
        observations = []
        if llm_calls < max_llm_calls and raw.get("screenshot"):
            obs = interpret_with_llm(workspace / raw["screenshot"], raw.get("text", ""), entry_tp)
            observations = obs
            llm_calls += 1
        elif raw.get("screenshot"):
            observations = ["[Budget approaching limit]"]
        else:
            observations = ["[No screenshot captured]"]

        finding = Finding(
            test_point_id=entry_id,
            test_point_name=entry_name,
            timestamp=datetime.now().isoformat(),
            url=raw.get("url", ""),
            screenshot=raw.get("screenshot"),
            observations=observations,
            severity=None,
            raw_text_excerpt=raw.get("text", "")[:500],
        )
        new_findings.append(asdict(finding))
        with findings_jsonl.open("a") as f:
            f.write(json.dumps(asdict(finding), ensure_ascii=False) + "\n")
        next_l += 1

        # Visit each filtered nav link
        for i, nl in enumerate(filtered_nav, 1):
            if llm_calls >= max_llm_calls:
                print(f"   ⚠️  LLM budget hit ({llm_calls}/{max_llm_calls}) — stopping early")
                break
            text_label = (nl.get("text") or nl.get("path", ""))[:50]
            tp_id = f"L{next_l}"
            tp_name = f"Dashboard: {text_label}"
            explore_tp = {
                "id": tp_id,
                "name": tp_name,
                "action": "explore",
                "explore_url": nl["href"],
                "source_text": nl.get("text"),
                "source_path": nl.get("path"),
                "link_text": nl.get("text", ""),
            }
            print(f"[{tp_id}] {tp_name} → {nl['href']}")

            raw = execute_test_point(session, explore_tp, args.url, nav_links=nav_links)
            observations = []
            if llm_calls < max_llm_calls and raw.get("screenshot"):
                obs = interpret_with_llm(workspace / raw["screenshot"], raw.get("text", ""), explore_tp)
                observations = obs
                llm_calls += 1
            elif raw.get("screenshot"):
                observations = ["[Budget approaching limit]"]
            else:
                observations = ["[No screenshot captured]"]

            finding = Finding(
                test_point_id=tp_id,
                test_point_name=tp_name,
                timestamp=datetime.now().isoformat(),
                url=raw.get("url", ""),
                screenshot=raw.get("screenshot"),
                observations=observations,
                severity=None,
                raw_text_excerpt=raw.get("text", "")[:500],
            )
            new_findings.append(asdict(finding))
            with findings_jsonl.open("a") as f:
                f.write(json.dumps(asdict(finding), ensure_ascii=False) + "\n")
            next_l += 1

        # Re-run synthesis_pass on FULL findings (marketing + dashboard) so the
        # narrative / scorecard / risks / growth funnel sections incorporate
        # logged-in workspace data.
        if new_findings:
            all_findings = existing_findings + new_findings
            print(f"\n🧠 Re-running synthesis pass on {len(all_findings)} total findings "
                  f"({len(existing_findings)} marketing + {len(new_findings)} dashboard)...")
            _, llm_calls = synthesis_pass(all_findings, workspace, llm_calls, max_llm_calls)

    finally:
        session.close()

    # Update audit-meta.json with login-mode info
    meta_update = {
        "url": args.url,
        "template": "login-extend",
        "depth": args.depth,
        "language": args.language,
        "test_points_executed": len(existing_findings) + len(new_findings),
        "llm_calls_used": llm_calls,
        "llm_calls_budget": max_llm_calls,
        "completed_at": datetime.now().isoformat(),
    }
    if meta_path.exists():
        try:
            existing_meta = json.loads(meta_path.read_text())
            existing_meta.update({
                "test_points_executed": meta_update["test_points_executed"],
                "llm_calls_used": meta_update["llm_calls_used"],
                "login_mode_appended_at": meta_update["completed_at"],
                "login_mode_dashboard_url": args.url,
                "login_mode_new_test_points": len(new_findings),
                "login_mode_run": True,  # v1.10 HARD RULE: marks rule as satisfied
            })
            meta_path.write_text(json.dumps(existing_meta, ensure_ascii=False, indent=2))
        except Exception:
            meta_path.write_text(json.dumps(meta_update, ensure_ascii=False, indent=2))
    else:
        meta_path.write_text(json.dumps(meta_update, ensure_ascii=False, indent=2))

    print(f"\n✅ Login-mode audit complete. {len(new_findings)} new L* test points captured.")
    print(f"   Total workspace findings: {len(existing_findings) + len(new_findings)}")
    print(f"   Workspace: {workspace}")
    print(f"   Next: run generate_report.py to produce updated report.md + report.html")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Product audit driver")
    parser.add_argument("--url", required=True, help="Target product URL")
    parser.add_argument("--template", default="saas", help="Template name")
    parser.add_argument("--depth", default="standard", choices=["express", "standard", "deep"])
    parser.add_argument("--workspace", required=True, help="Output workspace directory")
    parser.add_argument("--language", default="zh-CN", help="Report language")
    parser.add_argument("--debug", action="store_true", help="Headed browser, verbose output")
    parser.add_argument("--storage-state", default=None,
                        help="Path to Playwright storage_state.json (produced by capture_login.py) "
                             "for logged-in audit. Use with --login-mode.")
    parser.add_argument("--login-mode", action="store_true",
                        help="Logged-in audit mode: skip template, traverse dashboard nav, "
                             "append L* test points to existing workspace findings. "
                             "Requires --storage-state.")
    parser.add_argument("--skip-login", action="store_true",
                        help="v1.10 HARD RULE escape hatch: explicitly skip login-mode "
                             "even if a login interface is detected. Sets "
                             "login_skipped_by_user=true in audit-meta.json. Use only "
                             "when the user actively opts out of login.")
    args = parser.parse_args()

    if args.login_mode:
        return run_login_mode(args)

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "raw").mkdir(exist_ok=True)

    skill_dir = SCRIPT_DIR.parent

    # Setup LLM (CLI backend via Claude Code subscription by default)
    if llm_available():
        print(f"✅ LLM ready (backend: {backend_name()})")
    else:
        print("⚠️  No LLM backend available. Will capture screenshots/text but skip interpretation.")

    # Load template + budget — template filters by depth automatically
    template = load_template(args.template, args.depth)
    budget = DEPTH_BUDGET[args.depth]
    max_points = budget["max_test_points"]
    test_points = template["test_points"][:max_points]

    print(f"🚀 Starting audit: {args.url}")
    print(f"   Template: {args.template} | Depth: {args.depth} | Points: {len(test_points)}")

    # Initialize session + findings log
    session = BrowserSession(workspace=workspace, headless=not args.debug)
    findings: list[dict] = []
    llm_calls = 0

    # Phase 0: discover homepage nav links AND cross-subdomain hub candidates
    # (both captured in the same homepage page-load to avoid double navigation cost)
    print("🔍 Discovering homepage nav links + cross-subdomain hubs...")
    nav_links, cross_subdomain_hubs = discover_nav_links(session, args.url)
    print(f"   Found {len(nav_links)} same-origin sub-pages + {len(cross_subdomain_hubs)} cross-subdomain hubs")
    if nav_links:
        for nl in nav_links[:8]:
            print(f"     • [{nl.get('source','?')}] {nl.get('text','?')[:40]:40s} → {nl.get('path','?')}")
        if len(nav_links) > 8:
            print(f"     ... and {len(nav_links) - 8} more")
    for ch in cross_subdomain_hubs[:5]:
        print(f"     • [{ch.get('source','?'):16s}] {ch.get('text','?')[:40]:40s} → {ch['href']}")

    # v1.10/v1.12 HARD RULE: detect login interface (nav + URL probing)
    login_detected, login_indicators = detect_login_interface(
        nav_links, cross_subdomain_hubs, session=session, base_url=args.url
    )
    if login_detected:
        print()
        print("=" * 72)
        print("⚠️  HARD RULE (v1.10): Login interface detected on this product")
        print("=" * 72)
        for ind in login_indicators[:5]:
            if ind["kind"] == "nav-link":
                print(f"  🔑 nav-link: '{ind['text']}' → {ind.get('href','?')}")
            elif ind["kind"] == "app-subdomain":
                print(f"  🔑 app subdomain: {ind['host']} ({ind.get('text','?')})")
        print()
        print("  After this public audit completes, you MUST capture a logged-in")
        print("  session and run --login-mode for full §3.2 Workspace Layer coverage.")
        print("  Steps: capture_login.py → audit.py --storage-state ... --login-mode")
        print("=" * 72)
        print()

    try:
        for i, tp in enumerate(test_points, 1):
            print(f"[{i}/{len(test_points)}] {tp['id']}: {tp['name']}")

            raw = execute_test_point(session, tp, args.url, nav_links=nav_links)

            observations: list[str] = []
            if raw.get("nav_type") == "not_found":
                # Link pattern didn't match — explicitly mark so reports don't mislead
                observations = [
                    f"[Link not found] 该模板期望的链接（{tp.get('link_text', tp['name'])}）"
                    f"在 {args.url} 上未找到 — 可能产品用了不同的措辞或这个功能不存在。"
                    f" 已跳过截图与 LLM 解读以避免重复首页快照。"
                ]
            elif llm_calls < budget["max_llm_calls"] and raw.get("screenshot"):
                obs = interpret_with_llm(
                    workspace / raw["screenshot"],
                    raw.get("text", ""),
                    tp,
                )
                observations = obs
                llm_calls += 1
            elif raw.get("screenshot"):
                observations = ["[Budget approaching limit — manual review needed]"]
            else:
                observations = ["[No screenshot captured]"]

            finding = Finding(
                test_point_id=tp["id"],
                test_point_name=tp["name"],
                timestamp=datetime.now().isoformat(),
                url=raw.get("url", ""),
                screenshot=raw.get("screenshot"),
                observations=observations,
                severity=None,
                raw_text_excerpt=raw.get("text", "")[:500],
            )
            findings.append(asdict(finding))

            # Append to JSONL as we go (resumable)
            with (workspace / "raw" / "findings.jsonl").open("a") as f:
                f.write(json.dumps(asdict(finding), ensure_ascii=False) + "\n")

        # ====== Phase 0+: Auto-Explore unvisited nav links (Standard/Deep) ======
        # After main test points, discover and visit any nav-discovered sub-pages
        # that weren't reached by the template. Caps based on depth.
        EXPLORE_BUDGET = {"express": 0, "standard": 8, "deep": 20}
        explore_budget = EXPLORE_BUDGET.get(args.depth, 0)
        if explore_budget > 0 and nav_links:
            # Collect paths already visited by main test points
            from urllib.parse import urlparse
            visited_paths = set()
            for f in findings:
                url = f.get("url") or ""
                if url:
                    try:
                        p = urlparse(url).path or "/"
                        visited_paths.add(p.rstrip("/") or "/")
                    except Exception:
                        pass

            # Filter to unvisited nav links (and skip Privacy/Terms style legal pages — low audit value)
            SKIP_PATHS_REGEX = _re_pat_skip = None
            import re as _re_pat_skip_init
            SKIP_PATHS_REGEX = _re_pat_skip_init.compile(
                r"/(privacy|terms|legal|cookie|gdpr|copyright|imprint|refund|sitemap)",
                _re_pat_skip_init.IGNORECASE,
            )
            unvisited = []
            for nl in nav_links:
                path = (nl.get("path") or "").rstrip("/") or "/"
                if path in visited_paths:
                    continue
                if SKIP_PATHS_REGEX.search(path):
                    continue
                unvisited.append(nl)

            to_explore = unvisited[:explore_budget]
            if to_explore:
                print(f"\n🔭 Auto-exploring {len(to_explore)} additional nav sub-pages "
                      f"({args.depth} depth allows up to {explore_budget})...")
                for j, nl in enumerate(to_explore, 1):
                    extra_id = f"E{j}"
                    extra_name = f"探索: {(nl.get('text') or nl.get('path', ''))[:40]}"
                    synthetic_tp = {
                        "id": extra_id,
                        "name": extra_name,
                        "action": "explore",
                        "explore_url": nl["href"],
                        "source_text": nl.get("text"),
                        "source_path": nl.get("path"),
                        "link_text": nl.get("text", ""),
                    }
                    print(f"[{extra_id}] {extra_name} → {nl['href']}")

                    raw = execute_test_point(session, synthetic_tp, args.url, nav_links=nav_links)

                    observations = []
                    if llm_calls < budget["max_llm_calls"] and raw.get("screenshot"):
                        obs = interpret_with_llm(
                            workspace / raw["screenshot"],
                            raw.get("text", ""),
                            synthetic_tp,
                        )
                        observations = obs
                        llm_calls += 1
                    elif raw.get("screenshot"):
                        observations = ["[Budget approaching limit — manual review needed]"]
                    else:
                        observations = ["[No screenshot captured]"]

                    finding = Finding(
                        test_point_id=extra_id,
                        test_point_name=extra_name,
                        timestamp=datetime.now().isoformat(),
                        url=raw.get("url", ""),
                        screenshot=raw.get("screenshot"),
                        observations=observations,
                        severity=None,
                        raw_text_excerpt=raw.get("text", "")[:500],
                    )
                    findings.append(asdict(finding))
                    with (workspace / "raw" / "findings.jsonl").open("a") as f:
                        f.write(json.dumps(asdict(finding), ensure_ascii=False) + "\n")

        # ====== Phase 0++: Recursive Background-Info Deep-Dive (v1.4) ======
        # Drill into help / docs / resources hubs (including cross-subdomain
        # like help.artisan.co) and recursively follow "What is X / Getting
        # Started / Overview" links up to RECURSION_DEPTH levels deep.
        #
        # Real example we need to handle:
        #   www.artisan.co/  → Resources nav → help.artisan.co  (hub, depth 0)
        #     → "Getting Started" collection                    (depth 1)
        #       → "What Is Artisan? A Quick Overview" article   (depth 2)
        #
        # BFS within each hub. Level-0 (hub itself) is the entry point and
        # NOT captured as B* (it's an index, no value-add). Captures begin
        # at depth >= 1.
        background_budget = BACKGROUND_BUDGET.get(args.depth, 0)
        hub_descent_budget = HUB_DESCENT_BUDGET.get(args.depth, 0)
        max_recursion = RECURSION_DEPTH.get(args.depth, 0)
        if background_budget > 0 and hub_descent_budget > 0 and max_recursion > 0:
            print(f"\n📚 Background deep-dive: scanning for company/product intro pages "
                  f"(max {background_budget} pages × {hub_descent_budget} hubs × depth {max_recursion})...")

            visited_urls = set()
            for f in findings:
                if f.get("url"):
                    visited_urls.add(f["url"])

            hub_candidates = discover_hub_candidates(nav_links, cross_subdomain_hubs, visited_urls)
            if not hub_candidates:
                # v1.6 A3: fallback chain when product has no help/docs/resources
                # Try /about, /features, /how-it-works, /solutions, /blog as proxy hubs
                print("   no primary hubs found — trying fallback chain "
                      "(/about → /features → /how-it-works → /solutions → /blog)")
                hub_candidates = discover_fallback_hubs(nav_links, visited_urls, max_n=3)
                if hub_candidates:
                    print(f"   fallback found {len(hub_candidates)} alternative hub(s)")
            if not hub_candidates:
                print("   no hub candidates found (primary + fallback exhausted) — "
                      "product has no obvious product-intro content section")
            else:
                print(f"   found {len(hub_candidates)} hub candidate(s):")
                for h in hub_candidates[:hub_descent_budget]:
                    print(f"     • [{h.get('source','?'):16s}] {(h.get('text') or h.get('path') or '?')[:40]:40s} → {h['href']}")

                n_dived = 0
                background_visited = set()  # everything we've crawled/captured during background phase

                for hub in hub_candidates[:hub_descent_budget]:
                    if n_dived >= background_budget:
                        break
                    hub_url = hub["href"]
                    print(f"\n   🔎 descending into hub (BFS depth ≤ {max_recursion}): {hub_url}")

                    # BFS queue: (url, depth, source_text, parent_url)
                    queue = [(hub_url, 0, hub.get("text", ""), None)]
                    while queue and n_dived < background_budget:
                        current_url, depth, src_text, parent_url = queue.pop(0)
                        if current_url in background_visited:
                            continue
                        background_visited.add(current_url)

                        # depth==0 is the hub entry, depth>=1 is real intro content
                        if depth >= 1 and current_url not in visited_urls:
                            extra_id = f"B{n_dived+1}"
                            extra_name = f"背景 D{depth}: {(src_text or current_url)[:60]}"
                            synthetic_tp = {
                                "id": extra_id,
                                "name": extra_name,
                                "action": "explore",
                                "explore_url": current_url,
                                "category": "background",
                                "source_hub": hub_url,
                                "parent_url": parent_url,
                                "depth": depth,
                                "link_text": src_text,
                            }
                            print(f"   [{extra_id}] D{depth} {(src_text or '')[:50]}")
                            print(f"        ← from: {parent_url or hub_url}")
                            print(f"        → {current_url}")

                            raw = execute_test_point(session, synthetic_tp, args.url, nav_links=nav_links)

                            observations = []
                            if llm_calls < budget["max_llm_calls"] and raw.get("screenshot"):
                                obs = interpret_background_with_llm(
                                    workspace / raw["screenshot"],
                                    raw.get("text", ""),
                                    synthetic_tp,
                                )
                                observations = obs
                                llm_calls += 1
                            elif raw.get("screenshot"):
                                observations = ["[Budget approaching limit — manual review needed]"]
                            else:
                                observations = ["[No screenshot captured]"]

                            finding = Finding(
                                test_point_id=extra_id,
                                test_point_name=extra_name,
                                timestamp=datetime.now().isoformat(),
                                url=raw.get("url", ""),
                                screenshot=raw.get("screenshot"),
                                observations=observations,
                                severity=None,
                                raw_text_excerpt=raw.get("text", "")[:500],
                            )
                            findings.append(asdict(finding))
                            with (workspace / "raw" / "findings.jsonl").open("a") as f:
                                f.write(json.dumps(asdict(finding), ensure_ascii=False) + "\n")
                            n_dived += 1

                        # Recurse one level deeper if budget allows
                        if depth < max_recursion and n_dived < background_budget:
                            sub_links = discover_background_links(
                                session, current_url,
                                background_visited | visited_urls,
                            )
                            if sub_links:
                                print(f"        ↳ {len(sub_links)} sub-link(s) queued at depth {depth+1}")
                            for sl in sub_links[:6]:  # cap fanout per node to prevent explosion
                                if sl["href"] in background_visited:
                                    continue
                                queue.append((sl["href"], depth + 1, sl.get("text", ""), current_url))

                print(f"\n   📚 background deep-dive complete — captured {n_dived} intro page(s)")

        # ====== Phase final: Synthesis pass (v1.5+v1.6+v1.8+v1.9) ======
        # 5 extra LLM calls that aggregate ALL findings into:
        #   - §1.4 战略 X 化 叙事 (strategic abstractions)
        #   - §0.5 综合评分 (5pt scorecard across 6 dimensions)
        #   - §3.1 官网 Narrative 综合 (keyword map + narrative techniques)
        #   - §5.4 官网用户增长漏斗推断 (官网作用域, excludes L* dashboard)
        #   - §1.5 公司基本信息 (WebSearch — funding / team / founding)
        # v1.9: consolidated_risks (§4.1) removed per user feedback.
        print(f"\n🧠 Synthesis pass: cross-test aggregation (6 LLM calls, v1.15)...")
        _, llm_calls = synthesis_pass(findings, workspace, llm_calls, budget["max_llm_calls"])

    finally:
        session.close()

    # Write run metadata (incl. v1.10 login-detection result)
    meta = {
        "url": args.url,
        "template": args.template,
        "depth": args.depth,
        "language": args.language,
        "test_points_executed": len(findings),
        "llm_calls_used": llm_calls,
        "llm_calls_budget": budget["max_llm_calls"],
        "completed_at": datetime.now().isoformat(),
        # v1.10 HARD RULE: login-detection result
        "login_detected": login_detected,
        "login_indicators": login_indicators,
        "login_mode_run": False,  # flipped to True by run_login_mode() when --login-mode runs
        "login_skipped_by_user": bool(args.skip_login),
    }
    (workspace / "audit-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"\n✅ Audit complete. {len(findings)} test points executed.")
    print(f"   Workspace: {workspace}")

    if login_detected:
        print()
        print("⚠️  " + "=" * 68)
        print("⚠️  HARD RULE REMINDER (v1.10): Login was detected on this product.")
        print("⚠️  You MUST now run capture_login.py + audit.py --login-mode to get")
        print("⚠️  full §3.2 Workspace Layer coverage before treating this report as complete.")
        print("⚠️  Run with --skip-login or set login_skipped_by_user=true if the user")
        print("⚠️  explicitly opts out (which should be rare).")
        print("⚠️  " + "=" * 68)
    else:
        print(f"   Next: run generate_report.py to produce report.md + report.html")


if __name__ == "__main__":
    main()
