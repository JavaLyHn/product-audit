# product-audit

> **一个自动化深度产品测评 Claude Code Skill** — 把人工 2 小时的专家级产品调研压缩到 5–60 分钟，并产出一份结构化、可分享的 Markdown + HTML 报告。

[![Skill Version](https://img.shields.io/badge/skill-v1.16-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-orange.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

---

## 📌 项目简介

**product-audit** 是一个面向 SaaS / AI Agent / Web 产品 / 平台 的自动化深度测评工具，作为 [Claude Code Skill](https://docs.claude.com/) 形式发布。

它的核心理念是：

> **专注于"产品功能层的可理解性与完整性"，不评 UI 美学。**

也就是说，它不会告诉你"这个按钮颜色丑"、"这个布局应该改"，而是会回答这样的问题：

- 这个产品到底**能做什么、不能做什么**？
- 它的核心卖点（如"AI 记住你的品牌"、"端到端发布"）**机制透明吗、可信吗**？
- 定价 / 集成 / 上手路径 / 团队协作 等**关键决策证据是否齐全**？
- 它的 Narrative（叙事、品牌故事）**用了哪些手法、是否兑现**？
- 用户在 Reddit / Product Hunt / Hacker News / G2 上**真实评价如何**？（v1.15+）

### 设计灵感

本项目通过迭代对照 5 份手工撰写的咨询级产品分析报告（Artisan / Kuse / monday / Moxt / Okara）作为质量基线进行校准，目标是让自动化产出尽可能接近人工产品分析师的严谨度，但只花费 ~10% 的时间成本。

---

## 🎯 它为谁而生

| 角色 | 用例 |
|---|---|
| **产品经理 / 战略** | 竞品深度调研、横向对标素材库构建 |
| **投资 / 分析师** | DD 前置筛选、Portfolio 公司监控 |
| **设计 / 增长** | 拆解优秀产品的 Narrative / 增长漏斗 / 模块叙事手法 |
| **企业买家** | 评估 SaaS 是否值得采购前的功能完整性核查 |
| **创业者** | 看竞品有没有暴露关键漏洞、学习他们怎么讲故事 |

---

## ✨ 核心能力

### 一、 端到端自动化

```
parse intent → Playwright 浏览 → 截图 → Claude 解读 → 多页面 BFS 探索 → LLM 合成 → MD + HTML 报告
```

无需人工干预（登录态除外，见 HARD RULE 章节），从 URL 到一份 5000–15000 字的报告，全程自动。

### 二、 三档深度（按需取舍）

| 档位 | 用时 | 测试点 | 工具调用 | 报告字数 | 适用 |
|---|---|---|---|---|---|
| **Express** | 5–15 min | 10–15 | ≤ 50 | 1.5K–2.5K 字 | 快速扫盲 / 演示 |
| **Standard** | 30–60 min | 20–30 | ≤ 200 | 5K–8K 字 | 常规评测 |
| **Deep** | 1–3 h | 40–60 | ≤ 500 | 10K–20K 字 | 战略决策 |

预算会被严格执行 — 超额时脚本会**诚实地切到 write-up 阶段并标记报告为 "partial"**，绝不伪造完整性。

### 三、 多模板（按产品形态）

| Template | 适用场景 |
|---|---|
| `saas` | 通用 SaaS（默认） |
| `multi-agent` | 多智能体协作 AI 产品（多个命名 Agent） |
| `ai-tool` | 单 Agent / Chat 类 AI 工具 |
| `ecommerce` | 电商 / Marketplace |

每个模板定义自己的测点列表 + 报告 schema，所有模板都包含 `_common.md` 中定义的共通测点。

### 四、 递归背景发现（v1.4）

不止抓首页 — 会自动钻进 `help.X.com / docs.X.com / /about / /features / /blog` 等 2–3 层深度，挖出产品团队自己写的"What is X / Getting Started / Overview"页面，这些往往比首页营销文案更准确地揭示产品本质。

### 五、 6 路 LLM Synthesis Pass（v1.5–v1.15）

跨全部测点的 LLM 综合调用，产出 7 大⭐合成章节：

| 调用 | 章节 | 内容 |
|---|---|---|
| #1 | §2.4 战略 X 化叙事 | 4–6 个抽象（如 "AI Employee 化 / Workspace 化"） |
| #2 | §1.5 综合评分 | 6 维度 × 5 分制 评分卡（带证据引用） |
| #3 | §4.1 官网 Narrative | 关键词图谱 + 5 类叙事手法分析 |
| #4 | §6.4 用户增长漏斗 | 多阶段 Aha-moment 推断（官网作用域） |
| #5 | §2.5 公司基本信息 | **WebSearch**：融资 / 团队 / 上线时间，带源 URL（v1.8+）|
| #6 | §3.2 模块聚类 | 30+ 散落测点 → 17 个语义模块 |
| #7 | §5 第三方社区反馈 | **WebSearch**：Reddit / PH / HN / G2 非官方讨论（v1.15+）|

### 六、 实体身份验证（v1.11）

避免 "Pika" 这种同名公司混淆 — 强制使用 `site:` 域名锚定的 WebSearch 查询 + 4 步交叉验证（搜索结果中的 LinkedIn / Crunchbase / 新闻**必须明确链回审计域名**才被采纳）。无法验证时输出 "需要用户确认" 模板而不是编造事实。

### 七、 登录态审计（v1.7 + v1.10 强规则）

- `capture_login.py` — Headed 浏览器，用户登一次，自动检测完成并保存 session
- `audit.py --login-mode` — 拿着 session 进入 dashboard，遍历后台导航，附加 L* 测点
- **v1.10 HARD RULE**：检测到登录入口时，**必须**完成登录或显式 `--skip-login`，否则报告标记为 partial coverage

### 八、 工作区干净交付（v1.13）

报告生成后默认自动清理 `raw/ + .auth/ + audit-meta.json`，只保留：

```
NN-product/
├── figs/        (截图)
├── report.md    (主交付物)
└── report.html  (内嵌 base64 截图，可单文件分享)
```

如需后续重新生成报告，使用 `--keep-raw` 标志。

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. 解析用户意图（URL / template / depth / credentials / language）   │
│                                ↓                                      │
│  2. 初始化 workspace + 启动 Playwright                                │
│                                ↓                                      │
│  3. Phase 0: 首页导航 + 跨子域 hub 发现 + 登录入口检测                │
│                                ↓                                      │
│  4. 主测点循环（按模板执行 15–60 个测点）：                          │
│     ├─ Playwright: 导航 / 交互 / 截图                                │
│     ├─ Claude: 功能性解读（强约束不评 UI）                            │
│     └─ 持久化: 写入 figs/ + raw/findings.jsonl                       │
│                                ↓                                      │
│  5. Phase 0+: 自动探索剩余 nav 子页（standard 8 / deep 20）          │
│                                ↓                                      │
│  6. Phase 0++: 递归背景发现 (BFS depth 2-3, help/docs/about)         │
│                                ↓                                      │
│  7. (可选) Login-mode: dashboard 内部遍历，追加 L* 测点               │
│                                ↓                                      │
│  8. Synthesis Pass: 7 路 LLM 调用（含 2 路 WebSearch）                │
│                                ↓                                      │
│  9. generate_report.py → report.md + report.html → 清理 raw/         │
└──────────────────────────────────────────────────────────────────────┘
```

详细架构见 [`references/architecture.md`](references/architecture.md)。

---

## 🚀 安装

### 前置依赖

```bash
# Python 3.9+
python3 --version

# Playwright
pip install playwright
playwright install chromium

# Markdown 渲染
pip install markdown

# 可选：宽松 JSON 解析
pip install json-repair

# Claude Code CLI（已默认安装即可）
which claude   # 验证 $PATH 中可用
```

### 安装为 Claude Code Skill

```bash
# 用户全局
git clone git@github.com:JavaLyHn/product-audit.git ~/.claude/skills/product-audit

# 或项目级
git clone git@github.com:JavaLyHn/product-audit.git <your-project>/.claude/skills/product-audit
```

安装后在 Claude Code 中输入 `/help` 或直接说 "测评 https://example.com"，Skill 会自动激活。

---

## 📖 使用流程（详细）

### 方式 A：通过 Claude Code 自然语言触发（推荐）

直接在 Claude Code 对话中输入：

```
测评 https://manus.im
深度调研 https://artisan.co
audit https://lovable.dev
帮我评估一下 https://browser.use 这个产品
做一份 Cursor 的体验报告
```

Skill 会：
1. 自动解析 URL
2. 推断合适的 template（如 manus → `ai-tool`，Salesforce → `saas`）
3. 询问 / 默认 depth（无指示则 `standard`）
4. 弹窗征询登录意愿（如检测到登录入口）
5. 执行 + 生成 + 返回路径

### 方式 B：手动调用（CI / 批量场景）

```bash
cd .claude/skills/product-audit/scripts

# 关键：清除 API key，让 CLI 使用 Claude Code 订阅 auth（不走 API 计费）
unset ANTHROPIC_API_KEY

# Step 1: 公开页审计
python3 -u audit.py \
  --url "https://example.com" \
  --template ai-tool \
  --depth deep \
  --workspace /path/to/audits/01-example \
  --language zh-CN

# Step 2: (可选) 检测到登录入口时，捕获 session
python3 capture_login.py \
  --url https://dashboard.example.com \
  --output /path/to/audits/01-example/.auth/storage_state.json \
  --success-url-contains dashboard

# Step 3: (可选) Login-mode 审计 — 追加 L* 测点 + 重跑 synthesis
python3 -u audit.py \
  --url https://dashboard.example.com \
  --template ai-tool \
  --depth deep \
  --workspace /path/to/audits/01-example \
  --storage-state /path/to/audits/01-example/.auth/storage_state.json \
  --login-mode

# Step 4: 生成报告（默认清理 raw/）
python3 generate_report.py \
  --workspace /path/to/audits/01-example \
  --formats md,html

# 如果后续要再生成 / 调试报告模板，加 --keep-raw 跳过清理
```

### 工作区结构

执行过程中 / 完成后：

```
01-example/
├── figs/                        # 编号截图：01-c1_homepage.png, 02-c2_pricing.png ...
├── raw/                         # ⚠️ 默认会被清理（除非 --keep-raw）
│   ├── findings.jsonl           # 每测点的原始观察 + Claude 解读
│   └── synthesis.json           # 7 路 LLM 综合调用产出
├── .auth/                       # ⚠️ 默认会被清理
│   └── storage_state.json       # Playwright session（含 token，gitignore 必加）
├── audit-meta.json              # ⚠️ 默认会被清理
├── report.md                    # ← 最终交付
└── report.html                  # ← 最终交付（单文件可分享）
```

---

## 📋 报告结构（v1.15）

```markdown
# <Product> 产品深度体验报告

## 报告信息   (时间 / 版本 / 深度 / 模板 / 语言 / 体验人)
## 目录       (自动生成 TOC + ⭐ 标记合成章节)

## §1 Executive Summary
   1.1 一句话判定
   1.2 整体兑现度（覆盖度 / P1/P2/P3 计数 / 登录态状态）
   1.3 风险与机会 Top 3（功能层）
   1.4 立即可做的 Quick Wins
   1.5 综合评分（5 分制 × 6 维度）⭐

## §2 产品概览
   2.1 基础信息
   2.2 测点速览
   2.3 产品 / 公司背景信息（递归发现）
   2.4 产品战略抽象（X 化 叙事）⭐
   2.5 公司基本信息（WebSearch 自动补充）⭐

## §3 体验方法论
   3.1 测试用例矩阵
   3.2 评分与严重度分级
   3.3 限制与边界声明

## §4 体验流程记录
   4.1 官网 Narrative 综合（叙事手法 + 关键词图谱）⭐
   4.2 测点流程详情（按 17 个语义模块聚合）
      🏠 首页  🤖 AI 能力 / Agent  💰 定价  🎯 解决方案
      🔌 集成 / API  📚 产品官方介绍  🔐 登录后 Workspace ...

## §5 第三方社区反馈（非官方）⭐
   ↳ Reddit / Product Hunt / Hacker News / G2 / Trustpilot
   ↳ 域名锚定 WebSearch + URL 引用 + 原文 blockquote
   ↳ 与官方叙事 §4.1 对比 gap

## §6 总结
   6.1 一句话评价
   6.2 最大优点 Top 3
   6.3 最大风险 Top 3
   6.4 用户增长漏斗推断（官网作用域）⭐
```

⭐ 表示由 Synthesis Pass LLM 调用产出。

---

## 🔐 登录态 HARD RULE（v1.10）

> **如果产品有登录界面（大多数 SaaS 都有），Skill MUST 提示用户捕获登录态。否则报告标记为 incomplete。**

### 为什么这条规则存在

- 营销页告诉你产品**声称做什么**
- 登录后页面告诉你产品**实际是什么**
- §3.2 Workspace Layer 是产品分析最高价值的章节（onboarding 流 / 计费模型 / 多用户配置 / 实际功能边界）
- 跳过登录 = 报告 50% 盲区

### 检测层（3 层）

| 层 | 信号 |
|---|---|
| **Nav-link** | 文本 / 路径匹配 `log in / sign in / 登录 / /auth / /oauth` |
| **App-subdomain** | 跨子域 hub 匹配 `app.X / dashboard.X / admin.X / portal.X / console.X` |
| **URL-probe (v1.12)** | 即使首页无明显登录链接，也主动探测 `/login /signin` 等路径 |

任一层命中即设 `login_detected = true`。

### 决策树

```
audit-meta.json: login_detected == true ?
├─ NO  → 直接生成报告
└─ YES → login_mode_run == true ?
         ├─ YES → 直接生成报告（已完成）
         └─ NO  → login_skipped_by_user == true ?
                  ├─ YES → 生成报告（标注 partial coverage）
                  └─ NO  → MUST 提示用户登录
```

### 例外（可豁免登录）

1. 用户显式拒绝（"跳过登录" / "no login"）— 设 `login_skipped_by_user=true`，§1.2 标注 partial
2. 产品真的没有登录入口（detection 返回 false）
3. 登录被 CAPTCHA / OTP / KYC 阻断 — 设 `login_capture_failed=true`

---

## 🛡️ 凭据安全规则

1. **不持久化** — credentials 永不写入任何文件
2. **不出现在 LLM prompt 中** — 永不发往 Claude API
3. **Env var 传递** — 用 `AUDIT_USER` / `AUDIT_PWD`，不走 CLI args（避免 `ps` 泄漏）
4. **仅内存** — Playwright 用完即弃
5. **显式同意** — 接受 credentials 前必须征询
6. **登录失败不重试** — 防止账户锁定

详见 [`references/credential-handling.md`](references/credential-handling.md)。

---

## 📁 文件结构

```
product-audit/
├── SKILL.md                       # Claude Code skill manifest（先读这个）
├── README.md                      # 本文件（GitHub-facing）
├── README.old.md                  # 历史版本备份
├── .gitignore
│
├── scripts/
│   ├── audit.py                   # 主审计驱动（Playwright + Claude + 7 路 synthesis）
│   ├── browser.py                 # Playwright 封装（支持 storage_state）
│   ├── llm.py                     # LLM 抽象层（CLI 子进程 + SDK 后端；含 WebSearch tool）
│   ├── capture_login.py           # v1.7 session 捕获（headed 浏览器，自动检测登录完成）
│   ├── generate_report.py         # MD + HTML 渲染 + cleanup
│   └── research_competitors.py    # ⚠️ DEPRECATED v1.4（保留为历史代码）
│
├── templates/
│   ├── _common.md                 # 所有模板共通的测点
│   ├── saas.md                    # 默认 SaaS 模板
│   ├── multi-agent.md             # 多智能体协作产品
│   ├── ai-tool.md                 # 单 Agent / Chat 工具
│   └── ecommerce.md               # 电商 / Marketplace
│
├── references/
│   ├── architecture.md            # 系统架构深度解析
│   ├── depth-tiers.md             # Express/Standard/Deep 预算细节
│   └── credential-handling.md     # 登录态安全规则
│
├── assets/
│   └── report-template.md         # 早期 v1.0 模板（参考用；当前模板内嵌在 generate_report.py）
│
└── evals/
    └── evals.json                 # 质量验证测试用例
```

---

## 🛠️ 故障排查（FAQ）

| 现象 | 原因 / 解决 |
|---|---|
| `LLM ready (backend: cli)` 卡很久不动 | Claude Code CLI 在登录态过期 — 执行 `claude /login` 重新认证 |
| Playwright 报 `Executable doesn't exist` | 跑 `playwright install chromium` |
| Captcha / Bot 检测 | Skill 会优雅退出 — 不抗 captcha。改用 headed mode `--debug` 手动配合 |
| `unset ANTHROPIC_API_KEY` 后仍报 billing | 检查 `.env / shell rc / IDE config` 里是否注入了 key |
| Login mode 跳出 dashboard 后挂死 | 自动检测的 success-url 没匹配上 — 用 `--success-url-contains` 显式指定关键词 |
| 报告生成中字段缺失（"未找到"） | Synthesis #5/#7（WebSearch）在 entity 不确定时主动拒绝编造 — 这是 feature 不是 bug |
| 想要重新生成报告但 raw/ 被清理了 | 下次跑 `audit.py` 时加 `--keep-raw`，或重跑整个 audit |

---

## ⚠️ 已知限制

1. **硬编码绝对路径** — `SKILL.md` / `scripts/llm.py` / `evals/evals.json` / `assets/report-template.md` 内仍有 `/Users/aa00945/Desktop/octok/...` 的开发环境路径。`audit.py` 和 `generate_report.py` 本身是 path-agnostic（靠 `--workspace` 驱动），但 SKILL.md 中的示例命令需要按你的环境替换。
2. **Captcha / OTP 阻断** — 极少数产品在登录链路上有强 anti-bot，`capture_login.py` 无法自动绕过
3. **WebSearch 域名锚定的代价** — 对于域名特别小众 / 无任何外部讨论的产品，§5 会输出 "未找到讨论" 模板，这是**正确行为**（拒绝编造）但用户可能误以为是 bug

---

## 🗓️ 版本演进

| Version | Capability |
|---|---|
| **v1.4** | 递归背景发现 — BFS 钻入 help/docs/about 2–3 层 |
| **v1.5–v1.6** | 5 路 synthesis pass + 17-模块聚类 + 6 维评分卡 |
| **v1.7** | Login-mode — capture_login.py + --login-mode |
| **v1.8** | WebSearch 合成 — §2.5 公司基本信息（融资 / 团队 / 上线时间）|
| **v1.9** | 移除规约性章节（"下季度建议" 等）— 只保留客观观察 |
| **v1.10** | **HARD RULE**：登录态检测 → 必须捕获或显式跳过 |
| **v1.11** | §2.5 实体身份 4 步验证（防同名公司混淆，如 pika.me vs pika.art）|
| **v1.12** | HARD RULE 第 3 层：URL 探测（即使首页无登录链接也主动 probe）|
| **v1.13** | 精简结构 + 默认清理 raw/ |
| **v1.14** | TOC 完整化 + 章节从 §1 重新编号 |
| **v1.15** | §5 第三方社区反馈（synthesis #7，WebSearch 拉 Reddit/PH/HN/G2）|
| **v1.16** | §5 Format B 极简化（无社区讨论时只输出 1 句话，不列同名干扰项）|

---

## 🤝 贡献

欢迎 Issue 和 PR。重点关注：

- 新增 template（如 `developer-tool` / `b2b-marketplace` / `data-platform`）
- HARD RULE detection 信号补全（如 SSO-only / Magic-link login）
- 合成 prompt 优化（评分卡校准 / Narrative 手法识别）
- 国际化（目前主要为 zh-CN，欢迎 en / ja / ko 模板贡献）

---

## 📄 License

MIT License — 自由使用 / 修改 / 二次发行 / 商业使用，不附带任何形式的担保。

---

## 🙏 致谢

设计阶段对照了 5 份手工撰写的产品深度分析报告（Artisan / Kuse / monday / Moxt / Okara）作为质量基线 — 6 章结构和 7 路 synthesis 输出都是为了对标人工产品分析师的咨询级严谨度而校准的。

特别感谢 Anthropic Claude Code 团队提供的 Skill 机制和 WebSearch / WebFetch 工具能力，没有这些底层能力，自动化深度调研是无法实现的。

---

**Repo**: [github.com/JavaLyHn/product-audit](https://github.com/JavaLyHn/product-audit)
**Skill version**: v1.16
**Last updated**: 2026-05
