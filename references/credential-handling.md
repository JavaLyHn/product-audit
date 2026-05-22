# Credential Handling

Security details for the product-audit skill. Read this if you're debugging credential issues or extending the skill to support new auth flows.

## Threat model

When a user provides credentials to audit a login-required product, three actors must NOT see those credentials:

1. **Local filesystem** — credentials must not be written to any file (config, log, transcript, screenshot metadata)
2. **Claude API** — credentials must not appear in any LLM prompt
3. **Process listing** — credentials must not be in `ps aux` output (no CLI args)

The only place credentials should exist:
- Memory of the Python process running `audit.py`
- Memory of the Playwright browser context, briefly during form-fill
- Environment variables of the audit process (parent shell may have them; that's the user's responsibility)

## Implementation rules

### Reading credentials
```python
# ✅ Correct
email = os.environ.get("AUDIT_USER")
password = os.environ.get("AUDIT_PWD")

# ❌ Wrong — CLI args leak via ps
parser.add_argument("--password")
```

### Passing to Playwright
```python
# ✅ Correct
page.fill("input[type=password]", os.environ["AUDIT_PWD"])

# ❌ Wrong — don't log
print(f"Logging in with {email} / {password}")
```

### Screenshots
- After login form fill but before submit, take screenshot ONLY if `--debug` is set
- Even then, mask the password field before screenshot:
```python
page.fill("input[type=password]", "•" * 12)  # mask before screenshot
page.screenshot(...)
page.fill("input[type=password]", actual_password)  # restore
```

### Network capture
- If you capture network traffic for audit, exclude login response bodies
- Strip Authorization / Cookie headers from any persisted network data

## User-facing checks

Before accepting credentials, audit.py should:

1. **Confirm intent** — "You're providing credentials. They will be kept in memory only and discarded when the audit ends. Confirm? [y/N]"
2. **Verify env vars are set** — fail-fast if user said yes but didn't set env vars
3. **Test login first** — if login fails, do NOT retry (account lockout risk). Continue with public-page tests only.

## Failure modes

| Symptom | Probable cause | Fix |
|---|---|---|
| Login form not found | Selector doesn't match | Override via template's `login_selector` config |
| Login succeeds but next page redirects to login | CSRF token / 2FA needed | This skill can't handle 2FA. Use a non-2FA test account. |
| Login appears to succeed but next test point fails | Session cookie not persisted | Check Playwright context lifetime |
| Audit completes but report contains login form screenshots | Failed login was treated as success | Review login success heuristic in browser.py |

## What this skill does NOT do (intentional limitations)

- **No 2FA handling.** Use audit-only accounts without 2FA, or provide a recovery code workflow externally.
- **No persistent session storage.** Each audit re-logs-in. This is by design (no risk of stale session being abused).
- **No SSO automation.** Google / GitHub / SAML logins are too varied. Use email+password test accounts.
- **No password manager integration.** Could be added later, but adds attack surface.

## If credentials leak

If a user reports that they think their credentials leaked from an audit:

1. **Have them rotate the password immediately.**
2. **Check `audit-meta.json` and `raw/findings.jsonl`** — these should NEVER contain credentials. If they do, that's a bug — file an issue.
3. **Check `figs/` for unmasked password screenshots** — if `--debug` was used, manually delete login-page screenshots.
4. **Don't blame the user.** This is a security responsibility of the skill.
