# E-commerce / Marketplace Template

Use when:
- The product is an e-commerce store, marketplace, or shopping platform
- The user wants to evaluate buying / selling UX, conversion funnels, trust signals

## Test points (in execution order)

Includes common points (C1-C8) plus e-commerce-specific points (E1-E12).

### Common (from _common.md)
- C1-C8

### E-commerce specific

**E1: Product browse / category navigation**
- Action: Click through top-level categories
- Observe: Depth of taxonomy, filter capabilities, sort options
- Output: `figs/e1-browse.png`

**E2: Product detail page (PDP)**
- Action: Click into 2-3 product detail pages
- Observe: Image quality, variant selection, description depth, social proof
- Output: `figs/e2-pdp.png`

**E3: Search experience**
- Action: Try common search queries (specific + ambiguous)
- Observe: Result relevance, autocomplete, filter facets
- Output: `figs/e3-search.png`

**E4: Add to cart flow**
- Action: Add product to cart
- Observe: Confirmation UX, cart preview, upsell suggestions
- Output: `figs/e4-cart.png`

**E5: Cart page**
- Action: Open cart
- Observe: Editability, shipping calculator visible, promo code field
- Output: `figs/e5-cart-page.png`

**E6: Checkout flow (no submit)**
- Action: Start checkout
- Observe: Steps, guest checkout option, payment method variety
- Output: `figs/e6-checkout.png`

**E7: Payment methods**
- Observe: Cards / PayPal / Apple Pay / local payment (WeChat / Alipay in CN context)
- Output: `figs/e7-payments.png`

**E8: Trust signals (purchase context)**
- Observe: Reviews / ratings on PDP? Verified buyer badges? Return policy clarity?
- Output: `figs/e8-trust.png`

**E9: Shipping / delivery info**
- Action: Find shipping policy
- Observe: Delivery time estimates, international shipping, free shipping threshold
- Output: `figs/e9-shipping.png`

**E10: Returns / refunds policy**
- Action: Find return policy page
- Observe: Window length, free returns?, restocking fees
- Output: `figs/e10-returns.png`

**E11: Account / order tracking**
- Observe: Logged-out vs logged-in experience for order tracking
- Output: `figs/e11-tracking.png`

**E12: Customer support channels (purchase context)**
- Observe: Pre-purchase chat vs post-purchase, response SLA
- Output: `figs/e12-support.png`

## Report sections this template produces

1. **Conversion funnel scorecard** — friction at each step
2. **Trust signals matrix** — for purchase decision
3. **Payment flexibility matrix** — by region
4. **Returns/refunds clarity**

## Depth tier mapping

| Depth | Test points | Time |
|---|---|---|
| Express | C1-C3, E1, E2, E4 | 8-12 min |
| Standard | C1-C8 + E1-E10 | 35-50 min |
| Deep | All E1-E12 + edge cases | 90-150 min |
