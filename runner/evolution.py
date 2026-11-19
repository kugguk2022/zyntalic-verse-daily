"""Slow, daily evolution for the Verse: language (lexicon), agents (move
learning from judged rewards) and run metrics.

Everything here is deliberately simple and inspectable. Each piece writes its
evidence into state.json so the dashboard can show how it changed over days.
"""
from __future__ import annotations

import math
import random
import re
from collections import Counter

STOP = set("""a an and are as at be been but by can could did do does for from had has have he her
here him his how i if in into is it its just like me more most my no not now of on one or our out
over said say says she so some than that the their them then there these they this those to too up
us very was we were what when where which who why will with would you your yes yet also only even
because about after again before both each every much many still such own same other any all
really thing things something nothing anything everything rival asci asci2 visitor
show first make makes think know want need tell keep take give look come going doing being never always
sure means mean answer answers question ask asks says told tells again better best worse less least
which while until other another
""".split())

WORD = re.compile(r"[A-Za-z][A-Za-z'-]{4,}")
ZY_WORD = re.compile(r"^[a-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ'-]{3,14}$", re.I)

# ------------------------------------------------------------------ language


def content_words(text: str) -> list[str]:
    return [w.lower().strip("'-") for w in WORD.findall(text) if w.lower() not in STOP]


def lexicon(state: dict) -> dict:
    return state.setdefault("lexicon", {})


BAD_END = ("ly", "ing", "ed", "ful", "ous", "ive", "able")


def candidates(state: dict, turns: list, k: int = 3, nouns: set | None = None) -> list[str]:
    lex = lexicon(state)
    c = Counter(w for t in turns[-30:] for w in content_words(t.get("en", "")))
    out = [w for w, n in c.most_common(60) if n >= 2 and w not in lex and not w.endswith(BAD_END)]
    if nouns is not None:
        out = [w for w in out if w in nouns]
    return out[:k]


def first_word(display: str) -> str:
    for tok in display.split():
        tok = tok.strip(".,;:!?…\"'()")
        if ZY_WORD.match(tok):
            return tok.lower()
    return ""


def syllables(word: str) -> list[str]:
    return re.findall(r"[^aeiouyąęó]*[aeiouyąęó]+", word.lower()) or [word]


def blend(a: str, b: str, rng: random.Random) -> str:
    sa, sb = syllables(a), syllables(b)
    w = "".join(sa[:2] + sb[-1:])
    return w[:9] if len(w) >= 3 else (a or b)[:8]


def coin_prompt(who: str, concept: str, bases: dict, state: dict) -> str:
    sample = ", ".join(f'{v["word"]}={k}' for k, v in list(lexicon(state).items())[-8:]) or "(none yet)"
    return f"""You are {who}. You and your rival are slowly growing your own dialect of an invented language.
You keep talking about "{concept}". The base engine renders it as "{bases['ASCI']}" (mountain) and "{bases['ASCI2']}" (coast).
Words already adopted: {sample}
Coin ONE new word for "{concept}": 3 to 12 letters, built from syllables of the two base forms, easy to say.
If "{concept}" is not a meaningful idea or thing worth its own word, reply {{"skip":true}}.
Reply ONLY JSON: {{"word":"...","why":"under 12 words"}}"""


def vote_prompt(who: str, concept: str, word: str, why: str) -> str:
    return f"""You are {who}. Your rival proposes the new word "{word}" for "{concept}" ({why}).
Accept it into your shared dialect only if it is easy to say and fits. Reply ONLY JSON: {{"accept":true|false,"reason":"under 10 words"}}"""


def apply_lexicon(state: dict, en: str, display: str, base_of=None, max_tail: int = 3) -> tuple[str, list]:
    """The engine translates whole sentences, so coined words cannot be swapped in
    word-for-word. They are added as a short dialect tail after the sentence."""
    lex = lexicon(state)
    words = set(content_words(en))
    used = []
    for concept, entry in lex.items():
        if entry.get("status") != "adopted" or concept not in words:
            continue
        entry["uses"] = entry.get("uses", 0) + 1
        entry["last_run"] = state["runs"][-1]["run"]
        used.append({"concept": concept, "word": entry["word"]})
    used = used[:max_tail]
    return display, used


def age_lexicon(state: dict, run_no: int, dormant_after: int = 7) -> int:
    n = 0
    for e in lexicon(state).values():
        if e.get("status") == "adopted" and run_no - e.get("last_run", e.get("run", run_no)) >= dormant_after:
            e["status"] = "dormant"
            n += 1
    return n

# ------------------------------------------------------------------ agents (bandit-style move learning)


def weights(state: dict, who: str, moves: list) -> dict:
    a = state["agents"][who]
    w = a.setdefault("move_weights", {})
    for m in moves:
        w.setdefault(m, 1.0)
    return w


def style_hint(state: dict, who: str, moves: list) -> str:
    w = weights(state, who, moves)
    if not any(abs(v - 1.0) > 0.05 for v in w.values()):
        return "No learned style yet."
    top = sorted(w, key=w.get, reverse=True)
    return (f"Learned from earlier days (judged reactions): your strongest moves are "
            f"{', '.join(top[:3])}; your weakest are {', '.join(top[-2:])}.")


def sample_move(state: dict, who: str, moves: list, rng: random.Random) -> str:
    w = weights(state, who, moves)
    total = sum(w.values())
    r = rng.random() * total
    for m, v in w.items():
        r -= v
        if r <= 0:
            return m
    return moves[0]


def judge_prompt(prev: dict, t: dict) -> str:
    return f"""Rate one exchange from a debate between two AI characters, as a strict, fair reader.
{prev['who']}: {prev['en']}
{t['who']}: {t['en']}
coherence: does the reply make sense and respond to the previous line (1-5)?
engagement: is it interesting, specific and in character (1-5)?
Reply ONLY JSON: {{"coherence":n,"engagement":n}}"""


def learn(state: dict, who: str, move: str, reward: float, moves: list, lr: float = 0.25):
    a = state["agents"][who]
    base = a.get("reward_mean", 0.5)
    w = weights(state, who, moves)
    if move in w:
        w[move] = round(min(3.0, max(0.2, w[move] * math.exp(lr * (reward - base) * 4))), 4)
    a["reward_mean"] = round(0.9 * base + 0.1 * reward, 4)


def entropy(w: dict) -> float:
    s = sum(w.values()) or 1
    p = [v / s for v in w.values() if v > 0]
    return round(-sum(x * math.log(x) for x in p) / math.log(len(p) or 2), 3)

# ------------------------------------------------------------------ metrics


def diversity(lines: list[str]) -> float:
    grams = [g for l in lines for g in zip(l.lower().split(), l.lower().split()[1:])]
    return round(len(set(grams)) / len(grams), 3) if grams else 0.0


PRIME_V1 = {   # targets for the "Prime v1" scorecard; edit freely
    "coherence": 4.0,      # judge average over the last 7 runs, out of 5
    "engagement": 3.8,
    "diversity": 0.75,     # distinct word-pairs per run
    "lexicon": 250,        # adopted words
    "lexicon_use": 0.30,   # share of lines that use an adopted word
    "streak": 150,         # consecutive days with a run
}
