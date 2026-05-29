# Social MCP Setup Guide

> Give this file to a fresh Claude Code / Codex CLI session and say **"follow this guide to set up social-mcp"**.
> It will execute every step. After setup you can say "post to Facebook: ..." to publish.
> Also works with Claude Desktop and Codex Desktop.

---

## Prerequisites

Run these checks first. Install anything missing before proceeding.

```bash
# Check uv
uv --version || echo "MISSING: install with: curl -LsSf https://astral.sh/uv/install.sh | sh"

# Check Chrome
ls "/Applications/Google Chrome.app" || echo "MISSING: install Google Chrome"

# Check Claude Code or Codex CLI (at least one needed)
claude --version || codex --version || echo "MISSING: install Claude Code or Codex CLI"
```

---

## Step 1: Clone and install

```bash
git clone https://github.com/whypuss/social-mcp.git ~/Projects/social-mcp
cd ~/Projects/social-mcp
uv sync
uv run playwright install chromium
```

## Step 2: Fix known bugs

The upstream code has two bugs. Apply both fixes:

### Bug 1: Missing `async_playwright` import

`social_mcp/mcp_server.py` imports `async_playwright` only inside `open_login_window()` but uses it in every function.

**Fix:** Add a module-level import and remove the redundant local one.

In `social_mcp/mcp_server.py`, change:

```python
from mcp.server.fastmcp import FastMCP
```

to:

```python
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright
```

And inside `open_login_window()`, delete the line:

```python
    from playwright.async_api import async_playwright
```

### Bug 2: Hardcoded Chinese aria-labels

The `post_facebook()` function uses Chinese-only selectors (`建立帖子`, `下一頁`, `發佈`) which break on English or other locale Facebook UIs.

**Fix:** Replace the entire `post_facebook` function body (after the `is_chromium_running` check) with this multi-locale version:

```python
@mcp.tool()
async def post_facebook(message: str):
    """
    Post a text message to your personal Facebook wall.
    Requires: Chrome running on port 9333 with a logged-in SocialMCP profile.
    """
    if not is_chromium_running():
        return "Chrome not running. Run open_login_window() first."

    await ensure_chromium()
    await asyncio.sleep(2)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9333")
        ctx = browser.contexts[0]
        fb_page = None
        for pg in ctx.pages:
            if "facebook.com" in pg.url and "/login" not in pg.url:
                fb_page = pg
                break

        if not fb_page:
            await browser.close()
            return "No Facebook page found. Open facebook.com in Chrome first."

        await fb_page.goto("https://www.facebook.com", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Detect login wall
        body = await fb_page.inner_text("body")
        if ("登入" in body[:400] or "Log in" in body[:400] or "Log In" in body[:400]):
            await browser.close()
            return "Not logged in. Run open_login_window() first."

        # Click composer (multi-locale)
        composer_clicked = False
        for label in ["建立帖子", "Create a post", "Create post"]:
            try:
                await fb_page.locator(f'[aria-label="{label}"]').first.click(timeout=3000)
                composer_clicked = True
                break
            except Exception:
                continue

        if not composer_clicked:
            try:
                await fb_page.evaluate("""
                () => {
                    const spans = document.querySelectorAll('span');
                    for (const s of spans) {
                        const t = (s.innerText || '').trim();
                        if (t.includes("What's on your mind") || t.includes('在想些什麼')) {
                            let el = s;
                            for (let i = 0; i < 5; i++) {
                                el = el.parentElement;
                                if (!el) break;
                                if (el.getAttribute('role') === 'button') { el.click(); return; }
                            }
                            s.click(); return;
                        }
                    }
                }
                """)
            except Exception as e:
                await browser.close()
                return f"Could not open composer: {e}"

        await asyncio.sleep(3)

        # Find contenteditable and type via execCommand
        typed = False
        for _ in range(5):
            r = await fb_page.evaluate("""
            () => {
                const dialogs = document.querySelectorAll('[role="dialog"]');
                for (const d of dialogs) {
                    const text = d.innerText.slice(0, 200);
                    if (text.includes('Create') || text.includes('建立')) {
                        const ce = d.querySelector('[contenteditable="true"]');
                        if (ce) { ce.focus(); return 'focused'; }
                    }
                }
                return 'no_editor';
            }
            """)
            if 'focused' in r:
                await fb_page.evaluate("(msg) => document.execCommand('insertText', false, msg)", message)
                typed = True
                break
            await asyncio.sleep(1)

        if not typed:
            await browser.close()
            return "Could not find text editor in composer dialog"

        await asyncio.sleep(2)

        # Click Next (optional step on some accounts)
        for label in ["Next", "下一頁", "Continue", "繼續"]:
            try:
                await fb_page.locator(f'[aria-label="{label}"]').first.click(timeout=3000)
                await asyncio.sleep(2)
                break
            except Exception:
                continue

        # Click Post/Publish (multi-locale + JS fallback)
        post_clicked = False
        for label in ["Post", "發佈", "Publish"]:
            try:
                await fb_page.locator(f'[aria-label="{label}"]').first.click(timeout=5000)
                post_clicked = True
                break
            except Exception:
                continue

        if not post_clicked:
            await fb_page.evaluate("""
            () => {
                const btns = document.querySelectorAll('[role="button"], button');
                for (const b of btns) {
                    const t = (b.innerText || '').trim();
                    if (['Post', '發佈', 'Publish'].includes(t)) { b.click(); return; }
                }
            }
            """)

        # Wait for dialog to close (= post succeeded)
        for i in range(15):
            await asyncio.sleep(1)
            still = await fb_page.evaluate("""
            () => {
                const ds = document.querySelectorAll('[role="dialog"]');
                for (const d of ds) {
                    if (d.innerText.includes('Create') || d.innerText.includes('建立')) return true;
                }
                return false;
            }
            """)
            if not still:
                await browser.close()
                return "Post published successfully!"

        await browser.close()
        return "Post may have been published. Check your Facebook wall."
```

## Step 3: Register MCP

Pick the client(s) you use:

**Claude Code (CLI):**
```bash
claude mcp add social -- uv run --project ~/Projects/social-mcp social-mcp
claude mcp list   # Should show "social"
```

**Codex CLI / Codex Desktop** (shared config):
```bash
codex mcp add social -- uv run --project ~/Projects/social-mcp social-mcp
codex mcp list    # Should show "social"
```

**Claude Desktop:**

Open Settings > Developer > Edit Config, add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "social": {
      "command": "uv",
      "args": ["run", "--project", "/Users/YOU/Projects/social-mcp", "social-mcp"]
    }
  }
}
```
Replace `/Users/YOU` with your home directory. Save and restart Claude Desktop.

## Step 4: First-time Facebook login (manual, one-time)

This creates a dedicated Chrome profile. You only do this once.

```bash
mkdir -p ~/Library/Application\ Support/Google/Chrome/SocialMCP

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SocialMCP" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check
```

**User action:** Log in to Facebook in the browser window, then close it.

## Step 5: Launch Chrome with CDP (before each posting session)

```bash
# Clear stale locks
for lock in SingletonLock SingletonSocket SingletonCookie; do
  rm -f "$HOME/Library/Application Support/Google/Chrome/SocialMCP/$lock"
done

# Launch with CDP
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9333 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SocialMCP" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check \
  --window-size=1280,720 \
  "https://www.facebook.com" &

# Verify CDP is ready (wait up to 10s)
for i in $(seq 1 10); do
  curl -s --max-time 2 http://localhost:9333/json/version > /dev/null 2>&1 && echo "CDP ready" && break
  sleep 1
done
```

## Step 6: Restart your client

- **Claude Code:** `/exit` then `claude`
- **Codex CLI:** exit then `codex`
- **Claude Desktop:** Quit and reopen the app
- **Codex Desktop:** Quit and reopen the app

The `social` MCP tools (`post_facebook`, `open_login_window`, `read_messenger`, `read_notifications`) will now be available.

---

## Usage

Say any of:
- `post to Facebook: Hello world!`
- `用 social-mcp 發 FB`
- `post_facebook("your message here")`

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `async_playwright is not defined` | Step 2 Bug 1 not applied. Add the import. |
| `Chromium not running` | Run Step 5 to launch Chrome with CDP. |
| `Could not open composer` | Step 2 Bug 2 not applied. Replace post_facebook function. |
| `Timeout 15000ms exceeded` | Multiple Chrome instances. Run: `pkill -f SocialMCP`, clear locks, relaunch one. |
| `No Facebook page found` | Chrome is open but not on facebook.com. Navigate there manually. |
| `Not logged in` | Session expired. Redo Step 4. |
| MCP tool not found | Re-register MCP (Step 3) and restart your client. |

---

## Architecture

```
MCP Client   ──MCP stdio──►  social-mcp (Python FastMCP)
                                  │
                            Playwright CDP
                                  │
                                  ▼
                         Chrome (port 9333)
                         SocialMCP profile
                                  │
                                  ▼
                          facebook.com
                        (logged-in session)
```

- **No API tokens.** Uses Chrome DevTools Protocol to control a real browser.
- **Session persists** in `~/Library/Application Support/Google/Chrome/SocialMCP/`.
- **macOS only** (Chrome path hardcoded for macOS).
