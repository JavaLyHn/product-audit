# Multi-Agent Product Template

Use when:
- The product positions itself as having multiple AI agents collaborating (e.g., Lindy, Coze, or similar "AI team" platforms)
- The product features a "team of AI" / "AI employees" narrative
- The user wants to evaluate AI orchestration, agent collaboration, role boundaries

## Test points (in execution order)

Includes all common points (C1-C8) plus multi-agent-specific points (M1-M15).

### Common (from _common.md)
- C1-C8 (see _common.md)

### Multi-Agent specific

**M1: Agent inventory**
- Action: Find the page listing all agents/employees
- Observe: # of agents, distinct roles, naming convention (named persons vs functional labels)
- Output: `figs/m1-agents.png`, parsed list to `raw/agents.json`

**M2: Agent role descriptions**
- Action: Click into each agent's profile page (up to 6)
- Observe: Role specialization depth, skills listed, sample tasks
- Output: `figs/m2-agent-{name}.png` for each

**M3: Agent persona / humanization**
- Observe: Real photos vs icons, "Partner" / "Employee" terminology, personalities
- Capture: Persona signals in copy

**M4: Task orchestration / coordination**
- Action: Identify the "Navigator" / orchestrator agent (if exists)
- Observe: How tasks are dispatched, OKR / project / workflow protocols
- Output: `figs/m4-orchestrator.png`

**M5: Skills / Capabilities catalog**
- Action: Find Skills / Tools / Integrations page (per-agent or global)
- Observe: # of skills, real vs placeholder, integration vs internal
- Output: `figs/m5-skills.png`, count to `raw/skills.json`

**M6: Agent-to-channel deployment (key differentiator)**
- Action: Check each agent's "Channels" / "Deploy" tab
- Observe: Can agents be deployed to Telegram/WhatsApp/Slack? Real configurable or "coming soon"?
- Click into one config modal to verify if functional
- Output: `figs/m6-channels.png`, `figs/m6-channel-config-modal.png`

**M7: Persistent enterprise context**
- Action: Find company-info / knowledge-base / RBAC pages
- Observe: Does the product have a notion of "company context" that agents share? Or session-only?
- Output: `figs/m7-context.png`

**M8: Multi-Agent collaboration demo (login required for Standard+)**
- Action: If logged in, trigger a multi-agent task (use product's example prompts)
- Observe: Do agents actually hand off? Or does one agent answer for all?
- Output: `figs/m8-collab.png`

**M9: Role boundary / escalation behavior**
- Action: Try giving an agent a task outside its specialization
- Observe: Does the agent refuse and escalate? Or hallucinate-answer?
- This is a CRITICAL differentiator — most LLM products don't refuse
- Output: `figs/m9-escalation.png`

**M10: Decision break points (human-in-loop)**
- Observe: Does the product pause for user approval at decision points?
- Or fully autonomous (no breaks)?
- Output: `figs/m10-decision.png`

**M11: Tool call transparency**
- Action: Trigger a task; observe how tool calls are surfaced
- Observe: Visible / hidden? Real URLs shown? Internal IDs leaked?
- Output: `figs/m11-tools.png`

**M12: Artifact output form**
- Action: After a task completes, examine the output
- Observe: Just text / downloadable file / shareable URL / interactive page?
- Critical for: Where do artifacts live (file tab, chat, separate panel)?
- Output: `figs/m12-artifact.png`

**M13: Cross-agent state / data sharing**
- Action: Have Agent A do something; check if Agent B can see it
- Observe: True shared state vs siloed conversations
- Output: `figs/m13-shared-state.png`

**M14: Onboarding flow for agents (hire / activate)**
- Action: Test the "hire" / "activate" agent flow
- Observe: Free? Paywall? Friction count?
- Output: `figs/m14-hire.png`

**M15: Tool budget transparency (Deep depth)**
- Action: Run a long task; observe if product discloses budget limits
- Observe: Honest "approaching limit" notifications? Or silent termination?
- Output: `figs/m15-budget.png`

## Report sections this template produces

Multi-Agent reports include unique sections beyond the standard structure:

1. **Agent roster table** — name, role, skills, hire status
2. **Orchestration architecture diagram** — how agents coordinate
3. **Role-boundary scorecard** — does each agent know its limits?
4. **Channel deployment matrix** — which channels are real vs placeholder
5. **Compare to "AI employee" / "AI team" market positioning** — vs other multi-agent or "AI employee" branded products in §6

## Depth tier mapping

| Depth | Test points | Time |
|---|---|---|
| Express | C1-C3, M1, M2 (sample 2 agents), M5 | 10-15 min |
| Standard | C1-C8 + M1-M11 (no login-required) | 40-60 min |
| Deep | All M1-M15 + login flow | 90-180 min |

## Why this template matters

Multi-agent products are a fast-growing AI product category (e.g., Lindy / Coze / OpenAI Swarm / various "AI team" SaaS). They share common architectural patterns but differ on:
- Agent specialization depth (named persons vs generic roles)
- Orchestration protocol (chat-based vs OKR-based vs workflow-DAG)
- Persistent context (per-session vs cross-session vs cross-agent shared)
- Channel deployment (closed loop vs open to external channels)

This template evaluates products on all these axes.
