---
name: product-audit
description: Automated deep product **feature** audit report generator (v1.15). Use this skill whenever the user wants to evaluate, audit, review, benchmark, or do "调研/体验/测评/评估" on a SaaS / AI agent / web product / 平台 — focusing on **product features and capabilities**, not UI aesthetics. Triggers on phrases like "帮我测评 X", "深度调研这个产品", "audit this platform", "评测 https://...". Combines Playwright (deterministic browser actions + screenshots) with Claude (functional interpretation) to produce a Markdown + HTML report covering 20-40 test points across configurable depth tiers (Express / Standard / Deep). **⚠️ v1.10 HARD RULE: if login interface is detected (login_detected=true in audit-meta.json), Claude MUST prompt the user to log in via capture_login.py and then run --login-mode.** **⚠️ v1.11 §2.5 entity-identity verification: web search MUST use domain-anchored queries (site:/exact-match) and cross-verify the searched company's LinkedIn/Crunchbase/news links back to the audited domain — if uncertain, output a "需要用户确认" template instead of fabricating facts.** **v1.13 report structure: §4 问题清单 and 附录 chapters REMOVED. v1.14 chapters renumbered from 1 (1-5).** **v1.13 cleanup: by default, after `generate_report.py` produces report.md + report.html, the workspace is cleaned to retain ONLY figs/ + report.md + report.html.** **v1.15 §5 community feedback (NEW): synthesis #7 uses WebSearch to pull NON-OFFICIAL third-party user discussion from Reddit / Product Hunt / Hacker News / G2 / Trustpilot — domain-anchored search to avoid name collisions, real URL citations required, "未找到讨论" template when none found. Marks output as 非官方 to contrast with §2.5 official company info and §4.1 official Narrative.** Other key capabilities: (v1.4) recursive background discovery; (v1.5-v1.6) synthesis pass; (v1.7) login-mode; (v1.9) simplified summaries.
---

# Product Audit Skill

A Claude Code skill that drives a Browser Agent to deeply explore a web product, take screenshots, capture findings, and generate a polished research report (Markdown + HTML).

This skill exists because manually evaluating a product to professional consultancy quality takes 2+ hours of expert time per product. The skill compresses that to 5-60 minutes depending on depth, while preserving the structured rigor of a human-authored report.

## When to use this skill

Use this skill when the user asks to:

- Evaluate / audit / review / benchmark a web product, SaaS, AI agent, or platform
- Produce a "调研报告 / 体验报告 / 测评报告 / 评估报告" for a specific URL
- Do competitive intelligence on a product
- Compare a product to a baseline (this skill does single-product depth; for multi-product compare, run it N times and synthesize)

Phrases that should trigger this skill (in any language):
- "帮我测评 / 深度调研 / 体验一下 / 评估一下" + product/URL
- "audit / review / benchmark / evaluate" + product/URL
- "做一份 X 产品的体验报告"
- "我想知道 X 这个产品怎么样"
- Even just a URL with a casual ask like "看看这个值不值得用"

## What the user will get

Two deliverables saved to a workspace directory:

1. **`<workspace>/report.md`** — A 1500-15000 word structured Markdown report (length depends on depth tier)
2. **`<workspace>/report.html`** — Self-contained HTML with embedded screenshots, ready to share

Workspace layout:
```
<workspace>/
├── report.md                       # Main deliverable
├── report.html                     # Shareable HTML
├── figs/                           # Numbered screenshots (01-..., 02-...)
├── raw/                            # Raw page snapshots, observations, transcripts
└── audit-meta.json                 # Run metadata (template, depth, duration, etc.)
```

## High-level workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. Parse user intent (URL, template, depth, credentials/storage?)   │
│                                ↓                                      │
│  2. Initialize workspace + start Playwright session                  │
│                                ↓                                      │
│  3. Phase 0: discover homepage nav/footer + cross-subdomain hubs     │
│     (returns both same-origin nav links AND help.X.com style hubs)   │
│     v1.10: ALSO detect login interface → audit-meta.json              │
│           If login found → Claude MUST prompt user later (HARD RULE) │
│                                ↓                                      │
│  4. Run main test points (per template, focused on FUNCTIONALITY):   │
│     for each test point:                                             │
│       Playwright: navigate / interact / screenshot                   │
│       Claude:     interpret feature/capability (NOT UI aesthetics)   │
│       Persist:    save figs/, raw/, append to findings log          │
│                                ↓                                      │
│  5. Auto-explore: visit any unvisited nav sub-pages                  │
│                                ↓                                      │
│  6. Phase 0++: recursive BACKGROUND discovery (v1.4)                 │
│     Drill into help/docs/resources hubs (incl. help.X.com cross-     │
│     subdomain). BFS depth 2-3. Match "What is X / Getting Started   │
│     / Overview" patterns. v1.6: fallback to /about, /features        │
│     when no help portal exists.                                      │
│                                ↓                                      │
│  6b. (OPTIONAL) login-mode (v1.7) — if --storage-state provided      │
│     Skip template loop; instead traverse dashboard nav. Use L*       │
│     test IDs. Append to existing workspace's findings.               │
│                                ↓                                      │
│  7. Synthesis pass (v1.5-v1.9) — 5 cross-test LLM calls:             │
│     - Strategic abstractions (X 化叙事, §1.4)                        │
│     - 6-dim scorecard 5pt scale (§0.5)                               │
│     - Narrative summary + keyword map (§3.1)                         │
│     - Growth funnel inference (§5.4, 官网-only since v1.9)           │
│     - Company info via WebSearch (§1.5, v1.8) — funding/team/news    │
│     [REMOVED v1.9: consolidated risks §4.1 — too prescriptive]       │
│                                ↓                                      │
│  8. Report generation (v1.6 module clustering) → report.md + html    │
│                                ↓                                      │
│  9. Return workspace path + summary to user                          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ HARD RULE: Login-mode is MANDATORY when login exists (v1.10)

> **This is a binding rule for Claude when invoking this skill. Don't ship a
> "complete" report without satisfying it.**

If the audited product has a login interface (which ~95% of SaaS / AI agent /
dashboard products do), the skill **MUST** capture a logged-in session and run
`--login-mode` AFTER the public audit. A report without the §3.2 🔐 登录后
Workspace section is **incomplete** for any product that has a dashboard.

### Why this rule exists

- Marketing pages tell you **what the product claims to do**
- Login-only pages tell you **what the product actually is**
- The §3.2 Workspace Layer is the highest-value section of human-written product
  analyses (see the Artisan reference: 11 onboarding quests, Guardrails module,
  mailbox matrix, Direct Message-Only Campaign — none of which appear on
  marketing pages)
- Skipping login = shipping a report that's 50% blind

### Decision tree Claude must follow

```
1. Run audit.py (public audit) — script auto-detects login interface
   ↓
2. Read audit-meta.json after the run
   ↓
3. Is login_detected == true?
   ├─ NO → proceed to generate_report.py (rule N/A)
   └─ YES → CONTINUE to step 4
   ↓
4. Has login_mode_run already happened? (incremental rerun case)
   ├─ YES → proceed to generate_report.py (rule satisfied)
   └─ NO  → CONTINUE to step 5
   ↓
5. Has login_skipped_by_user been set? (explicit user opt-out)
   ├─ YES → proceed to generate_report.py (rule explicitly waived)
   └─ NO  → MUST prompt user (see template below) before proceeding
```

### Prompt template (use verbatim or adapt minimally)

After the public audit completes, when `login_detected == true` and login-mode
hasn't run, Claude must say something like:

> **检测到登录入口**（`<indicator from audit-meta.json>`）。
> Skill v1.10 强规则：必须捕获登录态才算完整覆盖产品功能层。
>
> 我现在会打开 `capture_login.py` 让你登录一次（headed 浏览器），
> 登完它会自动保存 session，我再跑 `--login-mode` audit 补足 §3.2
> 登录后 Workspace 章节。
>
> 如果你确实不想登录（极少数情况），请明确回复 "**跳过登录**" — 我会
> 写 `login_skipped_by_user=true` 到 audit-meta.json 并在 §1.2 标注此报告
> 是公开页 only 的 partial coverage。

Don't ask "你想登录吗？" — the default IS to log in. Only the explicit user opt-out
should skip this step.

### What counts as a login interface (detection signals)

The `detect_login_interface()` function in `audit.py` flags any of:

- **nav-link signals**: text/path matches `log in / sign in / login / signin / 登录 / 登陆 / /auth / /oauth`
- **app-subdomain signals**: cross-subdomain hub matches `app.X / dashboard.X / admin.X / portal.X / account.X / my.X / workspace.X / console.X / hub.X`

Both layers are checked. If either fires, `login_detected = true`.

### Exceptions (when rule may be waived)

Only these scenarios allow skipping login-mode:

1. **User explicitly opts out** — they reply "跳过登录" / "no login" / "skip auth"
   → Add `--skip-login` flag. Report §1.2 will surface the partial-coverage warning.
2. **Product genuinely has no login** — `login_detected == false`. Detection is
   accurate for ~95% of products; if you're sure detection missed it, manually
   inspect Phase 0 output before assuming login doesn't exist.
3. **Login is technically blocked** — CAPTCHA / phone OTP / KYC stack that
   `capture_login.py` can't navigate in <10 min. Document in report §1.2.

In all 3 cases, `login_skipped_by_user` (or `login_capture_failed`) must be set in
audit-meta.json so the report transparently surfaces incomplete coverage.

### Workflow steps after login is captured

```bash
# Step A: capture session (headed browser, user logs in once, auto-detect saves)
python3 capture_login.py \
  --url https://dashboard.<PRODUCT>.com/<entry-page> \
  --output <WORKSPACE>/.auth/storage_state.json \
  --success-url-contains <dashboard-substring>

# Step B: run login-mode audit (appends L* findings to existing workspace)
unset ANTHROPIC_API_KEY
python3 -u audit.py \
  --url https://dashboard.<PRODUCT>.com/<entry-page> \
  --template <same as public audit> \
  --depth <same as public audit> \
  --workspace <WORKSPACE> \
  --storage-state <WORKSPACE>/.auth/storage_state.json \
  --login-mode

# Step C: regenerate report (synthesis pass re-runs on full findings)
python3 generate_report.py --workspace <WORKSPACE> --formats md,html
```

---

## Quick start (what Claude should do when invoked)

### Step 1: Gather parameters

When invoked, parse the user's request and confirm these parameters (ask only what's missing):

| Param | Required | Default | Example |
|---|---|---|---|
| `url` | yes | — | `https://example.com` |
| `template` | yes | `saas` | `saas` / `multi-agent` / `ai-tool` / `ecommerce` |
| `depth` | yes | `standard` | `express` / `standard` / `deep` |
| `credentials` | no | — | Login email + password (optional, only for tests behind login) |
| `workspace` | no | `/Users/aa00945/Desktop/octok/audits/<domain>-<timestamp>/` | Output dir. **Default is always under the octok project folder** — never `/tmp/` or scattered locations. |
| `language` | no | `zh-CN` | Report language: `zh-CN` / `en` |

**Smart defaults:** If the user just says "测评 https://example.com", default to `template=saas`, `depth=standard`, `language=zh-CN`. Confirm before starting.

**Credentials handling (critical):**
- Credentials are **never** written to disk
- Credentials are **never** sent to Claude API in prompts
- Playwright uses them in-memory only, then they're discarded
- If user provides credentials, prompt: "Credentials will be kept in memory only and discarded after the session. Confirm to proceed."

### Step 2: Load the template

Read `templates/<template>.md`. Each template defines:
- Test point list (30+ items, each is a navigation + observation task)
- Required vs optional per depth tier
- Expected output schema for the report

Templates live in `templates/`:
- `saas.md` — Generic SaaS evaluation (default)
- `multi-agent.md` — Multi-Agent AI products (multiple named agents collaborating)
- `ai-tool.md` — Single-Agent AI tools (single autonomous agent / chat assistant)
- `ecommerce.md` — E-commerce / marketplace
- `_common.md` — Common test points all templates include

If the user requests a template that doesn't exist, fall back to `saas.md` and note this in the report.

### Step 3: Run the audit

Invoke `scripts/audit.py` with the parameters. Strip `ANTHROPIC_API_KEY` so the
CLI backend uses subscription auth:

```bash
unset ANTHROPIC_API_KEY  # use Claude Code subscription, not API billing
python3 -u /Users/aa00945/Desktop/octok/.claude/skills/product-audit/scripts/audit.py \
  --url "$URL" \
  --template "$TEMPLATE" \
  --depth "$DEPTH" \
  --workspace "$WORKSPACE" \
  --language "$LANGUAGE"
```

The audit script:
1. Launches Playwright in headless mode (or headed if `--debug` set)
2. Phase 0: nav discovery + cross-subdomain hub discovery (single page-load)
3. Iterates main template test points; for each:
   - Performs the page action (navigate / click / scroll / 404 / etc.)
   - Takes screenshot with numbered semantic filename
   - Asks Claude (via CLI subprocess) to interpret with FUNCTIONAL focus
   - Appends findings to `raw/findings.jsonl`
4. Phase 0+: auto-explore unvisited nav sub-pages (Standard 8 / Deep 20)
5. Phase 0++: recursive background dive (BFS depth 2-3 into help/docs/resources)
6. Phase final: 6-call synthesis pass → `raw/synthesis.json`

Logging is `N/M` per test point for live progress.

**Note (v1.4):** competitor research (`research_competitors.py`) is **deprecated**.
Don't call it — §6 横向对标 was removed from the report.

### Step 3b (OPTIONAL): Login-mode for logged-in pages (v1.7)

If the product has a dashboard / workspace behind login (which holds the highest-
value §3.2 Workspace Layer content), capture a session and run login-mode:

```bash
# 1. Capture session (headed browser, user logs in, auto-detect saves storage_state)
python3 /Users/aa00945/Desktop/octok/.claude/skills/product-audit/scripts/capture_login.py \
  --url "https://dashboard.PRODUCT.com" \
  --output "$WORKSPACE/.auth/storage_state.json" \
  --success-url-contains "dashboard"

# 2. Run login-mode audit (appends L* findings to existing workspace)
unset ANTHROPIC_API_KEY
python3 -u /Users/aa00945/Desktop/octok/.claude/skills/product-audit/scripts/audit.py \
  --url "https://dashboard.PRODUCT.com/HOME_PAGE" \
  --template "$TEMPLATE" \
  --depth "$DEPTH" \
  --workspace "$WORKSPACE" \
  --storage-state "$WORKSPACE/.auth/storage_state.json" \
  --login-mode
```

Login-mode skips the template loop, traverses dashboard nav with auto-explore-style
logic, uses L1, L2, L3... test point IDs, and **filters out logout links** to avoid
killing its own session. After capturing, synthesis re-runs on full findings to
incorporate dashboard data into §3.2 modules + §5.4 growth funnel.

**Security:** `storage_state.json` contains session tokens — workspace `.auth/`
directory should be git-ignored. Tokens expire (typically 1-30 days).

### Step 4: Generate the report

After all test points complete, invoke the report generator:

```bash
python /Users/aa00945/Desktop/octok/.claude/skills/product-audit/scripts/generate_report.py \
  --workspace "$WORKSPACE" \
  --formats md,html
```

This reads `raw/findings.jsonl` + screenshots and produces:
- `report.md` — Engineer-style Markdown with TOC, tables, severity-graded issues
- `report.html` — Self-contained HTML with embedded base64 screenshots

### Step 5: Summarize to user

After generation, print to the user:
- Workspace path
- Report file paths (both md and html)
- 3-5 headline findings (high-severity issues + key strengths)
- Time + token usage

Then return control. Don't reproduce the full report in chat — it's already a file.

## Depth tiers (key sizing decision)

| Tier | Time | Test points | Tool calls | Report length | Use case |
|---|---|---|---|---|---|
| **Express** | 5-15 min | 10-15 | ≤ 50 | 1500-2500 字 | Quick scan, demo |
| **Standard** | 30-60 min | 20-30 | ≤ 200 | 5000-8000 字 | Normal review |
| **Deep** | 1-3 h | 40-60 | ≤ 500 | 10000-20000 字 | Strategic decision |

**Important:** Each tier has a hard tool-call budget that the audit script enforces. If the budget runs low mid-task, the script prints a "budget approaching limit, transitioning to write-up phase" message and proceeds to synthesis. This honesty-over-completeness behavior is intentional — better a partial report flagged as partial than a complete-looking report with degraded findings.

## Report structure (v1.15)

The generated `report.md` uses this structure (template-agnostic):

```markdown
# <Product> 产品深度体验报告

> 本报告聚焦：产品功能层的可理解性与完整性 — 不评 UI 美学

## 报告信息  (time / version / depth / template / language / 体验人)
## 目录    (TOC with anchor links + ⭐ marks v1.5+ synthesis sections)
## 0. Executive Summary
   0.1 一句话判定
   0.2 整体兑现度
   0.3 风险与机会 Top 3（功能层）
   0.4 立即可做的 Quick Wins
   0.5 综合评分（5 分制 × 6 维度）           ⭐ v1.5 synthesis
## 1. 产品概览
   1.1 基础信息
   1.2 测点速览
   1.3 产品 / 公司背景信息（递归发现）        ← v1.4
   1.4 产品战略抽象（X 化 叙事）             ⭐ v1.5 synthesis
   1.5 公司基本信息（web search 自动补充）   ⭐ v1.8 synthesis (WebSearch)
## 2. 体验方法论
## 3. 体验流程记录
   3.1 官网 Narrative 综合                  ⭐ v1.6 synthesis
   3.2 测点流程详情（按 17 个语义模块聚合）   ← v1.6 module clustering
      🏠 首页  🤖 AI 能力 / Agent  💰 定价  🎯 解决方案  🔌 集成 / API
      📚 产品官方介绍（递归发现）  🔐 登录后 Workspace (v1.7 login-mode)  ...
## 5. 第三方社区反馈（非官方）⭐                     ⭐ v1.15 synthesis #7 (NEW)
   ↳ Reddit / Product Hunt / Hacker News / G2 / Trustpilot
   ↳ 域名锚定 WebSearch + 真实 URL 引用 + 原文 blockquote
   ↳ "未找到讨论" 模板防编造（同 v1.11 §2.5 鲁棒性）
   ↳ 与官方叙事 §4.1 对比 gap

## 6. 总结
   6.1 一句话评价
   6.2 最大优点 Top 3
   6.3 最大风险 Top 3
   6.4 用户增长漏斗推断（**官网作用域**）       ⭐ v1.6 synthesis (v1.9 收紧)

(v1.13 已移除：原 §4 问题清单 + 附录 / 原 §5.5 下一季度建议 / 原 §5.6 元建议)
```

The canonical report structure is rendered by `scripts/generate_report.py`.

**Design decisions (v1.4 baseline):**
- **No §5 改进建议 / §6 横向对标** — removed by user feedback (these duplicate §4 and require separate competitor data that distracts from the target product)
- **Focus on functional features, not UI** — LLM prompt explicitly forbids commenting on visual design, button styling, layout aesthetics, or mobile responsiveness
- **§1.3 recursive background** — drills 2-3 levels deep into help/docs/resources to extract the product team's own "What is X" descriptions

**v1.5 — Synthesis pass introduced (3 LLM calls)**:
- §0.5 综合评分: 6-dim 5pt scorecard with cited evidence
- §1.4 战略 X 化叙事: 4-6 abstractions like "AI Employee 化 / Workspace 化"
- §4.1 综合产品级风险: de-duped 3-5 product-level risks from散落 P1/P2/P3

**v1.6 — A1+A2+A3**:
- §3.1 官网 Narrative 综合: keyword map + 5 narrative techniques (synthesis #4)
- §5.4 用户增长漏斗推断: multi-stage funnel with Aha moment inference (synthesis #5)
- §3.2 module clustering: flat 30+ test points → 17 semantic modules
- Hub fallback: when no /help|/docs found, try /about → /features → /how-it-works → /blog

**v1.7 — Login-mode**:
- `capture_login.py`: headed browser, auto-detects login completion, saves storage_state.json
- `audit.py --storage-state PATH --login-mode`: skip template loop, traverse dashboard nav, append L* findings
- Logout-link filter prevents accidentally killing the session mid-audit
- Synthesis re-runs on full findings (marketing + dashboard) for richer §3.2 + §5.4

**v1.8 — Web search synthesis**:
- §1.5 公司基本信息: synthesis #6 uses WebSearch + WebFetch to pull funding rounds, founders, headquarters, recent events from Crunchbase / TechCrunch / LinkedIn / press releases
- Every fact cited with source URL — no hallucinated funding amounts
- `llm.py` exposes `allowed_tools=['WebSearch', 'WebFetch']` for future tool-augmented prompts

**v1.15 — Community feedback chapter (CURRENT LATEST)**:
- **§5 第三方社区反馈** added as the penultimate chapter (倒数第二章), pushing 总结 to §6
- **synthesis #7** uses WebSearch + WebFetch to find user discussion on:
  - Reddit (any subreddit) — top priority, most candid
  - Product Hunt (launch posts + comments)
  - Hacker News (Show HN / Ask HN / related threads)
  - G2 / Trustpilot / Capterra (verified reviews)
  - (optional) Twitter/X public threads
- **Domain-anchored search** (`site:reddit.com "{domain}"`, `site:producthunt.com {product_name}`, etc.) to avoid pulling discussion about same-name companies
- **No screenshots needed for this chapter** — content is text + URL citations only (faster than v1.7 login-mode)
- **Strict NON-OFFICIAL labeling** — every finding tagged with source URL + original quote (blockquote format)
- **Format A** (found discussion): 5 sub-sections (调研范围 / 核心议题表 / 正面 / 负面 / 与官方叙事的差异)
- **Format B** (nothing found): explicit "未找到显著社区讨论" template with possible causes + manual search URLs
- **No fabrication rule** — same rigor as v1.11 §2.5: if can't find real discussions, output Format B instead of inventing
- **Why this matters**: marketing pages and the company's own help docs tell you what the product CLAIMS; community discussion tells you what users actually EXPERIENCE. Gap detection between §4.1 official Narrative and §5 community reality is one of the highest-signal sections for buyers.

**v1.13 — Trimmed report structure + workspace cleanup**:
- **§4 问题清单 REMOVED** — the P1/P2/P3 inventory was too noisy and duplicated §0.3 Top 3 风险. Decision-makers use §0.3 Top 3 (factual highlights from buckets) + §3.2 module-level observations (rich context) — that's enough.
- **附录 REMOVED** — A. 截图索引 was redundant with §3.2 inline screenshots; B. 原始数据 refs lose meaning when raw is cleaned (see below); C. 工具版本 was self-promotion noise.
- **§5 → §4 renumber** — total chapter is now 0/1/2/3/4. The final 总结 chapter is §4 (was §5).
- **Workspace cleanup (default ON)** — after `generate_report.py` produces report.md + report.html, it automatically deletes:
  - `raw/` (findings.jsonl + synthesis.json)
  - `.auth/` (storage_state.json)
  - `audit-meta.json`
  Final workspace contains ONLY `figs/` + `report.md` + `report.html`. This matches the user-facing "deliverable bundle" mental model.
- **Escape hatch**: `--keep-raw` flag preserves all intermediate files. Use when iterating on report templates or debugging.
- **One-way trip warning**: cleanup is destructive. Once raw/ + meta are gone, you CANNOT regenerate the report without re-running the full audit. If you'll need regen, add `--keep-raw` from the start.

**v1.11 — Entity identity verification for §1.5**:
- **Problem solved**: WebSearch on "Pika" returned Pika Labs / pika.art (AI video gen) when audited target was pika.me — wrong-entity attribution risk
- **Fix**: synthesis #6 prompt rewritten with mandatory 4-step identity verification:
  1. Extract identity anchors from audit observations (real product description, not just name)
  2. Domain-anchored search ONLY (`site:{domain}` / `"{domain}" funding` / etc) — pure-name searches forbidden
  3. Cross-verify each found company by checking that its LinkedIn / Crunchbase / Twitter / news article EXPLICITLY links back to the audited `{domain}` — if only name matches but domain differs, that's a different company; discard
  4. When identity can't be confirmed → output "需要用户确认" template listing candidate entities + asking for user-supplied LinkedIn/Crunchbase URLs, instead of fabricating facts
- **Output structure**: 
  - Format A (identity confirmed): `#### ✅ 实体身份已确认` + evidence chain + facts table with `置信度` column (✅ direct / ⚠️ inferred / ❌ omitted)
  - Format B (uncertain): `#### ⚠️ 实体身份未能确认 — 需要用户手动核实` + candidate table + user-confirmation prompt
- **Validated on Pika**: produced a 3-evidence chain correctly identifying pika.me as Pika Labs' new product line (2026-02 launch), with explicit caveat that funding/valuation data is mother-company-level, not pika.me-product-level

**v1.10 — Login HARD RULE**:
- **Removed §4.1 综合产品级风险** — the LLM-synthesized de-duped risk list felt redundant with §4 (raw P1/P2/P3 inventory) and §0.3 (Top 3 risks). Decision-makers can now form their own synthesis from raw data.
- **Removed §5.5 下一季度建议优先级** — too prescriptive (action lists drawn from P1/P2 buckets); the report should surface observations, not pretend to be a roadmap.
- **Removed §5.6 给产品方的元建议** — same reasoning. Elements that read like consulting deliverables have been stripped out.
- **§5.4 Growth funnel restricted to 官网 scope** — synthesis #5 now explicitly excludes L* (dashboard) findings. Funnel analysis stops at the conversion point (signup / demo submit / trial start). Post-login activation / retention / team viral analysis is no longer attempted (since it relied too heavily on what's behind login, which may or may not be captured by --login-mode).
- Synthesis count: **6 → 5 calls** (consolidated_risks removed from synthesis_pass). LLM budget drops slightly (~5 vs 6 calls).

## Credential security

Always honor these rules:

1. **No persistence** — credentials never written to `audit-meta.json`, `findings.jsonl`, or any other file
2. **No LLM exposure** — credentials never appear in prompts sent to Claude API
3. **Env var passing** — pass via `AUDIT_PWD`/`AUDIT_USER` env vars, not CLI args (which leak via `ps`)
4. **Memory only** — Playwright uses them in-page, then discards
5. **Explicit consent** — always confirm with user before accepting credentials
6. **Login-fail behavior** — if login fails, do NOT auto-retry (might lock account); report and exit gracefully

For implementation details, see `references/credential-handling.md`.

## Error handling

Common failure modes and recovery:

| Failure | Recovery |
|---|---|
| Page timeout (slow site) | Retry once with longer timeout; log and continue with degraded data |
| Captcha / bot detection | Stop, notify user, exit gracefully (don't fight defenses) |
| Login fails | Don't retry. Continue with public-page tests only. Note in report. |
| LLM API rate limit | Exponential backoff up to 3 attempts; if all fail, skip that test point |
| Playwright crash | Save partial findings; restart Playwright; resume from last checkpoint |
| Budget exhausted | Transition early to write-up phase, mark report as "partial" |

The audit script writes a checkpoint after each test point so `--resume` can pick up where it left off.

## Working with the user

- Be transparent about what the skill is doing — print N/M progress
- When the user provides a URL with no other context, default to `saas` template + `standard` depth, but confirm before starting
- For known products (e.g., the user says "测评 manus.im"), the skill can suggest a more specific template (e.g., `ai-tool` for Manus) — but always confirm
- After the report is generated, offer to:
  - Run it again with a different depth (e.g., user wants Deep version)
  - Run a comparison audit on a different URL (the user can synthesize manually)
  - Highlight specific findings inline

## Common requests after first run

| User says | Skill should |
|---|---|
| "再深一点" | Re-run with `depth=deep`, reuse workspace |
| "也测一下 https://other.com" | Run new audit, suggest using same template for comparability |
| "帮我把报告改成英文" | Re-run report generator with `--language en` (skip re-crawling) |
| "把 X 章节展开" | Show that section in chat, offer to expand specific test points |

## Files in this skill

| Path | Purpose | Since |
|---|---|---|
| `SKILL.md` (this file) | High-level orchestration | v1.0 |
| `templates/saas.md` | SaaS template (default) | v1.0 |
| `templates/multi-agent.md` | Multi-Agent product template | v1.0 |
| `templates/ai-tool.md` | Single-Agent AI tool template | v1.0 |
| `templates/ecommerce.md` | E-commerce template | v1.0 |
| `templates/_common.md` | Common test points all templates include | v1.0 |
| `scripts/audit.py` | Main audit + recursive background + login-mode + 6-call synthesis | v1.0→v1.8 |
| `scripts/generate_report.py` | Report generator (MD + HTML) — module clustering + 6 synthesis sections | v1.0→v1.8 |
| `scripts/browser.py` | Playwright wrapper (storage_state support added v1.7) | v1.0→v1.7 |
| `scripts/llm.py` | LLM abstraction layer (CLI + SDK backends; WebSearch tool support v1.8) | v1.1→v1.8 |
| `scripts/capture_login.py` | One-time session capture for login-mode (headed browser, auto-detect) | **v1.7** |
| `scripts/research_competitors.py` | **DEPRECATED (v1.4)** — competitor research, no longer invoked | v1.1→v1.4 |
| `references/architecture.md` | Detailed system architecture (read if debugging) | v1.0 |
| `references/depth-tiers.md` | Detail on depth tier budgets | v1.0 |
| `references/credential-handling.md` | Security details | v1.0 |
| `evals/evals.json` | Test cases for skill quality verification | v1.0 |

## Setup / dependencies

First-time use requires:

```bash
# Node + Playwright
npm install -g playwright
npx playwright install chromium

# Python deps
pip install anthropic playwright pyyaml jinja2

# Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...
```

The skill checks for these on first run and prompts user if missing.

## Why this skill exists

Professional product **feature** evaluations typically take 2+ hours of expert time per product to reach actionable depth. The most valuable elements of such evaluations are:

1. **Multi-page functional exploration** — 30-60 screenshots covering features, capabilities, product introductions, AND logged-in dashboard pages (v1.7)
2. **Recursive background discovery (v1.4)** — drilling into help/docs/resources to extract the product team's own "What is X" descriptions, which are often more accurate than the marketing copy on the homepage
3. **Cross-test synthesis (v1.5-v1.9)** — 5 LLM calls that aggregate散落 findings into a 6-dim scorecard, strategic X 化叙事 (4-6 abstractions), narrative手法分析, and a 官网-scoped growth funnel. v1.9 removed the prescriptive sections (consolidated risks, next-quarter action lists, meta advice) — observations and structural analysis only.
4. **Logged-in workspace audit (v1.7)** — `capture_login.py` enables the highest-value §3.2 Workspace Layer content that marketing pages can't reveal (e.g., onboarding quests, billing model, multi-user设置)
5. **Web-search-augmented company info (v1.8)** — synthesis #6 uses Claude's WebSearch tool to pull founding date, funding rounds, founder backgrounds, and recent events from Crunchbase / TechCrunch / LinkedIn with sourced citations
6. **Severity-graded feature-clarity issues** — P1/P2/P3 focused on functional understandability, NOT UI critique
7. **Honest transparency about tool budget limits** — partial reports labeled as such
8. **Structured deliverable** — MD + HTML with consistent template, ready to share

This skill encodes these as defaults so future audits achieve similar quality at ~10% the time cost.
