# one-post

> Post to Facebook & Instagram from any MCP client. No API tokens, no developer accounts.
>
> 从任何 MCP 客户端直接发 Facebook / Instagram。无需 API token，无需开发者帐号。
>
> 從任何 MCP 客戶端直接發 Facebook / Instagram。無需 API token，無需開發者帳號。

### Supported Clients | 支持的客户端

| Client | Type | MCP Config |
|---|---|---|
| **Claude Code** | CLI | `claude mcp add` |
| **Codex CLI** | CLI | `codex mcp add` |
| **Claude Desktop** | Desktop App | `claude_desktop_config.json` |
| **Codex Desktop** | Desktop App | `~/.codex/config.toml` (shared with CLI) |

## How it works

```
Any MCP Client  ──MCP stdio──>  social-mcp (Python FastMCP)
                                      │
                                Playwright CDP
                                      │
                                      v
                             Chrome (port 9333)
                             SocialMCP profile
                                      │
                                      v
                              facebook.com
                            (logged-in session)
```

- **No API tokens** — uses Chrome DevTools Protocol to control a real browser
- **Session persists** in `~/Library/Application Support/Google/Chrome/SocialMCP/`
- **macOS only** (Chrome path is macOS-specific)

## Quick Start

### Option 1: Claude Code Skill (Recommended)

Install as a Claude Code skill, then say "setup social-mcp":

```bash
# Clone this repo
git clone https://github.com/sunyuding/one-post.git ~/Projects/one-post

# Add as Claude Code skill
claude skill add ~/Projects/one-post/one-post

# Start Claude Code and say:
claude
# > setup social-mcp
```

### Option 2: One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/sunyuding/one-post/main/one-post/install.sh | bash
```

### Option 3: Follow the guide manually

See [social-media-setup-guide.md](social-media-setup-guide.md) for step-by-step instructions.

## Usage | 使用方法

After setup, say any of these in your MCP client:

| Language | Command |
|---|---|
| English | `post to Facebook: Hello world!` |
| 简体中文 | `发 Facebook: 你好世界！` |
| 繁體中文 | `發 Facebook: 你好世界！` |

## Prerequisites | 先决条件 | 先決條件

| Tool | Install |
|---|---|
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Google Chrome](https://www.google.com/chrome) | Download from website |
| An MCP client (at least one): | |
| - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `npm install -g @anthropic-ai/claude-code` |
| - [Codex CLI](https://developers.openai.com/codex/cli) | `npm install -g @openai/codex` |
| - [Claude Desktop](https://claude.ai/download) | Download from website |
| - [Codex Desktop](https://developers.openai.com/codex) | Download from website |

## Setup Steps | 设置步骤 | 設定步驟

1. **Clone & install** — Clone social-mcp, install dependencies
2. **Patch bugs** — Fix missing import + add multi-locale selectors
3. **Register MCP** — Register with your client (Claude Code / Codex / Desktop)
4. **Login once** — Open Chrome, log in to Facebook, close browser
5. **Launch CDP** — Start Chrome with remote debugging on port 9333
6. **Restart your client** — Reconnect with patched MCP server

See [SKILL.md](one-post/SKILL.md) for detailed instructions.

## Troubleshooting | 故障排除 | 疑難排解

| Symptom | Fix |
|---|---|
| `async_playwright is not defined` | Add `from playwright.async_api import async_playwright` at module level |
| `Chromium not running` | Launch Chrome with CDP (Step 5) |
| `Could not open composer` | Apply multi-locale patch (Step 2, Bug 2) |
| `Timeout 15000ms exceeded` | `pkill -f SocialMCP`, clear locks, relaunch |
| `No Facebook page found` | Navigate Chrome to facebook.com |
| `Not logged in` | Redo Step 4 (login) |
| MCP tool not found | Re-register: `claude mcp add social -- ...` or `codex mcp add social -- ...` or edit Desktop config |

## Project Structure

```
one-post/
├── README.md                          # This file
├── social-media-setup-guide.md        # Full setup guide
└── one-post/                          # Claude Code skill
    ├── SKILL.md                       # Skill definition
    ├── install.sh                     # One-click installer
    └── references/
        └── patched_post_facebook.py   # Multi-locale post function
```

## Credits

- Built on [social-mcp](https://github.com/whypuss/social-mcp) by whypuss
- Multi-locale patches and skill packaging by [sunyuding](https://github.com/sunyuding)

## License

MIT
