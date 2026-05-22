# Architecture

Detailed system architecture for the product-audit skill. Read this if you're extending the skill or debugging issues that span the audit + report-generation boundary.

## Component diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code Skill Host                      │
│                                                                  │
│  Skill invocation → SKILL.md → Claude orchestration             │
└───────────────────────────┬──────────────────────────────────────┘
                            │ calls
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       scripts/audit.py                           │
│                                                                  │
│   ┌──────────────┐    ┌──────────────────┐                      │
│   │ load_template│ →  │ DEPTH_BUDGET     │                      │
│   └──────────────┘    └─────────┬────────┘                      │
│                                  │                               │
│                                  ▼                               │
│         ┌──────────────────────────────────────────┐            │
│         │  test-point loop                          │            │
│         │  ┌────────────┐ ┌────────────────────┐  │            │
│         │  │ Playwright │ │ Anthropic SDK      │  │            │
│         │  │ (browser)  │ │ (interpretation)   │  │            │
│         │  └─────┬──────┘ └─────────┬──────────┘  │            │
│         │        ▼                  ▼              │            │
│         │   figs/N-slug.png   findings.jsonl      │            │
│         └──────────────────────────────────────────┘            │
└───────────────────────────┬──────────────────────────────────────┘
                            │ on completion
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    scripts/generate_report.py                    │
│                                                                  │
│   ┌──────────────┐    ┌──────────────────┐                      │
│   │ load workspace│ → │ categorize_findings (P1/P2/P3/G)│       │
│   └──────────────┘    └─────────┬────────┘                      │
│                                  ▼                               │
│         ┌──────────────────────────────────────────┐            │
│         │ render sections:                          │            │
│         │  - executive summary                      │            │
│         │  - findings body (numbered by test point) │            │
│         │  - issues section (severity-grouped)      │            │
│         │  - recommendations                        │            │
│         └──────────────────────────────────────────┘            │
│                                  ▼                               │
│              report.md + report.html (embedded screenshots)     │
└──────────────────────────────────────────────────────────────────┘
```

## Data contracts

### `audit-meta.json`
Single JSON object written by audit.py at completion:
```json
{
  "url": "https://example.com",
  "template": "saas",
  "depth": "standard",
  "language": "zh-CN",
  "test_points_executed": 22,
  "llm_calls_used": 22,
  "llm_calls_budget": 200,
  "completed_at": "2026-05-19T15:42:11"
}
```

### `raw/findings.jsonl`
One JSON object per line, appended as each test point completes. Schema:
```json
{
  "test_point_id": "C1",
  "test_point_name": "Homepage 5-second test",
  "timestamp": "2026-05-19T15:32:11",
  "url": "https://example.com/",
  "screenshot": "figs/01-c1-homepage.png",
  "observations": ["Slogan clear", "Pricing CTA not visible", ...],
  "severity": null,
  "raw_text_excerpt": "First 500 chars of page text..."
}
```

JSONL format is intentional: enables `--resume` (each line is a checkpoint), enables grep/jq on raw data.

### `figs/<N>-<slug>.png`
Numbered, semantic. Number ensures ordering matches execution order. Slug derived from test_point_id + name. Counter is global per session.

## Extension points

### Add a new template
1. Create `templates/<name>.md` following the structure of `saas.md`
2. Add the template's test points to `audit.py`'s `load_template` (MVP) or implement markdown parsing (future)
3. Add an entry to `evals/evals.json` for the new template

### Add a new test-point action type
1. Add a case to `execute_test_point` in `audit.py` (currently handles: navigate, find_link, scroll_bottom)
2. Document the new action in `_common.md` or template-specific docs

### Add a new output format (e.g., PDF)
1. Add `pdf` to the `--formats` argument parser in `generate_report.py`
2. Implement `generate_pdf_report` using e.g. `weasyprint` from the HTML

### Use a different LLM provider
1. Replace `Anthropic` import with the new provider's SDK
2. Update `interpret_with_llm` to call it
3. Update `references/depth-tiers.md` cost estimates

## What's NOT in MVP (intentional)

- **No comparison mode** — designed for single-product depth. Users compare manually.
- **No scheduling / recurring audits** — one-shot CLI invocation per run.
- **No web UI** — Claude Code is the UI.
- **No multi-template per audit** — one template per run; users can re-run with different templates.
- **No incremental re-audit** — if you re-run on the same URL, it overwrites (use a different `--workspace` to keep history).

These are deferred until MVP validates value.
