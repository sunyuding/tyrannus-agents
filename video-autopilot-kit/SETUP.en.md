# SETUP — Answer these to make the system *yours*

> **This repo isn't a hand-me-down config — it's a framework + questionnaire.**
> It distills a battle-tested YouTube / short-form automation system into templates.
> You answer the questions below and it generates **your own** voice / brand / strategy
> / community files. The code is generic; **all personalization comes from your answers —
> none of the original author's private data is included.**

*(中文版見 [SETUP.md](SETUP.md))*

## 🚀 Three steps

1. Copy `templates/*.template.md` → `profiles/*.md` (drop the `.template`)
2. Answer each section below — or **hand the repo to Claude / ChatGPT** and say:
   > "Ask me the questions in `SETUP.md` section by section and generate my `profiles/` from my answers."
3. `cp config.example.py config.py` → fill in your own paths

When done you have **your own** automation system; run the `src/` tools for editing / publishing.

---

## 1️⃣ Brand / Channel → generates `profiles/brand.md`
- Channel name + handle? Website / main link?
- **How do you sign off?** (voice-over / title card / on-camera?) — this becomes your outro signature
- ⚠️ **Do you film talking-head / show your face?** (Important — if not, intros/outros must use b-roll + cards, never "selfie cue")
- Brand colors / preferred fonts? Subscribe-CTA placement?

## 2️⃣ Niche / Content type → routes the pipeline
- What do you make? (tutorial / vlog / unboxing / review / gaming …)
- Main platform? (YT long-form / Shorts / Reels / TikTok)
- Language?

## 3️⃣ Your Voice → generates `profiles/voice.md`
- **Paste 5–10 scripts/posts you wrote yourself** — the system learns *your* voice, not someone else's
- Your typical opener? Catchphrases? Sign-off?
- **Hard no's?** (anti-patterns — e.g. no profanity, no fake hype, no certain memes)

## 4️⃣ Production → generates `config.py`
- CapCut Desktop (Pro?) or pure ffmpeg?
- Where are your **fonts** / **BGM** / **b-roll** stored? Project / export paths?
- (Filled into `config.py` — the example contains **no account names**)

## 5️⃣ Algorithm context → fills `profiles/algorithm.md`
- Your current numbers? (subs / avg views / CTR / average view duration)
- Main traffic source? (Browse / Suggested / Search / External …)
- Biggest pain point? (reach / retention / CTR …)
- (The framework gives you **which metrics to watch and how to fix them**; you fill in **your** numbers)

## 6️⃣ Community / external traffic → fills `profiles/community.md`
- Which communities do you have, and how big? (Discord / Line / FB / IG …)
- Which channels can you mobilize at launch?
- (Gives you the mobilization-SOP **structure**; your communities, your numbers)

---

## Why a questionnaire instead of a ready-made config?

The most valuable part of a creator system is its **structure and methodology**, not one
person's private numbers. Copying someone else's voice / strategy / community data won't
help you — it may mislead you. So this repo gives you the **skeleton**; you fill it with
your own flesh. That's what makes it truly **yours**.
