# product-audit

> Claude Code Skill for automated, deep product **feature** audits of any SaaS / AI agent / web product.

**Version: v1.16**

Combines Playwright (deterministic browser actions + screenshots) with Claude (functional interpretation) to produce a Markdown + HTML report covering 20-40 test points across configurable depth tiers (Express / Standard / Deep).

The skill is designed to **focus on product features and capabilities, not UI aesthetics** — it explicitly avoids commenting on visual design, button styling, layout, or mobile responsiveness, and surfaces structural gaps in how the product communicates what it does.

---

## What it produces

A clean per-product workspace containing only three things:

```
NN-product/
├── figs/         (per-test-point screenshots)
├── report.md     (~700-1500 lines, 6-chapter structured analysis)
└── report.html   (single-file shareable HTML with embedded base64 screenshots)
```

Report chapters (v1.15):

```
§1 Executive Summary       (verdict / scorecard / risks-opportunities / quick wins)
§2 产品概览                (基础信息 / 测点速览 / recursive background / X 化叙事 / 公司基本信息 ⭐ WebSearch)
§3 体验方法论              (methodology + severity rubric + boundaries)
§4 体验流程记录            (Narrative 综合 ⭐ + 17-module-clustered findings)
§5 第三方社区反馈 ⭐ (NEW) (Reddit / Product Hunt / Hacker News / G2 — non-official discussion)
§6 总结                    (verdict / top opportunities / top risks / growth funnel inference)
```

⭐ marks LLM-synthesized chapters (6 cross-test synthesis calls aggregate findings into structured insight, including 2 WebSearch-augmented sections).

---

## Key capabilities

| Version | Capability |
|---|---|
| **v1.4** | Recursive background discovery — drills 2-3 levels deep into help/docs/resources including cross-subdomain `help.X.com` to extract the product team's own "What is X / Getting Started / Overview" introduction pages |
| **v1.5-1.6** | 5-call synthesis pass — 6-dim scorecard, strategic X-化 abstractions, narrative analysis with keyword map, 官网-scoped growth funnel, 17-module test-point clustering |
| **v1.7** | Login-mode — `capture_login.py` headed-browser session capture + `audit.py --login-mode` for §4.2 🔐 Workspace Layer coverage |
| **v1.8** | WebSearch synthesis — pulls funding / team / founding date from Crunchbase / TechCrunch / LinkedIn with sourced citations |
| **v1.9** | Simplified summaries — removed prescriptive sections |
| **v1.10** | **HARD RULE**: if login interface detected, Claude MUST prompt the user to capture session and run --login-mode (or explicit `--skip-login`) before treating the report as complete |
| **v1.11** | §2.5 entity-identity verification — domain-anchored web search + 4-step cross-verification to prevent same-name company mix-ups (e.g., `pika.me` vs `pika.art`) |
| **v1.12** | HARD RULE detection layer 3 — URL probing for JS-only login CTAs and unlinked `/login` paths |
| **v1.13** | Trimmed structure (removed §4 problem list + 附录) + default workspace cleanup keeping only `figs/ + report.md + report.html` |
| **v1.14** | TOC complete + chapters renumbered from §1 |
| **v1.15** | §5 community feedback — synthesis #7 pulls non-official Reddit/PH/HN/G2 user discussion, domain-anchored, with URL + blockquote citations, refuses to fabricate when no discussion found |
| **v1.16** | §5 Format B minimization — when no community discussion found, output only a 1-sentence null-finding statement (no name-collision lists, no search-query tables, no manual-search links) |

---

## Install / use as a Claude Code Skill

Drop into your Claude Code skills directory:

```bash
git clone git@github.com:JavaLyHn/product-audit.git ~/.claude/skills/product-audit
# or per-project:
git clone git@github.com:JavaLyHn/product-audit.git <your-project>/.claude/skills/product-audit
```

Then invoke through Claude Code: just say "测评 https://example.com" / "audit this platform" / "深度调研 https://..." and the skill activates.

### Manual invocation

```bash
cd .claude/skills/product-audit/scripts

unset ANTHROPIC_API_KEY    # use Claude Code subscription, not API billing

# 1. Public audit
python3 -u audit.py \
  --url "https://example.com" \
  --template <saas|multi-agent|ai-tool|ecommerce> \
  --depth <express|standard|deep> \
  --workspace /path/to/audits/NN-product \
  --language zh-CN

# 2. (Optional, if HARD RULE triggers) capture login session
python3 capture_login.py \
  --url https://dashboard.example.com \
  --output /path/to/audits/NN-product/.auth/storage_state.json \
  --success-url-contains dashboard

# 3. (Optional) login-mode audit — appends L* findings + re-runs synthesis
python3 -u audit.py \
  --url https://dashboard.example.com \
  --template <same as step 1> \
  --depth <same as step 1> \
  --workspace /path/to/audits/NN-product \
  --storage-state /path/to/audits/NN-product/.auth/storage_state.json \
  --login-mode

# 4. Generate report (default: cleanup keeps only figs/+md+html)
python3 generate_report.py \
  --workspace /path/to/audits/NN-product \
  --formats md,html
# Add --keep-raw if you want to re-generate from raw findings later
```

---

## Dependencies

- **Python 3.9+**
- **Playwright** (`pip install playwright && playwright install chromium`)
- **Claude Code CLI** (`claude` available in `$PATH`) — uses subscription auth, no API billing
- **python-markdown** (for HTML rendering: `pip install markdown`)
- **json-repair** (optional, for lenient JSON parsing: `pip install json-repair`)

---

## File map

```
product-audit/
├── SKILL.md                   ← Claude Code skill manifest (read first)
├── README.md                  ← this file (GitHub-facing)
├── scripts/
│   ├── audit.py               ← main audit driver (Playwright + Claude + synthesis pass)
│   ├── browser.py             ← Playwright wrapper (storage_state-aware)
│   ├── llm.py                 ← LLM abstraction (CLI subprocess + SDK backends; WebSearch tool support)
│   ├── capture_login.py       ← v1.7 session capture (headed browser, auto-detect login)
│   ├── generate_report.py     ← MD + HTML rendering, cleanup, helpers
│   └── research_competitors.py← DEPRECATED v1.4 (kept for archaeology)
├── templates/
│   ├── _common.md             ← test points shared across all templates
│   ├── saas.md
│   ├── multi-agent.md
│   ├── ai-tool.md
│   └── ecommerce.md
├── references/
│   ├── architecture.md        ← system architecture deep-dive
│   ├── depth-tiers.md         ← Express/Standard/Deep budget detail
│   └── credential-handling.md ← security rules for login-mode
├── assets/
│   └── report-template.md     ← legacy v1.0 template (kept for reference; live template is inline in generate_report.py)
└── evals/
    └── evals.json             ← test cases for skill quality verification
```

---

## ⚠️ Note: hardcoded absolute paths

Some files (`SKILL.md`, `scripts/llm.py`, `evals/evals.json`, `assets/report-template.md`) still contain `/Users/aa00945/Desktop/octok/...` paths from the development environment. They are illustrative — substitute your own absolute paths when adapting.

The `scripts/audit.py` and `scripts/generate_report.py` themselves are path-agnostic (driven by `--workspace` argument).

---

## License

MIT (or as configured on the GitHub repository).

---

## Acknowledgements

Designed iteratively against 5 hand-written product analysis reports (Artisan / Kuse / monday / Moxt / Okara) as quality baselines. The 6-chapter structure and synthesis-pass outputs are calibrated to match the rigor of human product analysts at consultancies, while delivering at ~10% of the time cost.
