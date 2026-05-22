# {product_name} 产品体验报告

> **🤖 由 product-audit Skill 自动生成** — 这是一份基于 {template} 模板在 {depth} 深度下的自动化评测报告。报告中所有观察由 Browser Agent (Playwright) + Claude API 联合产出。最终决策建议结合人工 review。

## 报告信息

| 项 | 内容 |
|---|---|
| 产品 URL | {url} |
| 体验时间 | {completed_at} |
| 评测模板 | {template} |
| 深度档位 | {depth} |
| 测试点数 | {test_points_count} |
| LLM 预算 | {llm_calls_used} / {llm_calls_budget} |
| 报告语言 | {language} |
| 工具版本 | product-audit Skill v1.15 (legacy v1.0 template — actual report rendered by `scripts/generate_report.py`'s inline REPORT_TEMPLATE_MD) |

---

## 目录

- [0. Executive Summary](#0-executive-summary)
- [1. 产品概览](#1-产品概览)
- [2. 测试方法](#2-测试方法)
- [3. 体验流程记录](#3-体验流程记录)
- [4. 问题清单](#4-问题清单)
- [5. 改进建议](#5-改进建议)
- [6. 总结](#6-总结)
- [附录](#附录)

---

## 0. Executive Summary

{exec_summary}

---

## 1. 产品概览

URL: {url}
首次访问标题: {first_title}

---

## 2. 测试方法

本次评测使用 **{template}** 模板的 **{depth}** 深度档位，共执行 {test_points_count} 个测试点。

测试覆盖范围由模板定义（见 templates/{template}.md）。每个测试点包含：
- 浏览器操作（导航 / 点击 / 截图）
- LLM 解读（Claude Sonnet 4.6）
- 观察记录（JSONL 格式持久化）

---

## 3. 体验流程记录

{findings_body}

---

## 4. 问题清单

{issues_section}

---

## 5. 改进建议

{recommendations}

---

## 6. 总结

{summary}

---

## 附录

### A. 截图索引

{screenshots_index}

### B. 原始数据

完整原始观察记录见 `raw/findings.jsonl`。每行一个 JSON 对象，含 timestamp / URL / 截图引用 / 完整文本片段。

### C. 工具说明

本报告由 [product-audit](file:///Users/aa00945/Desktop/octok/.claude/skills/product-audit/) Claude Code Skill 生成。

- **后端**：Playwright（浏览器自动化） + Anthropic SDK（LLM 解读）
- **代码**：`scripts/audit.py` + `scripts/generate_report.py`
- **模板**：`templates/{template}.md`

---

*生成时间: {generated_at}*
