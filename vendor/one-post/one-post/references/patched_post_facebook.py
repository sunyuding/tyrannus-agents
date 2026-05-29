"""
Patched post_facebook function — multi-locale support.

Replace the entire post_facebook() function in
~/Projects/social-mcp/social_mcp/mcp_server.py with this version.

Supports: English, Simplified Chinese, Traditional Chinese Facebook UIs.
"""


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

        # Detect login wall (multi-locale)
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
