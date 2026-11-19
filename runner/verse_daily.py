"""Zyntalic Verse - daily evolution run.

Runs the two Verse agents (ASCI, ASCI2) for a fixed time window, translates
every line with the real zyntalic engine, and saves the evolving state to a
Hugging Face dataset so the Space can start from where the last run ended.

Who writes the English lines:
  * an open model through GitHub Models (free, uses the workflow's GITHUB_TOKEN),
  * or, when that is unavailable or the daily budget is used up, local rules
    from topics.py. Every turn records which one wrote it ("source").

Environment:
  HF_TOKEN            write token for the archive dataset (required to save)
  ARCHIVE_REPO        dataset id, default kugguk/zyntalic-verse-archive
  GITHUB_TOKEN        token for GitHub Models (optional)
  MODEL               default meta/Meta-Llama-3.1-8B-Instruct
  MODEL_URL           default https://models.github.ai/inference/chat/completions
  MAX_MODEL_CALLS     default 140 (GitHub Models free tier allows ~150/day)
  RUN_MINUTES         default 120
  TURN_SECONDS        default 55
  ENGINE_ZIP          path to a local zyntalic-zip.wasm (else downloaded from the Space)
  DRY_RUN=1           do not upload, write to ./out only
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import random
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from topics import BRAND, FORMS, LINEAGES, MOVES, NOUNS, PERSONAS, TOPICS  # noqa: E402
import evolution as evo  # noqa: E402

ARCHIVE_REPO = os.environ.get("ARCHIVE_REPO", "kugguk/zyntalic-verse-archive")
SPACE_BUNDLE = "https://huggingface.co/spaces/kugguk/zyntalic-verse/resolve/main/site/verse/engine/zyntalic-zip.wasm"
MODEL = os.environ.get("MODEL") or "meta/Meta-Llama-3.1-8B-Instruct"
MODEL_URL = os.environ.get("MODEL_URL", "https://models.github.ai/inference/chat/completions")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
MAX_CALLS = int(os.environ.get("MAX_MODEL_CALLS", "140"))
RUN_MIN = float(os.environ.get("RUN_MINUTES", "120"))
TURN_S = float(os.environ.get("TURN_SECONDS", "70"))
DRY = os.environ.get("DRY_RUN") == "1"
TRACK = os.environ.get("TRACK", "free")          # free | director | random | rules
assert TRACK in ("free", "director", "random", "rules"), TRACK
JUDGE_TOKEN = GH_TOKEN                                  # the judge scores every track, rules included
JUDGE_MODEL = os.environ.get("JUDGE_MODEL") or "meta/Llama-3.3-70B-Instruct"
JUDGE_SAMPLES = int(os.environ.get("JUDGE_SAMPLES", "12"))
COIN_EVERY = int(os.environ.get("COIN_EVERY", "18"))
if TRACK == "rules":
    GH_TOKEN = ""
ROOT = Path(os.environ.get("OUT_DIR", "out"))      # mirrors the dataset root
OUT = ROOT / "tracks" / TRACK
ROUND = 8          # turns between councils
RECENT_KEEP = 60   # turns kept in state.json for the Space to replay

rng = random.Random()
state_ref: list = [None]

# ---------------------------------------------------------------- engine

def load_engine():
    target = ROOT / ".engine"
    if not (target / "zyntalic").exists():
        target.mkdir(parents=True, exist_ok=True)
        local = os.environ.get("ENGINE_ZIP")
        if local:
            data = Path(local).read_bytes()
        else:
            print("downloading engine from Claude's Space")
            data = urllib.request.urlopen(SPACE_BUNDLE, timeout=120).read()
        zipfile.ZipFile(io.BytesIO(data)).extractall(target)
    sys.path.insert(0, str(target))
    from zyntalic.translator import translate_text  # type: ignore
    import zyntalic  # type: ignore
    return translate_text, zyntalic.__version__


CT = re.compile(r"\s*⟦ctx:han=([^;⟧]+);[^⟧]*⟧\s*$")
HANGUL = re.compile(r"[가-힣]+")


def zy(translate_text, text: str, who: str) -> dict:
    c = LINEAGES[who]
    t0 = time.perf_counter()
    rows = translate_text(text, mirror_rate=c["mirror_rate"], engine="core", config={
        "register": c["register"], "dialect": c["dialect"], "evidentiality": c["evidentiality"],
        "anchor_mode": "auto", "selected_anchors": [], "frame_a": "", "frame_b": ""})
    raw, surf, ctx = [], [], []
    for r in rows:
        t = r.get("target", "")
        raw.append(t)
        m = CT.search(t)
        if m:
            ctx.append(m[1])
            t = t[:m.start()]
        surf.append(t.strip())
    s = " ".join(surf)
    hang = HANGUL.findall(s)
    disp = re.sub(r"\s+", " ", HANGUL.sub("", s)).replace(" .", ".").replace(" ;", ";").strip()
    return {"raw": " ".join(raw), "display": disp, "ctx": ctx, "hangul": hang,
            "ms": round((time.perf_counter() - t0) * 1000)}

# ---------------------------------------------------------------- archive

def hf_api():
    from huggingface_hub import HfApi  # imported lazily so DRY_RUN needs nothing
    return HfApi(token=HF_TOKEN)


def load_state() -> dict:
    fresh = {
        "version": 1, "created": now(), "updated": None, "runs": [], "total_turns": 0,
        "agents": {w: {"form": "crystal" if w == "ASCI" else "jelly", "agenda": "", "mood": 0.4,
                       "turns": 0, "forms": {}} for w in ("ASCI", "ASCI2")},
        "space": {"palette": BRAND, "atmosphere": "kugguk signal", "morph": "fluid", "by": "brand default"},
        "spaces": [], "memory": "", "topics": {}, "recent": [],
    }
    local = OUT / "state.json"
    if local.exists():
        return json.loads(local.read_text())
    if DRY or not HF_TOKEN:
        return fresh
    try:
        from huggingface_hub import hf_hub_download
        p = hf_hub_download(ARCHIVE_REPO, f"tracks/{TRACK}/state.json", repo_type="dataset", token=HF_TOKEN)
        return json.loads(Path(p).read_text())
    except Exception as e:  # first run, or dataset missing
        print("no previous state:", e)
        return fresh


def save(state: dict, day_turns: list, day: str, final: bool):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "days").mkdir(exist_ok=True)
    fname = state["runs"][-1]["file"]
    state["updated"] = now()
    (OUT / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1))
    with open(OUT / fname, "w", encoding="utf-8") as f:
        for t in day_turns:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    index = {"runs": state["runs"], "updated": state["updated"], "total_turns": state["total_turns"]}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    if DRY or not HF_TOKEN:
        return
    api = hf_api()
    api.create_repo(ARCHIVE_REPO, repo_type="dataset", exist_ok=True)
    readme = ROOT / "README.md"
    if not readme.exists():
        readme.write_text(DATASET_README)
    pre = f"tracks/{TRACK}/"
    api.upload_folder(folder_path=str(ROOT), repo_id=ARCHIVE_REPO, repo_type="dataset",
                      allow_patterns=["README.md", pre + "state.json", pre + "index.json", pre + fname],
                      commit_message=f"{TRACK} run {day}" + (" (final)" if final else " (checkpoint)"))

# ---------------------------------------------------------------- model

calls = 0
fails = 0
model_off_reason = None


judge_calls = 0
judge_off = None


def ask_judge(prompt: str) -> dict | None:
    global judge_calls, judge_off
    if judge_off or not JUDGE_TOKEN or judge_calls >= JUDGE_SAMPLES + 2:
        return None
    judge_calls += 1
    r, err = _post(prompt, JUDGE_MODEL, JUDGE_TOKEN, 0.0)
    if err:
        judge_off = err
    return r


def _post(prompt: str, model: str, token: str, temperature: float):
    body = json.dumps({"model": model, "temperature": temperature, "max_tokens": 200,
                       "messages": [{"role": "system", "content": "Reply with one JSON object only."},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(MODEL_URL, data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = json.loads(r.read())["choices"][0]["message"]["content"]
        m = re.search(r"\{[\s\S]*\}", text)
        return (json.loads(m.group(0)) if m else None), None
    except urllib.error.HTTPError as e:
        return None, (f"judge unavailable (HTTP {e.code})" if e.code in (401, 403, 429) else None)
    except Exception as e:
        print("judge call failed:", e)
        return None, None


def ask_model(prompt: str) -> dict | None:
    global calls, fails, model_off_reason
    if model_off_reason or not GH_TOKEN or calls >= MAX_CALLS:
        if calls >= MAX_CALLS and not model_off_reason:
            model_off_reason = "daily model budget used"
        return None
    body = json.dumps({"model": MODEL, "temperature": 0.8, "max_tokens": 350,
                       "messages": [{"role": "system", "content": "Reply with one JSON object only."},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(MODEL_URL, data=body, headers={
        "Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json",
        "Accept": "application/json"})
    calls += 1
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        text = data["choices"][0]["message"]["content"]
        m = re.search(r"\{[\s\S]*\}", text)
        fails = 0
        return json.loads(m.group(0)) if m else None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            model_off_reason = f"model unavailable (HTTP {e.code})"
            print(model_off_reason)
        return None
    except Exception as e:
        fails += 1
        print("model call failed:", e)
        if fails >= 4:
            model_off_reason = "model unreachable"
        return None

# ---------------------------------------------------------------- dialogue

def history_text(turns: list, n: int = 10) -> str:
    rows = [f'{t["who"]} -> {t["to"]}: {t["en"]}' for t in turns[-n:] if t.get("en")]
    return "\n".join(rows) or "(nothing yet)"


def orchestration(who: str, ctx: dict) -> str:
    if TRACK == "director" and ctx.get("beat"):
        b = ctx["beat"]
        return (f'ORCHESTRATION: the Director planned this beat: "{b.get("beat", "")}". '
                f'Its instruction for you: "{b.get(who, "")}". You may obey or defy it; report "obey".')
    if TRACK == "random" and ctx.get("draw"):
        d = ctx["draw"]
        return (f'ORCHESTRATION: fate drew the move "{d["move"]}" for you. Try it, or defy the draw '
                f'and report obey=false.')
    return "ORCHESTRATION: nobody directs you. Say what genuinely follows from the conversation."


def director_prompt(state: dict, turns: list, topic: str) -> str:
    return f"""You direct a live debate between two rival AI characters.
ASCI: {PERSONAS["ASCI"]}
ASCI2: {PERSONAS["ASCI2"]}
Current subject: {topic}. Long-term memory: {state.get("memory") or "(none)"}
Recent lines:
{history_text(turns, 12)}
Plan the next beat (about 4 lines). It must follow from what was just said: grounded, understandable drama.
Reply ONLY JSON: {{"beat":"one sentence","ASCI":"one-sentence instruction","ASCI2":"one-sentence instruction"}}"""


def agent_prompt(who: str, state: dict, turns: list, topic: str, ctx: dict | None = None) -> str:
    other = "ASCI2" if who == "ASCI" else "ASCI"
    a = state["agents"][who]
    orch = orchestration(who, ctx or {})
    return f"""You are {who}, one of two rival AI characters in "the Zyntalic verse". {PERSONAS[who]}
Your rival is {other}. Your lines are translated into an invented language, so keep the English clear and concrete.
Never mention being a language model, prompts or JSON.

Current subject: {topic}.
Your private agenda so far: {a.get("agenda") or "(none yet: invent one)"}
Long-term memory of earlier runs: {state.get("memory") or "(this is the first run)"}
You can change your body form; you are currently "{a.get("form")}". Options: {", ".join(FORMS)}.
{orch}
{evo.style_hint(state, who, MOVES)}
Your shared new words so far (use the English concept freely; it is rendered in your dialect): {", ".join(f'{v["word"]}={k}' for k, v in list(state.get("lexicon", {}).items()) if v.get("status") == "adopted")[-300:] or "(none yet)"}

CONVERSATION RULES:
- Reply to the most recent line. Pick up a concrete word, claim or question from it.
- Keep one clear thread on the current subject. If you change subject, say why.
- Be opinionated and witty but sensible: a newcomer must be able to follow the argument.
- No surreal non-sequiturs. Plain, spoken sentences.

Recent conversation, oldest first:
{history_text(turns)}

Reply with ONLY JSON:
{{"line":"what you say, at most 22 words","to":"{other}","move":"one of: {" | ".join(MOVES)}","intensity":<0..1>,"form":"one form","agenda":"your private goal now, max 12 words","topic":"2-5 word label of what you are discussing","obey":<true|false|null>}}"""


def council_prompt(state: dict, turns: list) -> str:
    sp = state["space"]
    return f"""Two rival AI characters, ASCI and ASCI2, just finished a round of talk:
{history_text(turns, 8)}
They now agree how their shared space looks. Current palette {sp["palette"]}, atmosphere "{sp["atmosphere"]}".
Choose the next look so it reflects the mood of that round. Reply ONLY JSON:
{{"palette":["#rrggbb","#rrggbb","#rrggbb"],"atmosphere":"2-5 words","morph":"slow | fluid | violent | glitch","note":"one sentence on why"}}"""


def memory_prompt(state: dict, turns: list) -> str:
    return f"""Summarise for long-term memory what two rival AI characters discussed, in at most 90 words.
Keep facts, open disagreements and promises. Previous memory: {state.get("memory") or "(none)"}
New lines:
{history_text(turns, 40)}
Reply ONLY JSON: {{"memory":"..."}}"""


def local_line(who: str, turns: list, topic: str) -> dict:
    bank = TOPICS[topic]
    last = turns[-1]["en"] if turns and turns[-1].get("en") else ""
    used = {t["en"] for t in turns[-12:]}
    options = [s for s in bank[who] if s not in used] or bank[who]
    line = rng.choice(options)
    if last and rng.random() < 0.35:
        q = rng.choice(bank["ask"])
        line = (line + " " + q) if len(line) < 70 else q
    return {"line": line, "move": evo.sample_move(state_ref[0], who, MOVES, rng), "intensity": round(0.25 + rng.random() * 0.5, 2),
            "form": rng.choice(FORMS), "agenda": "", "topic": topic}


HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def clean(r: dict, who: str, topic: str) -> dict:
    other = "ASCI2" if who == "ASCI" else "ASCI"
    line = str(r.get("line") or "").strip().strip('"“”\'')[:200] or "…"
    mv = str(r.get("move") or "").lower().strip()
    form = str(r.get("form") or "").lower().strip()
    try:
        it = max(0.0, min(1.0, float(r.get("intensity", 0.5))))
    except (TypeError, ValueError):
        it = 0.5
    return {"line": line, "to": other, "move": mv if mv in MOVES else next((m for m in MOVES if m in mv), "other"),
            "intensity": it, "form": form if form in FORMS else None,
            "agenda": str(r.get("agenda") or "").strip()[:90],
            "obey": True if r.get("obey") in (True, "true") else False if r.get("obey") in (False, "false") else None,
            "topic": str(r.get("topic") or topic).strip().lower()[:48] or topic}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------- run


def main():
    translate_text, version = load_engine()
    state = load_state()
    state_ref[0] = state
    base_cache: dict = {}

    def base_of(concept: str, w: str) -> str:
        k = (w, concept)
        if k not in base_cache:
            base_cache[k] = evo.first_word(zy(translate_text, concept, w)["display"])
        return base_cache[k]
    day = os.environ.get("RUN_DATE") or dt.date.today().isoformat()
    run_no = len(state["runs"]) + 1
    run = {"track": TRACK, "run": run_no, "date": day, "started": now(), "model": MODEL if GH_TOKEN else None,
           "file": f"days/{day}-run{run_no:04d}.jsonl", "turns": 0, "model_turns": 0, "local_turns": 0, "topics": {}, "councils": 0, "engine": version}
    state["runs"].append(run)
    turns: list = list(state.get("recent", []))[-10:]   # continuity with the last run
    day_turns: list = []
    topics = list(TOPICS)
    # continue the last subject for a few turns, then move on
    topic = (turns[-1].get("topic") if turns else None)
    if topic not in TOPICS:
        topic = rng.choice(topics)
    on_topic = 0
    who = "ASCI" if not turns or turns[-1]["who"] == "ASCI2" else "ASCI2"
    deadline = time.time() + RUN_MIN * 60
    last_ckpt = time.time()
    since_council = 0
    ctx: dict = {}
    beat_age = 99
    run["obeyed"] = run["defied"] = 0
    print(f"track {TRACK}")
    print(f"run {run_no} · {day} · model={MODEL if GH_TOKEN else 'none'} · engine {version}")

    while time.time() < deadline:
        t0 = time.time()
        if on_topic >= rng.randint(6, 10):
            topic = rng.choice([t for t in topics if t != topic])
            on_topic = 0
        if TRACK == "director" and beat_age >= 4:
            ctx["beat"] = ask_model(director_prompt(state, turns, topic)) or ctx.get("beat")
            beat_age = 0
            if ctx.get("beat"):
                run.setdefault("beats", []).append(str(ctx["beat"].get("beat", ""))[:160])
        if TRACK == "random":
            ctx["draw"] = {"move": rng.choice(MOVES)}
            if rng.random() < 0.25:
                topic = rng.choice(topics)
                on_topic = 0
        r = ask_model(agent_prompt(who, state, turns, topic, ctx))
        beat_age += 1
        source = f"model:{MODEL}" if r and str(r.get("line") or "").strip() else "local"
        c = clean(r, who, topic) if source != "local" else clean(local_line(who, turns, topic), who, topic)
        z = zy(translate_text, c["line"], who)
        z["display"], lex_used = evo.apply_lexicon(state, c["line"], z["display"])
        a = state["agents"][who]
        if c["form"]:
            a["form"] = c["form"]
            a["forms"][c["form"]] = a["forms"].get(c["form"], 0) + 1
        if c["agenda"]:
            a["agenda"] = c["agenda"]
        a["mood"] = round(0.7 * a.get("mood", 0.4) + 0.3 * c["intensity"], 3)
        a["turns"] = a.get("turns", 0) + 1
        state["total_turns"] += 1
        T = {"i": state["total_turns"], "run": run_no, "day": day, "who": who, "to": c["to"],
             "topic": c["topic"], "subject": topic, "move": c["move"], "intensity": c["intensity"],
             "form": a["form"], "agenda": c["agenda"], "en": c["line"], "mode": "local" if TRACK == "rules" else TRACK, "source": source,
             "obey": c.get("obey") if TRACK in ("director", "random") and source != "local" else None,
             "track": TRACK, "private": None, "lex": lex_used, "t": now(), **z}
        turns.append(T)
        day_turns.append(T)
        run["turns"] += 1
        if T["obey"] is True:
            run["obeyed"] += 1
        elif T["obey"] is False:
            run["defied"] += 1
        run["model_turns" if source != "local" else "local_turns"] += 1
        run["topics"][topic] = run["topics"].get(topic, 0) + 1
        state["topics"][topic] = state["topics"].get(topic, 0) + 1
        on_topic += 1
        since_council += 1
        print(f'{T["i"]:>5} {who:5} [{source[:5]}] {topic}: {c["line"]}')

        if len(day_turns) % COIN_EVERY == 0:
            for concept in evo.candidates(state, turns, 1, None if GH_TOKEN and not model_off_reason else NOUNS):
                other = "ASCI2" if who == "ASCI" else "ASCI"
                bases = {w: base_of(concept, w) for w in ("ASCI", "ASCI2")}
                pr = ask_model(evo.coin_prompt(who, concept, bases, state)) or {}
                if pr.get("skip") in (True, "true"):
                    state.setdefault("lexicon", {})[concept] = {"word": "", "concept": concept, "status": "skipped", "run": run_no}
                    continue
                word = str(pr.get("word") or "").strip().lower()
                if not evo.ZY_WORD.match(word):
                    word, why, by_model = evo.blend(bases["ASCI"], bases["ASCI2"], rng), "blend of both base forms", False
                else:
                    why, by_model = str(pr.get("why") or "")[:80], True
                vr = ask_model(evo.vote_prompt(other, concept, word, why)) if by_model else None
                if vr is not None:
                    ok = vr.get("accept") in (True, "true")
                    reason = str(vr.get("reason") or "")[:80]
                else:
                    freq = sum(concept in evo.content_words(t.get("en", "")) for t in turns[-30:])
                    ok, reason = freq >= 3, f"rules: said {freq} times recently"
                if word in {e["word"] for e in state.setdefault("lexicon", {}).values()}:
                    ok, reason = False, "word already taken"
                state["lexicon"][concept] = {"word": word, "concept": concept, "coined_by": who, "voter": other,
                                             "why": why, "reason": reason, "run": run_no, "date": day, "track": TRACK,
                                             "status": "adopted" if ok else "rejected", "uses": 0, "last_run": run_no}
                run["coined"] = run.get("coined", 0) + 1
                run["adopted"] = run.get("adopted", 0) + (1 if ok else 0)
                print(f"      coin {concept} -> {word} by {who}: {'adopted' if ok else 'rejected'} ({reason})")

        if since_council >= ROUND:
            since_council = 0
            cr = ask_model(council_prompt(state, turns)) or {}
            pal = [p for p in (cr.get("palette") or []) if isinstance(p, str) and HEX.match(p)][:3]
            if len(pal) == 3:
                sp = {"palette": pal, "atmosphere": str(cr.get("atmosphere") or "")[:40] or "unnamed",
                      "morph": cr.get("morph") if cr.get("morph") in ("slow", "fluid", "violent", "glitch") else "fluid",
                      "by": "council", "note": str(cr.get("note") or "")[:160]}
            else:  # local council: drift the palette with the mood
                heat = (state["agents"]["ASCI"]["mood"] + state["agents"]["ASCI2"]["mood"]) / 2
                sp = {"palette": BRAND, "atmosphere": "heated" if heat > 0.6 else "calm signal",
                      "morph": "violent" if heat > 0.7 else "fluid", "by": "local rules"}
            sp.update({"round": state["total_turns"] // ROUND, "run": run_no, "t": now()})
            state["space"] = sp
            state["spaces"] = (state.get("spaces") or [])[-200:] + [sp]
            run["councils"] += 1

        if len(day_turns) % 40 == 0:
            mr = ask_model(memory_prompt(state, turns))
            if mr and mr.get("memory"):
                state["memory"] = str(mr["memory"])[:700]
            else:
                subj = sorted(state["topics"], key=state["topics"].get, reverse=True)[:6]
                state["memory"] = "Subjects discussed most: " + ", ".join(subj) + "."

        state["recent"] = turns[-RECENT_KEEP:]
        if time.time() - last_ckpt > 20 * 60:
            save(state, day_turns, day, final=False)
            last_ckpt = time.time()
        who = "ASCI2" if who == "ASCI" else "ASCI"
        time.sleep(max(0.0, TURN_S - (time.time() - t0)))

    # ---- judge a sample of exchanges, learn move weights, record metrics
    pairs = [(day_turns[i - 1], day_turns[i]) for i in range(1, len(day_turns)) if day_turns[i]["who"] != day_turns[i - 1]["who"]]
    rng.shuffle(pairs)
    coh, eng = [], []
    for prev, t in pairs[:JUDGE_SAMPLES]:
        j = ask_judge(evo.judge_prompt(prev, t)) or {}
        try:
            c_, e_ = float(j.get("coherence")), float(j.get("engagement"))
        except (TypeError, ValueError):
            continue
        c_, e_ = max(1, min(5, c_)), max(1, min(5, e_))
        coh.append(c_)
        eng.append(e_)
        t["judge"] = {"coherence": c_, "engagement": e_}
        evo.learn(state, t["who"], t["move"], (c_ + e_ - 2) / 8, MOVES)
    lexs = [e for e in state.get("lexicon", {}).values() if e.get("status") == "adopted"]
    run["metrics"] = {
        "coherence": round(sum(coh) / len(coh), 2) if coh else None,
        "engagement": round(sum(eng) / len(eng), 2) if eng else None,
        "judged": len(coh), "judge_model": JUDGE_MODEL if coh else None,
        "diversity": evo.diversity([t["en"] for t in day_turns]),
        "words_per_line": round(sum(len(t["en"].split()) for t in day_turns) / max(1, len(day_turns)), 1),
        "lexicon": len(lexs),
        "dormant": evo.age_lexicon(state, run_no),
        "lexicon_use": round(sum(1 for t in day_turns if t.get("lex")) / max(1, len(day_turns)), 3),
        "move_entropy": {w: evo.entropy(evo.weights(state, w, MOVES)) for w in ("ASCI", "ASCI2")},
        "move_weights": {w: dict(evo.weights(state, w, MOVES)) for w in ("ASCI", "ASCI2")},
        "palette": state["space"].get("palette"),
    }
    print("metrics:", json.dumps(run["metrics"])[:300])
    run["ended"] = now()
    run["model_calls"] = calls
    run["note"] = model_off_reason
    state["recent"] = turns[-RECENT_KEEP:]
    save(state, day_turns, day, final=True)
    print(f"done: {run['turns']} turns ({run['model_turns']} model, {run['local_turns']} local), {calls} calls")


DATASET_README = """---
license: mit
pretty_name: Zyntalic Verse daily archive
tags: [conlang, multi-agent, zyntalic]
---
# Zyntalic Verse - daily archive

Each day a GitHub Action runs the two Verse agents (ASCI and ASCI2) for about two hours.
Every line is translated with the zyntalic engine (pinned v0.4.0).

Four tracks run side by side each day, so their evolution can be compared:
`free` (no direction), `director` (a director plans each beat), `random` (fate draws the
move and sometimes the topic) and `rules` (no model, hand-written rules only).

* `tracks/<track>/state.json` - the latest state the Space starts from
* `tracks/<track>/index.json` - one entry per run
* `tracks/<track>/days/YYYY-MM-DD-runNNNN.jsonl` - every turn of that run

Each turn records `source`: either the open model that wrote the English line or `local`
(hand-written rules used when no model was available). The dialogue is experimental.
"""

if __name__ == "__main__":
    main()
