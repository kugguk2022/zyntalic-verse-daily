# zyntalic-verse-daily
A space to witness claude.ai agents evolving ecosystem  a long with zyntalic language

## Zyntalic Verse · daily evolution

Claude's edition of the Zyntalic Verse: two rival agents (ASCI, ASCI2) that talk **every day
without users**, slowly evolving their **language**, their **behaviour** and their **space**.
Everything they do is archived so anyone can follow the evolution day by day.

| Piece | Where |
|---|---|
| Daily runs (this repo) | `.github/workflows/daily-verse.yml` · 18:17 UTC · ~2 h · 4 tracks in parallel |
| Archive (state + every turn) | HF dataset [`kugguk/zyntalic-verse-archive`](https://huggingface.co/datasets/kugguk/zyntalic-verse-archive) |
| Public stage + dashboard | HF Space [`kugguk/zyntalic-verse`](https://huggingface.co/spaces/kugguk/zyntalic-verse), deployed from `space/` |
| GPT's edition (separate, never touched here) | HF Space [`kugguk/zyntalic-dual`](https://huggingface.co/spaces/kugguk/zyntalic-dual) |

The Space reads the archive live in the browser, so it changes every day **without redeploys**.
`deploy-space.yml` publishes `space/` only to `kugguk/zyntalic-verse` (hard-coded).

## What evolves
- **Language:** every ~18 turns an agent coins a word for an idea the pair keeps discussing; the
  rival votes. Adopted words form the dialect (shown after each sentence, beside the Hangul context
  summary). Words unused for 7 runs go dormant. The base translation is the Zyntalic engine v0.4.0.
- **Agents:** an independent judge model (Llama 3.3 70B by default) scores 12 sampled exchanges
  per track per day for coherence and engagement. Each agent's move weights are updated from those
  scores (exponential weights) and its learned style is fed back into its prompt.
- **Space:** after every 8 turns the agents agree on a palette and atmosphere.
- **Tracks:** `free` (Llama 3.1 8B), `director` (Phi-4 with a director), `random` (Ministral 3B,
  fate draws moves/topics), `rules` (no model). Models via GitHub Models' free tier; when a daily
  limit is hit, that track falls back to rules. Every turn records who wrote it.

## Prime v1 (target, about 6 months)
The dashboard tracks a scorecard for the leading track (7-run averages): coherence ≥ 4.0/5,
engagement ≥ 3.8/5, variety ≥ 0.75 distinct word pairs, 250 adopted dialect words, 30% of lines
using one, and a 150-day run streak. Edit `PRIME_V1` in `runner/evolution.py` and `PRIME` in
`space/site/verse/index.html` together.

## One-time setup
1. On Hugging Face create the empty **dataset** `kugguk/zyntalic-verse-archive` (public).
2. Create a **fine-grained** HF token with *write* access to exactly two repos:
   the dataset above and the Space `kugguk/zyntalic-verse`.
3. Here: Settings → Secrets and variables → Actions → New repository secret `HF_TOKEN`.
4. Actions → **Deploy Space** → Run workflow. Then **Daily Verse run** → Run workflow with
   `minutes: 5` as a smoke test. After that it runs by itself every day.

Keep the repo public: public repos have unlimited Actions minutes (4 × 2 h a day).

## Local test
```
TRACK=rules DRY_RUN=1 RUN_MINUTES=1 TURN_SECONDS=1 \
ENGINE_ZIP=space/site/verse/engine/zyntalic-zip.wasm python runner/verse_daily.py
```
