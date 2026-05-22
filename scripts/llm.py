"""LLM abstraction layer for product-audit skill.

Why this exists:
- Anthropic API requires separate billing/credits
- But Claude Code users already have Claude.ai subscription
- The `claude` CLI uses subscription auth, bypassing API billing

This module wraps both backends with a single .call() interface:
- CLI backend (default): subprocess to `claude -p` — uses subscription
- SDK backend (fallback): anthropic.Anthropic — uses API credits

Default is CLI. Set AUDIT_LLM_BACKEND=sdk to force SDK.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _load_env_file(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file."""
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Load .env from common locations on import
for _p in [
    Path("/Users/aa00945/Desktop/octok/.env"),
    Path.cwd() / ".env",
]:
    _load_env_file(_p)


def _detect_backend() -> str:
    """Decide which backend to use.

    Priority:
    1. AUDIT_LLM_BACKEND env var (cli|sdk)
    2. If `claude` CLI is available → cli
    3. If ANTHROPIC_API_KEY is set → sdk
    4. Raise — no backend available
    """
    explicit = os.environ.get("AUDIT_LLM_BACKEND")
    if explicit in {"cli", "sdk"}:
        return explicit

    if shutil.which("claude"):
        return "cli"

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "sdk"

    raise RuntimeError(
        "No LLM backend available. Install Claude Code CLI "
        "(`claude` command) or set ANTHROPIC_API_KEY."
    )


# ============ CLI backend ============

def _call_cli(prompt: str, timeout: int = 180,
              allowed_tools: Optional[list] = None) -> str:
    """Call Claude via `claude -p` subprocess. Uses Claude Code subscription auth.

    Key trick: strip ANTHROPIC_API_KEY from subprocess env so `claude` CLI
    falls back to subscription auth instead of using a possibly-empty API key.

    allowed_tools: list of tool names to pre-approve (avoids interactive
    permission prompt in headless mode). Use for prompts that need WebSearch
    / WebFetch / Bash etc.
    """
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    cmd = ["claude", "-p"]
    if allowed_tools:
        # claude -p uses --allowedTools (comma-separated)
        cmd += ["--allowedTools", ",".join(allowed_tools)]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()[:300]
            return f"[CLI error: {err}]"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"[CLI timeout after {timeout}s]"
    except FileNotFoundError:
        return "[CLI error: claude not found in PATH]"


# ============ SDK backend ============

_sdk_client = None  # Lazy-initialized


def _get_sdk_client():
    global _sdk_client
    if _sdk_client is not None:
        return _sdk_client
    try:
        from anthropic import Anthropic
        _sdk_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        return _sdk_client
    except ImportError:
        raise RuntimeError("anthropic SDK not installed")


def _call_sdk(prompt: str, max_tokens: int = 4096, model: str = "claude-sonnet-4-6") -> str:
    """Call Claude via Anthropic SDK. Uses API credits."""
    try:
        client = _get_sdk_client()
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return f"[SDK error: {e}]"


# ============ Public interface ============

def call(prompt: str, *, max_tokens: int = 4096, model: str = "claude-sonnet-4-6",
         timeout: int = 180, allowed_tools: Optional[list] = None) -> str:
    """Call the LLM with the given prompt. Returns the text response.

    Errors are returned as `[error: ...]` strings rather than raised — audit
    can continue with partial findings if some calls fail.

    timeout: seconds before subprocess kill (CLI backend only). Bump for
    web-search-enabled prompts which can take 60-180s.

    allowed_tools: pre-approved tool list for CLI backend's headless mode
    (e.g. ['WebSearch', 'WebFetch']). Ignored by SDK backend (SDK doesn't
    support these tools through the bare messages API).
    """
    backend = _detect_backend()
    if backend == "cli":
        return _call_cli(prompt, timeout=timeout, allowed_tools=allowed_tools)
    elif backend == "sdk":
        return _call_sdk(prompt, max_tokens=max_tokens, model=model)
    return f"[unknown backend: {backend}]"


def is_available() -> bool:
    """True if any LLM backend is usable."""
    try:
        _detect_backend()
        return True
    except RuntimeError:
        return False


def backend_name() -> str:
    """Return the active backend name for logging."""
    try:
        return _detect_backend()
    except RuntimeError:
        return "none"


if __name__ == "__main__":
    # Smoke test
    print(f"Backend: {backend_name()}")
    print(f"Available: {is_available()}")
    if is_available():
        response = call("Reply with exactly: LLM_OK")
        print(f"Test response: {response}")
