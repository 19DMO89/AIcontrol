"""
Heuristic "does this text look AI-generated?" check for the clipboard monitor.

Deliberately conservative: ordinary copy-paste (a code snippet, a file path, a
paragraph lifted from a PDF, a log excerpt, a spreadsheet row) should score
near zero. Only text carrying several of the stylistic tells of an LLM answer
trips the threshold. It is a circumstantial signal - findings are logged as a
*warning*, with the matched signals and an excerpt shown for a human to judge.

    from aitext import analyse
    is_ai, score, reasons = analyse(text)

No third-party dependencies (bundled into AISessionAgent.exe).
"""

import re

import config

# ── 1. Near-certain give-aways - any one alone is decisive ────────────────────
_HARD_MARKERS = [
    "as an ai", "as an ai language model", "as a large language model",
    "i am an ai", "i'm an ai", "i am a language model", "i'm a language model",
    "as of my last knowledge update", "as of my knowledge cutoff",
    "my last knowledge update", "my training data", "my knowledge cutoff",
    "i don't have personal opinions", "i do not have personal opinions",
    "i don't have access to real-time", "i cannot provide real-time information",
    "i cannot browse the internet", "i'm unable to browse",
    "i don't have the ability to access", "i cannot access external",
    "als ki-sprachmodell", "als großes sprachmodell", "als ki-assistent",
    "ich bin eine ki", "ich bin ein sprachmodell", "als sprachmodell",
    "mein wissensstand", "meine trainingsdaten", "mein wissen reicht bis",
    "ich habe keinen zugriff auf echtzeit",
]

# ── 2. Soft tells - each contributes to the score ────────────────────────────
_OPENERS = [
    "certainly!", "certainly,", "certainly.", "sure!", "sure,", "sure thing",
    "of course!", "of course,", "absolutely!", "absolutely,",
    "great question", "that's a great question", "that is a great question",
    "i'd be happy to help", "i would be happy to help", "happy to help",
    "here's a", "here is a", "here's an", "here is an", "let's dive in",
    "let's break this down", "let me break this down", "let's explore",
    "in this guide", "in summary,", "to summarize,", "sure, here's",
    "sure! here's", "sure! here is",
    "natürlich!", "natürlich,", "selbstverständlich!", "gerne!",
    "gerne helfe ich", "hier ist eine", "hier ist ein", "hier eine übersicht",
    "im folgenden", "zusammengefasst:",
]
_CLOSERS = [
    "let me know if you have any questions", "let me know if you need",
    "let me know if you'd like", "i hope this helps", "hope this helps",
    "hope that helps", "feel free to ask", "feel free to reach out",
    "would you like me to", "do you want me to", "if you have any further questions",
    "if you'd like, i can", "let me know how you'd like to proceed",
    "ich hoffe, das hilft", "ich hoffe, das hilft dir weiter",
    "lass es mich wissen", "sag mir gern bescheid", "möchtest du, dass ich",
    "falls du weitere fragen hast",
]
_CLICHES = [
    "it's worth noting", "it is worth noting", "it's important to note",
    "it is important to note", "it's important to remember",
    "in the realm of", "delve into", "delving into", "a testament to",
    "plays a crucial role", "plays a vital role", "plays a significant role",
    "navigating the", "in today's fast-paced", "in today's digital age",
    "when it comes to", "on the other hand", "in conclusion,",
    "furthermore,", "moreover,", "additionally,", "that being said,",
    "it's essential to", "a wide range of", "a variety of factors",
    "es ist wichtig zu beachten", "es sei darauf hingewiesen",
    "spielt eine entscheidende rolle", "spielt eine wichtige rolle",
    "zusammenfassend lässt sich sagen", "darüber hinaus", "des weiteren",
    "in der heutigen schnelllebigen",
]


def analyse(text: str):
    """Return (is_ai_like: bool, score: int, reasons: list[str])."""
    reasons: list[str] = []
    if not text or not text.strip():
        return (False, 0, reasons)

    low = text.lower()

    for m in _HARD_MARKERS:
        if m in low:
            return (True, 100, [f'AI disclaimer: "{m}"'])

    score = 0

    head = low.lstrip("#>*-• \t\r\n")[:60]
    if any(head.startswith(o) for o in _OPENERS):
        score += 2
        reasons.append("AI-style opening line")

    closer_hits = [c for c in _CLOSERS if c in low]
    if closer_hits:
        score += 2
        reasons.append("AI-style sign-off / offer to help")

    cliche_hits = [c for c in _CLICHES if c in low]
    if len(cliche_hits) >= 2:
        score += min(3, len(cliche_hits) - 1)
        reasons.append(f"{len(cliche_hits)} filler phrases")
    elif cliche_hits:
        score += 1
        reasons.append("filler phrase")

    headers = len(re.findall(r"(?m)^\s{0,3}#{1,4}\s+\S", text))
    if headers >= 2:
        score += 2
        reasons.append(f"{headers} Markdown headings")

    bold = len(re.findall(r"\*\*[^*\n]{2,80}\*\*", text))
    if bold >= 3:
        score += 1
        reasons.append(f"{bold} bold spans")

    bullets = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S", text))
    if bullets >= 4:
        score += 2
        reasons.append(f"{bullets} list items")

    if re.search(r"(?s)(?<!\d)1[.)]\s.+?(?<!\d)2[.)]\s.+?(?<!\d)3[.)]\s", text):
        score += 1
        reasons.append("numbered walkthrough")

    if text.count(" — ") >= 3 or text.count("—") >= 4:
        score += 1
        reasons.append("frequent em-dashes")

    if len(text) > 1500 and (headers >= 1 or bullets >= 4):
        score += 1
        reasons.append("long, heavily structured answer")

    return (score >= config.CLIPBOARD_AI_SCORE, score, reasons)
