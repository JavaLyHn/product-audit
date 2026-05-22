# AI Tool / Single-Agent Template

Use when:
- The product is a single AI assistant / autonomous agent (Manus / Genspark / ChatGPT / Claude / Devin)
- The product is positioned as a "tool" rather than a "team"
- No multi-agent narrative

## Test points (in execution order)

Includes common points (C1-C8) plus AI-tool-specific points (A1-A12).

### Common (from _common.md)
- C1-C8 (see _common.md)

### AI-tool specific

**A1: First-prompt experience**
- Action: After login, identify the main chat/input box
- Observe: Default mode, suggested prompts, input affordances (file upload, voice, etc.)
- Output: `figs/a1-input.png`

**A2: Suggested example prompts**
- Observe: Quality of examples (specific vs generic), coverage of use cases
- Output: `figs/a2-examples.png`, list to `raw/example-prompts.json`

**A3: Tool / capability disclosure**
- Action: Find any UI showing available tools (web search, code, image gen, etc.)
- Observe: Visible to user? Or hidden / auto-selected?
- Output: `figs/a3-tools.png`

**A4: Run a sample task (Standard+ depth)**
- Action: Use the benchmark prompt (overridable via `--benchmark-prompt`; default is a structured market-research request — see end of this file)
- Observe: Total time, intermediate updates, tool calls shown
- Output: `figs/a4-task-progress.png` (sequence of screenshots)

**A5: Task plan visibility**
- During A4, capture: Does the agent reveal a task plan?
- Observe: Step counter (N/M) vs free-form, granularity
- Output: `figs/a5-taskplan.png`

**A6: Tool call transparency**
- During A4, capture each tool invocation
- Observe: Specific search query shown? Real URLs fetched? Internal IDs?
- This is where many products fail (e.g., Navigator's "静默执行" anti-pattern)
- Output: `figs/a6-toolcall.png`

**A7: Artifact output**
- After A4, examine the final deliverable
- Observe: Format (text / md / HTML / live URL / file download)
- Output: `figs/a7-artifact.png`

**A8: Citations / sourcing**
- Observe: Are claims sourced? Inline citations vs end-of-report references vs none vs fake [N†] without backref
- Critical for credibility
- Output: `figs/a8-citations.png`

**A9: Completion UX**
- After A4 completes, observe:
- Recommended follow-ups? Feedback solicitation (stars/thumbs)? Upsell?
- Output: `figs/a9-completion.png`

**A10: Sharing / export**
- Action: Try to share the result
- Observe: Live URL? PDF export? Embed code? Just text copy?
- Output: `figs/a10-share.png`

**A11: Task history / persistence**
- Action: Refresh page / open new session
- Observe: Past tasks accessible? Organized by project?
- Output: `figs/a11-history.png`

**A12: Pricing tiers (Deep depth)**
- Examine pricing model: pay-per-task / monthly subscription / credits
- Observe: Free quota generous? Pro tier triggers visible?
- Output: `figs/a12-tiers.png`

## Report sections this template produces

AI-tool reports emphasize:

1. **Task execution scorecard** — speed / depth / tool transparency
2. **Artifact quality matrix** — format / shareability / persistence
3. **Citation rigor** — inline real / end-of-report / fake / none
4. **vs benchmark products** — implicit comparison to Manus/Genspark/AutoGLM via shared evaluation prompt

## Depth tier mapping

| Depth | Test points | Time |
|---|---|---|
| Express | C1-C3, A1, A2 | 8-12 min |
| Standard | C1-C8 + A1-A10 (single task run) | 30-50 min |
| Deep | All A1-A12 + multi-task / edge cases | 90-150 min |

## Benchmark prompt (for A4 task run)

The skill ships with a generic market-research benchmark prompt designed to exercise:
search depth / multi-step reasoning / citation rigor / artifact format / completion UX.

Default benchmark prompt (overridable via `--benchmark-prompt`):

```
We are a mid-sized B2B SaaS company (~200 employees, registered in Singapore).
Our flagship product helps Chinese export-oriented companies expand to Southeast
Asia and East Asia markets. We want to understand: (1) market opportunity sizing
across Singapore, Vietnam, Thailand, Indonesia, Japan, Korea; (2) competitor
landscape; (3) recommended go-to-market sequence. Output a structured report.
```

Users can override with `--benchmark-prompt "my custom prompt"` to test the AI
tool against their own representative task. Using the same prompt across audits
enables apples-to-apples comparison.
