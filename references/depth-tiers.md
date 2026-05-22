# Depth Tiers

The product-audit skill offers three depth tiers. Understanding the budget mechanics helps you debug "audit terminated early" issues and choose the right tier per use case.

## Tier definitions

```python
DEPTH_BUDGET = {
    "express":  {"max_test_points": 15, "max_llm_calls": 50,  "report_target_words": 2000},
    "standard": {"max_test_points": 30, "max_llm_calls": 200, "report_target_words": 6500},
    "deep":     {"max_test_points": 60, "max_llm_calls": 500, "report_target_words": 15000},
}
```

## How budgets are enforced

`audit.py` tracks LLM calls in a counter. After each test point's interpretation call, the counter increments. When `llm_calls >= max_llm_calls`, subsequent test points are still executed (screenshot + page text capture) but their LLM interpretation is replaced with:

```
[Budget approaching limit — manual review needed]
```

This is intentional: the principle is **honesty over completeness**. A report marked "partial — budget exhausted at point N/M" is more useful than a report that silently degrades to shallow observations.

## Picking the right tier

| Use case | Recommended tier |
|---|---|
| Quick sanity check (is this product worth a deeper look?) | Express |
| Normal due diligence / weekly competitive intel | Standard |
| Pre-acquisition / pre-investment / strategic decision | Deep |
| Comparing many products (10+) | Express (avoid budget exhaustion) |
| Comparing few products (2-4) in depth | Standard |

## Cost estimation

Assuming Claude Sonnet 4.6 API pricing as of 2026-Q1:

| Tier | LLM calls × avg cost | Playwright time | Total $ estimate |
|---|---|---|---|
| Express | 50 × $0.01 = $0.50 | 5-15 min | $0.50-0.80 |
| Standard | 200 × $0.01 = $2.00 | 30-60 min | $2.00-3.00 |
| Deep | 500 × $0.01 = $5.00 | 1-3 h | $5.00-8.00 |

Costs assume avg 1500 input + 500 output tokens per call. Real costs vary by:
- Page text length (input tokens)
- Model choice (Sonnet vs Opus vs Haiku)
- Whether screenshots are sent (they triple token cost)

## Tuning the tiers

If you frequently exhaust budget on `standard`, increase the `max_llm_calls` in `audit.py`. If you find express reports too thin, raise `report_target_words` in `generate_report.py`.

## Why three tiers (not continuous)

Continuous sliders cause decision fatigue ("am I picking enough budget?"). Three named tiers map cleanly to mental models:

- **Express** = "I just need to know if this is worth my time"
- **Standard** = "I'm doing real work; give me a full picture"
- **Deep** = "This decision is high-stakes; spare no expense"

Mirrors Manus 1.6 Lite vs Max, AutoGLM standard vs deep mode, etc.
