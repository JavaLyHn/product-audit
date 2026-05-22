"""One-time login session capture for logged-in product audits.

Opens a HEADED Playwright browser at the target login URL. User logs in
manually in that browser window. The script POLLS for login-success
markers (no password field on page + URL contains target path) and
auto-saves storage_state once detected. No terminal interaction required.

Privacy notes:
- Credentials are NEVER typed in or read by this script — user types them
  into the headed browser window themselves.
- The saved JSON contains session tokens / cookies but NOT plaintext passwords.
- Tokens expire (typically 1-30 days). Re-run this script if audit fails
  with auth errors.

Usage:
    python3 capture_login.py \\
        --url https://dashboard.example.com/manage-ava \\
        --output /path/to/workspace/.auth/storage_state.json \\
        [--success-url-contains manage-ava]   # auto-detect hint
"""

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description="Capture a logged-in browser session for audit reuse")
    parser.add_argument("--url", required=True,
                        help="Starting URL — typically a logged-in app page that triggers login redirect")
    parser.add_argument("--output", required=True,
                        help="Path to save storage_state.json (will create parent dirs)")
    parser.add_argument("--viewport", default="1440x900",
                        help="Browser viewport, e.g. 1440x900")
    parser.add_argument("--success-url-contains", default=None,
                        help="Substring that, when seen in URL, signals login success. "
                             "Defaults to the path portion of --url.")
    parser.add_argument("--max-wait-sec", type=int, default=600,
                        help="Max seconds to wait for login (default 600 = 10 min)")
    parser.add_argument("--stable-sec", type=int, default=4,
                        help="How long URL+page must stay 'logged-in stable' before saving (default 4s)")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        vw, vh = (int(x) for x in args.viewport.lower().split("x"))
    except Exception:
        print(f"❌ Invalid viewport: {args.viewport} (expected 1440x900)")
        return 1

    # Default success-url-contains: extract path from --url
    success_hint = args.success_url_contains
    if not success_hint:
        try:
            parsed = urlparse(args.url)
            path = (parsed.path or "/").rstrip("/")
            if path and path != "/":
                # Use last segment (e.g. "/manage-ava" → "manage-ava")
                success_hint = path.split("/")[-1]
            else:
                # Fall back to hostname (e.g. "dashboard.artisan.co")
                success_hint = parsed.hostname or ""
        except Exception:
            success_hint = ""

    # Login-form indicators we expect to DISAPPEAR after login
    LOGIN_URL_HINTS = re.compile(r"(/login|/signin|/sign[-_]in|/auth|/oauth|accounts\.google)", re.IGNORECASE)

    print("=" * 72)
    print("🔐 Login session capture (auto-detect mode)")
    print("=" * 72)
    print(f"  Opening URL: {args.url}")
    print(f"  Will save to: {output}")
    print(f"  Auto-detect success when URL contains: {success_hint!r}")
    print(f"  Max wait: {args.max_wait_sec}s, stability window: {args.stable_sec}s")
    print()
    print("  Instructions:")
    print("    1. A browser window will open (may take a few seconds)")
    print("    2. Log in to the product in that window")
    print("    3. After successful login, this script will auto-detect and save")
    print("    4. The browser will close automatically when session is captured")
    print()
    print("  Privacy: cookies + localStorage saved. Password NOT captured.")
    print("=" * 72)
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": vw, "height": vh},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 product-audit/1.0"
            ),
        )
        page = context.new_page()
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"⚠️  Initial navigation slow / failed: {str(e)[:200]}")
            print("    (Browser is still open — log in manually)")

        print("✋ Polling for login completion (URL stable + no password field)...")
        last_url = ""
        stable_ticks = 0
        ticks_per_sec = 2  # poll every 0.5s
        max_ticks = args.max_wait_sec * ticks_per_sec
        stable_ticks_needed = args.stable_sec * ticks_per_sec
        last_log_url = ""

        for tick in range(max_ticks):
            time.sleep(1.0 / ticks_per_sec)
            try:
                current_url = page.url
                has_password = page.locator("input[type=password]").count() > 0
                on_login_url = bool(LOGIN_URL_HINTS.search(current_url))
            except Exception:
                continue

            # Log URL transitions
            if current_url != last_log_url:
                marker = "🔓" if (not has_password and not on_login_url) else "🔒"
                print(f"   {marker} {current_url[:90]}  pwd_field={has_password} login_url={on_login_url}")
                last_log_url = current_url

            # Success condition: URL stable + no password field + not on login page +
            # URL contains the success hint
            url_stable = (current_url == last_url)
            looks_logged_in = (not has_password) and (not on_login_url)
            hint_match = (success_hint == "" or success_hint.lower() in current_url.lower())

            if url_stable and looks_logged_in and hint_match:
                stable_ticks += 1
                if stable_ticks >= stable_ticks_needed:
                    print(f"   ✅ Stable logged-in state detected: {current_url}")
                    break
            else:
                if stable_ticks > 0:
                    pass  # reset silently
                stable_ticks = 0

            last_url = current_url
        else:
            print(f"\n❌ Timed out after {args.max_wait_sec}s — did you log in?")
            print(f"   Last URL: {last_url}")
            browser.close()
            return 1

        try:
            captured_url = page.url
            try:
                captured_title = page.title()
            except Exception:
                captured_title = "(unknown)"
            context.storage_state(path=str(output))
            print()
            print("=" * 72)
            print(f"✅ Session saved → {output}")
            print(f"   Captured at: {captured_url}")
            print(f"   Page title: {captured_title}")
            print()
            print("   Next step:")
            print(f"     python3 audit.py \\")
            print(f"       --url {args.url} \\")
            print(f"       --template multi-agent \\")
            print(f"       --depth standard \\")
            print(f"       --workspace <existing_workspace> \\")
            print(f"       --storage-state {output} \\")
            print(f"       --login-mode")
            print("=" * 72)
        except Exception as e:
            print(f"❌ Failed to save storage_state: {e}")
            browser.close()
            return 1

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
