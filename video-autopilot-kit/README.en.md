# 🎬 video-autopilot-kit

> A **framework**, not a hand-me-down config. Reusable CapCut + ffmpeg video-automation
> code, plus a questionnaire that asks about **your** channel and turns the system into yours.
>
> ⚠️ **Ships with zero of the original author's private data** — voice, strategy, and
> community numbers are all **blank templates** you fill in yourself.

*(中文版見 [README.md](README.md))*

## Why this is different

Most "creator systems" either sell you **someone else's setup** (useless to you, sometimes
misleading) or stay too generic to have real methodology. This kit gives you the **skeleton**
(a battle-tested structure); `SETUP.md` **asks you questions** one section at a time, and
your answers fill it in — so it actually becomes **your** system.

## What's inside

| Folder | What |
|---|---|
| `src/capcut_helpers/` | CapCut Desktop JSON automation (draft I/O, 4-level mute, captions/effects, post-export ffmpeg, AI-subtitle fixes, b-roll ratio + sync audit) |
| `src/silent_vlog_maker/` | ffmpeg-only pipeline utilities (content audit, asset normalize, KenBurns, subtitle burn) |
| ⭐ `SETUP.md` | **Start here** — answer questions to make the system yours |
| `templates/` | Blank fill-in templates: voice / brand / algorithm / community / pipeline / context |
| `config.example.py` | Path config (env vars; **no account names** — auto-detects current user) |

## Quick start

1. Read **`SETUP.md`** → fill `templates/*.template.md` into `profiles/*.md`
   (or hand the repo to Claude / ChatGPT: *"ask me the SETUP.md questions and generate my profiles/"*)
2. `cp config.example.py config.py` → set your CapCut / asset / export paths
3. Check requirements below, then use the tools in `src/`

## Requirements

- Python 3.9+
- `ffmpeg` / `ffprobe` on PATH
- *(optional)* CapCut Desktop — for the `capcut_helpers` draft automation
- *(optional)* an AI assistant — to auto-generate your profiles from your answers

## Philosophy

The most valuable part of a creator system is the **structure and methodology**, not one
person's private numbers. So this repo gives you the bones; you fill them with your own flesh.

## License

MIT — keep the notice and use / modify / sell freely.

## Author

Hao0321 Studio — an open-source framework distilled from a real personal creator system.
