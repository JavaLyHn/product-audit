"""Competitor research script — produces §6 横向对标 input data.

Approach:
1. If competitors not provided, ask Claude (with web search) to suggest 2-4 likely competitors
2. For each competitor:
   - Web search to gather positioning, features, pricing, target customer
   - For Standard+: take 1 screenshot of homepage via Playwright
3. Synthesize structured comparison data → raw/competitors.json

The comparison is text-only at MVP (no real audit of each competitor — that'd take
N× the time). For real audit-quality comparison, user should run audit.py separately
against each competitor and synthesize manually.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from browser import BrowserSession  # noqa: E402
from llm import call as llm_call, is_available as llm_available  # noqa: E402

try:
    from json_repair import repair_json
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False


def _parse_json_lenient(text: str):  # returns dict | list | None — typing union dropped for 3.9 compat
    """Parse JSON with multiple fallback strategies.

    LLMs sometimes output JSON with unescaped quotes (especially in CJK text).
    Use json-repair if available, else basic strict parse.
    """
    if not text:
        return None
    # Extract the JSON portion (between first { or [ and last } or ])
    start_obj = text.find("{")
    start_arr = text.find("[")
    if start_obj == -1 and start_arr == -1:
        return None
    if start_obj == -1:
        start = start_arr
    elif start_arr == -1:
        start = start_obj
    else:
        start = min(start_obj, start_arr)
    # Find matching end
    end_obj = text.rfind("}")
    end_arr = text.rfind("]")
    end = max(end_obj, end_arr) + 1
    if end <= start:
        return None
    candidate = text[start:end]
    # Try strict first
    try:
        return json.loads(candidate)
    except Exception:
        pass
    # Fallback: json-repair
    if HAS_JSON_REPAIR:
        try:
            repaired = repair_json(candidate)
            return json.loads(repaired) if isinstance(repaired, str) else repaired
        except Exception:
            pass
    return None


# How many competitors to research per depth tier
# `browse_each` controls homepage screenshot capture for each competitor.
# `extra_pages` lists additional pages to capture (Standard+ tiers).
COMPETITOR_BUDGET = {
    "express":  {"max_competitors": 2, "browse_each": True,  "extra_pages": [],
                 "max_llm_calls": 5},
    "standard": {"max_competitors": 4, "browse_each": True,  "extra_pages": ["pricing"],
                 "max_llm_calls": 15},
    "deep":     {"max_competitors": 4, "browse_each": True,  "extra_pages": ["pricing", "product"],
                 "max_llm_calls": 25},
}


# Map "extra page" keywords to link-text patterns (similar to ALL_TEST_POINTS)
EXTRA_PAGE_PATTERNS = {
    "pricing":  "pricing|定价|plans",
    "product":  "product|features|use case|how it works",
    "customers": "customers|case stud|stories",
    "about":    "about|company",
}


def load_main_audit_meta(workspace: Path) -> dict:
    """Load the main audit's metadata to inform competitor selection."""
    meta_file = workspace / "audit-meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text())
    return {}


def load_main_findings_excerpt(workspace: Path, max_chars: int = 3000) -> str:
    """Load a digest of main audit findings to inform competitor selection."""
    findings_file = workspace / "raw" / "findings.jsonl"
    if not findings_file.exists():
        return ""
    findings = []
    for line in findings_file.read_text().splitlines():
        if line.strip():
            try:
                f = json.loads(line)
                findings.append(f"[{f['test_point_id']}] {f['test_point_name']}: {' | '.join(f.get('observations', [])[:2])}")
            except Exception:
                continue
    excerpt = "\n".join(findings)[:max_chars]
    return excerpt


def suggest_competitors(target_url: str, template: str, main_findings: str) -> list[str]:
    """Ask Claude to suggest 2-4 competitors based on target product."""
    if not llm_available():
        return []
    prompt = f"""You are helping evaluate the web product at {target_url}.
Template: {template}
Main audit findings excerpt:
{main_findings[:2000]}

Suggest 2-4 most-relevant competitor products that users would realistically compare this against. Output ONLY a JSON array of strings, each being either a URL or a product name (e.g. ["manus.im", "genspark.ai", "coze.cn"]). No explanation, just the array."""
    text = llm_call(prompt, max_tokens=512)
    parsed = _parse_json_lenient(text)
    if isinstance(parsed, list):
        return parsed
    print(f"⚠️  Competitor suggestion JSON parse failed; got: {text[:200]}")
    return []


def research_one_competitor(name: str, target_url: str, template: str,
                             session=None, extra_pages: list = None) -> dict:
    """Research one competitor: positioning, features, pricing, target customer.

    Optionally takes screenshots of homepage + additional pages (pricing/product).
    """
    extra_pages = extra_pages or []
    if not llm_available():
        return {"name": name, "error": "No LLM backend available"}

    prompt = f"""Research the product/company "{name}" (it may be a URL like "manus.im" or a name).
This is for a competitor comparison against {target_url} (template: {template}).

Provide a concise structured analysis. Output STRICT JSON with these keys:
- "name": product display name
- "url": likely main URL (best guess)
- "positioning": one-sentence definition (1 sentence)
- "target_user": who uses it (1 phrase)
- "key_features": 3-5 bullets, very short
- "pricing_model": brief description (free/freemium/subscription/etc)
- "unique_strength": one sentence — what they do BETTER than alternatives
- "weakness_vs_target": one sentence — where the target ({target_url}) might beat them
- "category": one phrase (e.g., "general autonomous agent", "multi-agent platform")

Be honest and concrete. If you're unsure about a field, say "uncertain". Output ONLY JSON."""

    text = llm_call(prompt, max_tokens=1024)
    parsed = _parse_json_lenient(text)
    if isinstance(parsed, dict):
        data = parsed
        # Ensure 'name' is set
        if "name" not in data:
            data["name"] = name
    else:
        return {"name": name, "error": "JSON parse failed", "raw": text[:300]}

    # Take homepage screenshot + optional extra pages
    if session is not None and not data.get("error"):
        url = data.get("url") or (f"https://{name}" if "." in name else None)
        if url and not url.startswith("http"):
            url = "https://" + url.lstrip("/")
        if url:
            safe_name = name.replace(".", "-").replace("/", "-").replace(":", "")[:30]
            data["screenshots"] = []  # list of {page: str, file: str}

            # Homepage — use domcontentloaded (faster, more tolerant of marketing widgets)
            try:
                meta = session.navigate(url, wait_for="domcontentloaded", timeout_ms=20000)
                # Brief settle time for layout/css to apply
                import time as _t
                _t.sleep(2.0)
                slug = f"competitor-{safe_name}-homepage"
                path = session.screenshot(slug)
                data["screenshots"].append({"page": "homepage", "file": path.name})
                data["screenshot"] = path.name  # backward-compat alias
                data["actual_url"] = meta["url"]
            except Exception as e:
                # Fallback: try with longer timeout and load (not networkidle)
                try:
                    meta = session.navigate(url, wait_for="load", timeout_ms=30000)
                    import time as _t
                    _t.sleep(2.0)
                    slug = f"competitor-{safe_name}-homepage"
                    path = session.screenshot(slug)
                    data["screenshots"].append({"page": "homepage", "file": path.name})
                    data["screenshot"] = path.name
                    data["actual_url"] = meta["url"]
                except Exception as e2:
                    data["screenshot_error"] = f"{type(e).__name__}: {str(e)[:120]} | retry: {str(e2)[:120]}"

            # Extra pages (Standard+ tiers)
            for page_kind in extra_pages or []:
                pattern = EXTRA_PAGE_PATTERNS.get(page_kind, page_kind)
                try:
                    # Re-navigate to homepage first to ensure consistent starting state
                    session.navigate(url, timeout_ms=15000)
                    for p in pattern.split("|"):
                        try:
                            session.page.locator(
                                f"a:text-matches('(?i){p.strip()}', 'i')"
                            ).first.click(timeout=2500)
                            session.page.wait_for_load_state("networkidle", timeout=8000)
                            slug = f"competitor-{safe_name}-{page_kind}"
                            shot_path = session.screenshot(slug)
                            data["screenshots"].append({"page": page_kind, "file": shot_path.name})
                            break
                        except Exception:
                            continue
                except Exception:
                    pass

    return data


def build_comparison_synthesis(target_url: str, target_findings: str,
                                competitors: list[dict], template: str) -> dict:
    """Ask Claude to synthesize the comparison into structured tables.

    Returns dict with: form_table, capability_table, score_table, insights.
    """
    if not llm_available():
        return {"error": "No LLM backend available", "competitors": competitors}

    competitors_summary = "\n\n".join(
        f"**{c.get('name', 'Unknown')}**: {c.get('positioning', 'n/a')} | "
        f"Target user: {c.get('target_user', 'n/a')} | "
        f"Unique strength: {c.get('unique_strength', 'n/a')}"
        for c in competitors if not c.get("error")
    )

    prompt = f"""You are writing the "§6 横向对标" section of a product evaluation report.
Target product: {target_url}
Template: {template}

Target product key findings (from audit):
{target_findings[:2000]}

Competitors researched:
{competitors_summary}

Synthesize a comparison. Output STRICT JSON with these top-level keys:

1. "form_comparison_table" — array of rows. Each row: {{"维度": str, "{target_url}": str, [for each competitor by name]: str}}
   Rows should include: "定位", "目标用户", "形态隐喻", "核心壁垒"

2. "capability_comparison_table" — array of rows for template-relevant dimensions.
   For multi-agent template: rows like "多 Agent 编排", "OKR 派发", "角色边界 + Escalate", "渠道部署", "持久企业上下文"
   For saas template: rows like "集成生态", "定价透明度", "客户案例丰富度", "文档完整度", "API 开放度"
   For ai-tool template: rows like "工具调用透明度", "产物形态", "引用严谨度", "并行能力", "可分享性"
   For ecommerce: rows like "支付方式覆盖", "国际配送", "退换货政策", "信任信号"
   Each row uses ✅ / ⚠️ / ❌ + short note, e.g. "✅ 真功能" or "❌ 全 placeholder"

3. "score_table" — 5 分制综合评分 per product per dimension. Same dimensions as #2.
   Each row: {{"维度": str, "{target_url}": float, [for each competitor]: float}}
   Final row should be "**综合（产品全貌）**" with weighted avg.

4. "insights" — object with:
   - "target_should_learn": array of 3-5 strings — what target should learn from competitors
   - "target_moat": array of 3-5 strings — capabilities target has that competitors don't
   - "user_scenario_split": one paragraph — which user should pick which product

Output ONLY JSON. Be specific and honest. Use ⭐ to mark winners per row in score_table."""

    text = llm_call(prompt, max_tokens=4096)
    parsed = _parse_json_lenient(text)
    if isinstance(parsed, dict) and not parsed.get("error"):
        return parsed
    return {"error": "Failed to synthesize", "raw": text[:500], "competitors": competitors}


def main():
    parser = argparse.ArgumentParser(description="Competitor research driver")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--competitors", default="", help="Comma-separated. If empty, auto-suggest.")
    parser.add_argument("--template", default="saas")
    parser.add_argument("--depth", default="standard", choices=["express", "standard", "deep"])
    parser.add_argument("--auto-confirm", action="store_true",
                        help="Skip interactive confirmation when auto-suggesting competitors")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    main_meta = load_main_audit_meta(workspace)
    target_url = main_meta.get("url", "(unknown)")
    main_findings = load_main_findings_excerpt(workspace)

    if not llm_available():
        print("⚠️  No LLM backend available. Competitor research skipped — §6 will be empty.")
        (workspace / "raw" / "competitors.json").write_text(json.dumps({
            "skipped": True,
            "reason": "No LLM backend (claude CLI or ANTHROPIC_API_KEY)",
            "competitors": [],
            "comparison": {},
        }, ensure_ascii=False, indent=2))
        return 0

    # Determine competitor list
    if args.competitors.strip():
        competitor_names = [c.strip() for c in args.competitors.split(",") if c.strip()]
    else:
        print("🔍 No competitors provided. Asking Claude to suggest based on main audit findings…")
        competitor_names = suggest_competitors(target_url, args.template, main_findings)
        if not competitor_names:
            print("⚠️  Could not auto-suggest competitors. §6 will be empty.")
            (workspace / "raw" / "competitors.json").write_text(json.dumps({
                "skipped": True,
                "reason": "Auto-suggestion failed and no manual list provided",
                "competitors": [],
                "comparison": {},
            }, ensure_ascii=False, indent=2))
            return 0
        print(f"   Suggested: {competitor_names}")
        if not args.auto_confirm:
            print("   (use --auto-confirm to skip this confirmation in scripted runs)")

    # Trim to budget
    budget = COMPETITOR_BUDGET[args.depth]
    competitor_names = competitor_names[:budget["max_competitors"]]
    print(f"📊 Researching {len(competitor_names)} competitors: {competitor_names}")

    # Browser session (only if depth requires browsing)
    session = None
    if budget["browse_each"]:
        try:
            session = BrowserSession(workspace=workspace, headless=True)
        except Exception as e:
            print(f"⚠️  Could not start browser for competitor screenshots: {e}")

    # Research each
    competitor_data = []
    extra_pages = budget.get("extra_pages", [])
    for name in competitor_names:
        n_shots = (1 if session else 0) + len(extra_pages if session else [])
        print(f"  • Researching {name}… (planned screenshots: {n_shots})")
        data = research_one_competitor(name, target_url, args.template, session, extra_pages)
        competitor_data.append(data)

    if session:
        session.close()

    # Synthesize comparison
    print("🧩 Synthesizing comparison tables…")
    comparison = build_comparison_synthesis(
        target_url, main_findings, competitor_data, args.template
    )

    # Persist
    output = {
        "target_url": target_url,
        "template": args.template,
        "depth": args.depth,
        "researched_at": datetime.now().isoformat(),
        "competitors": competitor_data,
        "comparison": comparison,
    }
    out_path = workspace / "raw" / "competitors.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"✅ Wrote {out_path}")
    print(f"   Next: generate_report.py will render §6 from this data")
    return 0


if __name__ == "__main__":
    exit(main())
