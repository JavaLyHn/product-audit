# SaaS Generic Template

The default template. Use this when:
- The product is a typical B2B / B2C SaaS web app
- You don't have a more specific template (multi-agent / ai-tool / ecommerce)
- The user just said "评测这个产品" without specifying type

## Test points (in execution order)

Includes all common points (C1-C8) plus SaaS-specific points (S1-S15).

### Common (from _common.md)
- C1: Homepage 5-second test
- C2: Pricing page
- C3: Sign-up flow (no submit)
- C4: Login page
- C5: Footer audit
- C6: Mobile responsiveness
- C7: Help / docs
- C8: 404 handling

### SaaS-specific

**S1: Feature pages tour**
- Action: Walk through main "Features" / "Product" nav links (up to 5)
- Observe: Feature depth, screenshot quality, demo videos, copy clarity
- Output: `figs/s1-feature-{N}.png`

**S2: Use case / industry pages**
- Action: Find use-case / industry-vertical pages
- Observe: Specificity (real cases vs generic), customer logos, case study links
- Output: `figs/s2-usecase.png`

**S3: Integrations page**
- Action: Navigate to "Integrations" / "Connect" page
- Observe: # of integrations listed, real vs "coming soon", popular tools covered (Slack/Gmail/Salesforce etc.)
- Output: `figs/s3-integrations.png`, parsed list to `raw/integrations.json`

**S4: Customer / logo wall**
- Action: Find customer logo section (homepage or dedicated page)
- Observe: Logo recognizability, # of customers, geo distribution
- Output: `figs/s4-customers.png`

**S5: Case studies / testimonials**
- Action: Find "Case studies" / "Customer stories" section
- Observe: Quantified results in stories? Real names / titles? Video testimonials?
- Output: `figs/s5-casestudy.png`

**S6: Blog / Resources**
- Action: Navigate to "Blog" or "Resources"
- Observe: Posting frequency (latest 3 dates), topical depth, SEO presence
- Output: `figs/s6-blog.png`

**S7: About / Company page**
- Action: Navigate to "About"
- Observe: Founders named? Team size? Funding history? HQ location?
- Output: `figs/s7-about.png`

**S8: Careers page**
- Action: Navigate to "Careers"
- Observe: # of open roles (growth indicator), remote-friendly, office locations
- Output: `figs/s8-careers.png`

**S9: API / Developer docs (if present)**
- Action: Find API docs link
- Observe: Doc completeness, SDK languages, auth methods, rate limits documented
- Output: `figs/s9-api-docs.png`

**S10: Free trial / demo experience (Standard+ depth)**
- Action: If free trial available, sign up (use temp email or skip if requires CC)
- Observe: Onboarding steps, "aha moment" time, immediate value
- Output: `figs/s10-onboarding-{N}.png`

**S11: Dashboard tour (login required, Standard+ depth)**
- Action: If credentials provided, log in and explore main nav
- Observe: First-screen orientation, empty states, primary CTAs
- Output: `figs/s11-dashboard.png`

**S12: Trust / Security page**
- Action: Find security / trust / compliance page
- Observe: SOC2 / ISO 27001 / HIPAA certifications? Data location disclosed?
- Output: `figs/s12-trust.png`

**S13: Mobile app (Deep depth only)**
- Action: Check App Store / Play Store links if mentioned
- Observe: Mobile app exists? Rating? Last update?
- Output: `figs/s13-mobile.png`

**S14: Customer support channels**
- Action: Test "Contact us" / chat widget / email links
- Observe: Live chat available? Response SLA stated? Multi-language support?
- Output: `figs/s14-support.png`

**S15: Competitor mention / SEO comparison pages (Deep depth only)**
- Action: Look for "Alternatives to X" or "vs Competitor" pages
- Observe: How they position vs competitors, fairness of comparison
- Output: `figs/s15-vs.png`

## Report sections this template produces

Beyond the standard structure (Exec Summary / Product Overview / Issues / etc.), SaaS reports include:

1. **Trust signals scorecard** — table of trust indicators with present/absent
2. **Integration ecosystem analysis** — count of real vs placeholder integrations
3. **Pricing transparency score** — 1-5 scale
4. **Onboarding friction score** — 1-5 scale based on S3/S10 observations

## Depth tier mapping

| Depth | Test points included | Estimated time |
|---|---|---|
| Express | C1, C2, C3, C5, S3, S4, S7 (7 points) | 8-12 min |
| Standard | C1-C8 + S1-S12 (20 points) | 35-50 min |
| Deep | C1-C8 + S1-S15 + re-explore (25+ points) | 90-150 min |
