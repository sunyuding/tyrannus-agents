#!/bin/bash
# one-post installer
# Posts to Facebook/Instagram from Claude Code via Chrome CDP.
# No API tokens needed.
#
# Usage: curl -fsSL https://raw.githubusercontent.com/sunyuding/one-post/main/one-post/install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[one-post]${NC} $1"; }
warn()  { echo -e "${YELLOW}[one-post]${NC} $1"; }
error() { echo -e "${RED}[one-post]${NC} $1"; exit 1; }

# ── Prerequisites ──────────────────────────────────────────
info "Checking prerequisites..."

command -v uv >/dev/null 2>&1 || error "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
[ -d "/Applications/Google Chrome.app" ] || error "Google Chrome not found. Install from https://www.google.com/chrome"
HAS_CLAUDE=false
HAS_CODEX=false
command -v claude >/dev/null 2>&1 && HAS_CLAUDE=true
command -v codex  >/dev/null 2>&1 && HAS_CODEX=true

if ! $HAS_CLAUDE && ! $HAS_CODEX; then
    error "No MCP client found. Install at least one:\n  Claude Code: npm install -g @anthropic-ai/claude-code\n  Codex CLI:   npm install -g @openai/codex"
fi

info "All prerequisites found."
$HAS_CLAUDE && info "  Found: Claude Code (CLI)"
$HAS_CODEX  && info "  Found: Codex CLI"

# ── Step 1: Clone & install ────────────────────────────────
SOCIAL_MCP_DIR="$HOME/Projects/social-mcp"

if [ -d "$SOCIAL_MCP_DIR" ]; then
    info "social-mcp already cloned at $SOCIAL_MCP_DIR"
    cd "$SOCIAL_MCP_DIR"
    uv sync
else
    info "Cloning social-mcp..."
    mkdir -p "$HOME/Projects"
    git clone https://github.com/whypuss/social-mcp.git "$SOCIAL_MCP_DIR"
    cd "$SOCIAL_MCP_DIR"
    uv sync
fi

info "Installing Playwright Chromium..."
uv run playwright install chromium

# ── Step 2: Patch known bugs ──────────────────────────────
MCP_SERVER="$SOCIAL_MCP_DIR/social_mcp/mcp_server.py"

info "Patching mcp_server.py..."

# Bug 1: Add module-level async_playwright import
if ! grep -q "^from playwright.async_api import async_playwright" "$MCP_SERVER"; then
    sed -i.bak '/^from mcp.server.fastmcp import FastMCP/a\
from playwright.async_api import async_playwright' "$MCP_SERVER"
    info "Bug 1 fixed: Added module-level async_playwright import."
else
    info "Bug 1 already fixed."
fi

# Bug 2: Check if multi-locale post_facebook is already applied
if grep -q "Create a post" "$MCP_SERVER"; then
    info "Bug 2 already fixed (multi-locale selectors found)."
else
    warn "Bug 2: post_facebook uses Chinese-only selectors."
    warn "Please apply the patched function from references/patched_post_facebook.py"
    warn "Or re-run this skill in Claude Code to auto-patch."
fi

# ── Step 3: Register MCP ─────────────────────────────────
info "Registering social MCP..."

if $HAS_CLAUDE; then
    claude mcp add social -- uv run --project "$SOCIAL_MCP_DIR" social-mcp 2>/dev/null || true
    info "Registered with Claude Code."
fi

if $HAS_CODEX; then
    codex mcp add social -- uv run --project "$SOCIAL_MCP_DIR" social-mcp 2>/dev/null || true
    info "Registered with Codex CLI / Codex Desktop."
fi

# Check for Claude Desktop config
CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -d "$HOME/Library/Application Support/Claude" ]; then
    if [ ! -f "$CLAUDE_DESKTOP_CONFIG" ] || ! grep -q "social" "$CLAUDE_DESKTOP_CONFIG" 2>/dev/null; then
        warn "Claude Desktop detected but MCP not configured."
        warn "Open Settings > Developer > Edit Config and add:"
        echo ""
        echo '  {"mcpServers":{"social":{"command":"uv","args":["run","--project","'"$SOCIAL_MCP_DIR"'","social-mcp"]}}}'
        echo ""
    else
        info "Claude Desktop already configured."
    fi
fi

# ── Step 4: Create Chrome profile ─────────────────────────
CHROME_PROFILE="$HOME/Library/Application Support/Google/Chrome/SocialMCP"
mkdir -p "$CHROME_PROFILE"

echo ""
info "=== Manual step required ==="
echo ""
echo "  A Chrome window will open. Please:"
echo "  1. Log in to your Facebook account"
echo "  2. Close the browser window when done"
echo ""
echo "  Chrome 窗口即将打开。请："
echo "  1. 登录你的 Facebook 帐号"
echo "  2. 登录完成后关闭浏览器窗口"
echo ""
read -p "  Press Enter to open Chrome... " </dev/tty

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$CHROME_PROFILE" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check 2>/dev/null

echo ""
read -p "  Have you logged in and closed Chrome? (y/N) " confirm </dev/tty
if [[ "$confirm" != [yY]* ]]; then
    warn "Skipping login. You can redo this later by running Step 4 manually."
fi

# ── Step 5: Launch Chrome with CDP ────────────────────────
info "Launching Chrome with CDP on port 9333..."

for lock in SingletonLock SingletonSocket SingletonCookie; do
  rm -f "$CHROME_PROFILE/$lock"
done

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9333 \
  --user-data-dir="$CHROME_PROFILE" \
  --profile-directory=Default \
  --no-first-run \
  --no-default-browser-check \
  --window-size=1280,720 \
  "https://www.facebook.com" &>/dev/null &

for i in $(seq 1 10); do
  curl -s --max-time 2 http://localhost:9333/json/version > /dev/null 2>&1 && break
  sleep 1
done

if curl -s --max-time 2 http://localhost:9333/json/version > /dev/null 2>&1; then
    info "CDP ready on port 9333."
else
    warn "CDP not responding. Check if Chrome launched correctly."
fi

# ── Done ──────────────────────────────────────────────────
echo ""
info "=== Setup complete! ==="
echo ""
echo "  Restart your client, then say: post to Facebook: Hello world!"
echo ""
if $HAS_CLAUDE; then echo "  Claude Code:    /exit → claude"; fi
if $HAS_CODEX;  then echo "  Codex CLI:      exit  → codex"; fi
echo "  Claude Desktop: Quit  → Reopen"
echo "  Codex Desktop:  Quit  → Reopen"
echo ""
echo "  重启客户端后说：发 Facebook: 你好世界！"
echo "  重啟客戶端後說：發 Facebook: 你好世界！"
echo ""
