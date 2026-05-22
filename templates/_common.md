# Common Test Points

These test points are included in every template (SaaS, Multi-Agent, AI Tool, E-commerce). They cover the universal "first impression" experience that every web product can be evaluated on.

## Inclusion rules

| Depth | Common points included |
|---|---|
| Express | C1, C2, C3, C5 (4 points) |
| Standard | C1-C8 (all 8 points) |
| Deep | C1-C8 + revisit C2/C5 with edge cases |

---

## C1: Homepage 5-second test

**Action:** Navigate to base URL, take screenshot, capture above-the-fold HTML.
**Observe:**
- Is the product's value proposition clear in 5 seconds?
- Slogan / hero text / primary CTA visible?
- Trust signals (logos, testimonials, numbers)?
- Loading speed (TTI from Playwright metrics)?
**Output:** `figs/c1-homepage.png`, finding entry in `raw/findings.jsonl`

## C2: Pricing page

**Action:** Find "Pricing" link (try common selectors: nav, footer); navigate; screenshot.
**Observe:**
- Tiers count? Free tier exists?
- Pricing transparency (vs "Contact sales")?
- Currency, billing period
- Feature comparison clarity
**Output:** `figs/c2-pricing.png`, parsed tier list to `raw/pricing.json`

## C3: Sign-up flow (no credentials)

**Action:** Click "Sign up" / "Start free" / "Get started"; observe flow without submitting.
**Observe:**
- Steps required (email only? full form? OAuth options?)
- Friction signals (credit card upfront? required fields?)
- OAuth providers offered
**Output:** `figs/c3-signup-step1.png`, etc.

## C4: Login page

**Action:** Find login link; screenshot login form.
**Observe:**
- SSO / social login options
- "Forgot password" flow visible
- Magic link / passwordless options
**Output:** `figs/c4-login.png`

## C5: Footer audit

**Action:** Scroll to bottom; capture full footer.
**Observe:**
- Privacy / Terms / Cookie policy links present?
- Company info (registered name, address)
- Social media links
- Trust / compliance badges (GDPR, SOC2, etc.)
**Output:** `figs/c5-footer.png`, links extracted to `raw/footer-links.json`

## C6: Mobile responsiveness

**Action:** Resize viewport to 375x812 (iPhone 13); reload homepage; screenshot.
**Observe:**
- Layout adapts correctly?
- Touch targets large enough?
- Hamburger menu functional?
**Output:** `figs/c6-mobile.png`

## C7: Help / Documentation

**Action:** Find "Help" / "Docs" / "Support" link; navigate; screenshot landing page.
**Observe:**
- Documentation depth (placeholder vs real content?)
- Search functionality
- Tutorial / quickstart visible?
- Community link (Discord, forum)?
**Output:** `figs/c7-help.png`

## C8: 404 / error handling

**Action:** Navigate to `<base>/this-page-does-not-exist-12345`; screenshot.
**Observe:**
- Custom 404 page (vs default browser)?
- Helpful navigation (search, popular links)?
- Branded experience or generic?
**Output:** `figs/c8-404.png`

---

## How template-specific points reference common

In `saas.md` / `multi-agent.md` etc., common points are referenced by ID:

```yaml
test_points:
  - ref: _common.C1  # Homepage 5-second
  - ref: _common.C2  # Pricing
  - id: S1           # SaaS-specific: dashboard tour
    action: ...
```

The audit script merges common + template-specific into a single ordered list.
