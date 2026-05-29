name: one-post
description: Set up social-mcp to post to Facebook/Instagram from Claude Code or Codex CLI via Chrome CDP. No API tokens needed.
trigger: >
  User says "setup social-mcp", "install social mcp", "set up facebook posting",
  "configure social posting", "one-post setup", "设置 social-mcp", "安装 social mcp",
  "設定 social-mcp", "安裝 social mcp", or any variation asking to set up
  social media posting through Claude Code or Codex CLI.
---

# one-post

> Post to Facebook and Instagram from Claude Code or Codex CLI. No API tokens, no developer accounts.
>
> 从 Claude Code / Codex CLI 直接发 Facebook / Instagram。无需 API token，无需开发者帐号。
>
> 從 Claude Code / Codex CLI 直接發 Facebook / Instagram。無需 API token，無需開發者帳號。

## When to use

- User says "setup social-mcp" / "install social mcp" / "set up facebook posting"
- User says "设置 social-mcp" / "安装 social mcp" / "设置脸书发文"
- User says "設定 social-mcp" / "安裝 social mcp" / "設定臉書發文"
- User wants to post to Facebook or Instagram from Claude Code or Codex CLI
- User shares this skill or mentions one-post / social-mcp

## Prerequisites

Before running, verify these are installed:

```bash
uv --version        # Python package manager (required)
ls "/Applications/Google Chrome.app"  # Chrome browser, macOS only (required)
claude --version     # Claude Code CLI (one of these two)
codex --version      # Codex CLI         (one of these two)
```

If any is missing, tell the user how to install it and stop:
- uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Chrome: Download from https://www.google.com/chrome
- Claude Code: `npm install -g @anthropic-ai/claude-code`
- Codex CLI: `npm install -g @openai/codex`

At least one of Claude Code or Codex CLI must be installed.

## Setup Steps

Execute these steps in order. Report result after each step.

### Step 1: Clone and install | 克隆并安装 | 克隆並安裝

```bash
git clone https://github.com/whypuss/social-mcp.git ~/Projects/social-mcp
cd ~/Projects/social-mcp
uv sync
uv run playwright install chromium
```

If already cloned, skip the clone and just run `uv sync`.

### Step 2: Patch known bugs | 修复已知 Bug | 修復已知 Bug

Apply two fixes to `~/Projects/social-mcp/social_mcp/mcp_server.py`:

**Bug 1 — Missing import (缺少导入):**

Add `from playwright.async_api import async_playwright` at module level (after the `from mcp.server.fastmcp import FastMCP` line). Remove the duplicate import inside `open_login_window()` if it exists.

**Bug 2 — Hardcoded Chinese selectors (硬编码中文选择器):**

The `post_facebook()` function uses Chinese-only aria-labels (`建立帖子`, `下一頁`, `發佈`) that break on non-Chinese Facebook UIs. Replace the entire `post_facebook` function with the multi-locale version from `references/patched_post_facebook.py`.

The patched function:
1. Tries aria-labels in multiple locales: `["建立帖子", "Create a post", "Create post"]`
2. Falls back to finding "What's on your mind" / "在想些什麼" span text via JS
3. Uses `execCommand('insertText')` instead of `keyboard.type` (more reliable with contenteditable)
4. Tries `["Next", "下一頁", "Continue", "繼續"]` for the Next button
5. Tries `["Post", "發佈", "Publish"]` for the Post button with JS fallback
6. Detects login wall in both English and Chinese

### Step 3: Register MCP | 注册 MCP | 註冊 MCP

Pick the client(s) you use:

**Claude Code (CLI):**
```bash
claude mcp add social -- uv run --project ~/Projects/social-mcp social-mcp
claude mcp list   # Should show "social"
```

**Codex CLI / Codex Desktop** (they share the same config):
```bash
codex mcp add social -- uv run --project ~/Projects/social-mcp social-mcp
codex mcp list    # Should show "social"
```

**Claude Desktop:**

Open Settings > Developer > Edit Config, then add to `claude_desktop_config.json`:

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

Replace `/Users/YOU` with your actual home directory path. Save and restart Claude Desktop.

### Step 4: First-time login (requires user action) | 首次登录 | 首次登入

Tell the user:

> **EN:** I need you to log in to Facebook once. A Chrome window will open — log in to your Facebook account, then **close the browser window**. This saves your session for future automated posting.
>
> **简体:** 需要你登录一次 Facebook。Chrome 窗口会打开，请登录你的 Facebook 帐号，然后**关闭浏览器窗口**。这会保存你的会话供后续自动发文使用。
>
> **繁體:** 需要你登入一次 Facebook。Chrome 視窗會開啟，請登入你的 Facebook 帳號，然後**關閉瀏覽器視窗**。這會保存你的工作階段供後續自動發文使用。

Then run:

```bash
mkdir -p ~/Library/Application\ Support/Google/Chrome/SocialMCP

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SocialMCP" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check
```

**Wait for the user to confirm they've logged in and closed the browser before continuing.**

### Step 5: Launch Chrome with CDP | 启动 Chrome CDP | 啟動 Chrome CDP

```bash
# Clear stale locks | 清除残留锁 | 清除殘留鎖
for lock in SingletonLock SingletonSocket SingletonCookie; do
  rm -f "$HOME/Library/Application Support/Google/Chrome/SocialMCP/$lock"
done

# Launch with CDP | 以 CDP 模式启动 | 以 CDP 模式啟動
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9333 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/SocialMCP" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check \
  --window-size=1280,720 \
  "https://www.facebook.com" &

# Wait for CDP to be ready (up to 10s)
for i in $(seq 1 10); do
  curl -s --max-time 2 http://localhost:9333/json/version > /dev/null 2>&1 && echo "CDP ready" && break
  sleep 1
done
```

### Step 6: Restart your client | 重启客户端 | 重啟客戶端

Tell the user to restart their client so the MCP server reconnects with the patched code:
- **Claude Code:** `/exit` then `claude`
- **Codex CLI:** exit then `codex`
- **Claude Desktop:** Quit and reopen the app
- **Codex Desktop:** Quit and reopen the app

## After Setup | 设置完成后 | 設定完成後

The user can now say:
- `post to Facebook: <message>`
- `发 Facebook: <消息>`
- `發 Facebook: <訊息>`

## Troubleshooting | 故障排除 | 疑難排解

| Symptom | Fix |
|---|---|
| `async_playwright is not defined` | Step 2 Bug 1 not applied. Add the import. |
| `Chromium not running` | Run Step 5 to launch Chrome with CDP. |
| `Could not open composer` | Step 2 Bug 2 not applied. Replace `post_facebook` function. |
| `Timeout 15000ms exceeded` | Multiple Chrome instances. Run: `pkill -f SocialMCP`, clear locks, relaunch. |
| `No Facebook page found` | Chrome is open but not on facebook.com. Navigate there manually. |
| `Not logged in` | Session expired. Redo Step 4. |
| MCP tool not found | Re-run Step 3 and restart your CLI. |

## Do NOT | 禁止事项 | 禁止事項

- Store or transmit user's Facebook credentials
- Auto-login or change account settings
- Post without user confirmation (unless explicitly authorized in current session)
- Run on non-macOS (Chrome path is macOS-specific)
