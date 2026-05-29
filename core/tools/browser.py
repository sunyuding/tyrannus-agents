"""
Browser automation tool via Playwright CDP.

Merged from one-post (https://github.com/sunyuding/one-post) which extends
social-mcp (https://github.com/whypuss/social-mcp).

Supports multi-locale Facebook UI (English, Simplified Chinese, Traditional Chinese).
Connects to Chrome on a configurable CDP port with the SocialMCP profile.
"""

import asyncio
import subprocess

from playwright.async_api import async_playwright

from core.config import settings


def is_chromium_running() -> bool:
    """Check if Chrome is running with CDP on the configured port."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "2",
             f"http://localhost:{settings.CHROME_CDP_PORT}/json/version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


async def _get_facebook_page(browser):
    """Find an open, logged-in Facebook tab."""
    ctx = browser.contexts[0]
    for pg in ctx.pages:
        if "facebook.com" in pg.url and "/login" not in pg.url:
            return pg
    return None


async def _detect_login_wall(page) -> bool:
    """Return True if the page shows a login wall (multi-locale)."""
    body = await page.inner_text("body")
    prefix = body[:400]
    return any(kw in prefix for kw in ("登入", "Log in", "Log In"))


async def _click_composer(page) -> bool:
    """Click the Facebook post composer (multi-locale)."""
    # Try aria-label first
    for label in ["建立帖子", "Create a post", "Create post"]:
        try:
            await page.locator(f'[aria-label="{label}"]').first.click(timeout=3000)
            return True
        except Exception:
            continue

    # Fallback: find "What's on your mind" span via JS
    try:
        await page.evaluate("""
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
        return True
    except Exception:
        return False


async def _type_in_composer(page, message: str) -> bool:
    """Focus the contenteditable editor and type via execCommand."""
    for _ in range(5):
        result = await page.evaluate("""
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
        if "focused" in result:
            await page.evaluate(
                "(msg) => document.execCommand('insertText', false, msg)",
                message,
            )
            return True
        await asyncio.sleep(1)
    return False


async def _click_next_if_needed(page):
    """Click Next/Continue if the account requires it."""
    for label in ["Next", "下一頁", "Continue", "繼續"]:
        try:
            await page.locator(f'[aria-label="{label}"]').first.click(timeout=3000)
            await asyncio.sleep(2)
            return
        except Exception:
            continue


async def _click_post_button(page) -> bool:
    """Click the Post/Publish button (multi-locale + JS fallback)."""
    for label in ["Post", "發佈", "Publish"]:
        try:
            await page.locator(f'[aria-label="{label}"]').first.click(timeout=5000)
            return True
        except Exception:
            continue

    # JS fallback
    await page.evaluate("""
    () => {
        const btns = document.querySelectorAll('[role="button"], button');
        for (const b of btns) {
            const t = (b.innerText || '').trim();
            if (['Post', '發佈', 'Publish'].includes(t)) { b.click(); return; }
        }
    }
    """)
    return True


async def _wait_for_dialog_close(page, timeout_seconds: int = 15) -> bool:
    """Wait for the composer dialog to close (= post succeeded)."""
    for _ in range(timeout_seconds):
        await asyncio.sleep(1)
        still_open = await page.evaluate("""
        () => {
            const ds = document.querySelectorAll('[role="dialog"]');
            for (const d of ds) {
                if (d.innerText.includes('Create') || d.innerText.includes('建立')) return true;
            }
            return false;
        }
        """)
        if not still_open:
            return True
    return False


# ── Public API ──────────────────────────────────────────────


async def post_facebook(message: str) -> str:
    """
    Post a text message to the user's Facebook wall via Chrome CDP.

    Requires Chrome running on the configured CDP port with a logged-in
    SocialMCP profile.

    Multi-locale: supports English, Simplified Chinese, Traditional Chinese UIs.
    """
    if not is_chromium_running():
        return "Chrome not running. Launch Chrome with CDP first."

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            f"http://localhost:{settings.CHROME_CDP_PORT}"
        )

        fb_page = await _get_facebook_page(browser)
        if not fb_page:
            await browser.close()
            return "No Facebook page found. Open facebook.com in Chrome first."

        await fb_page.goto("https://www.facebook.com", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        if await _detect_login_wall(fb_page):
            await browser.close()
            return "Not logged in. Log in to Facebook first."

        if not await _click_composer(fb_page):
            await browser.close()
            return "Could not open composer."

        await asyncio.sleep(3)

        if not await _type_in_composer(fb_page, message):
            await browser.close()
            return "Could not find text editor in composer dialog."

        await asyncio.sleep(2)
        await _click_next_if_needed(fb_page)
        await _click_post_button(fb_page)

        success = await _wait_for_dialog_close(fb_page)
        await browser.close()

        if success:
            return "Post published successfully!"
        return "Post may have been published. Check your Facebook wall."
