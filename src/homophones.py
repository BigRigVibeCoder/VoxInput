"""
src/homophones.py — Common ASR homophone corrections for VoxInput.

P9-D: Post-processing step after spell correction. Maps common ASR
confusions to context-appropriate forms using simple preceding-word rules.

Usage:
    from src.homophones import fix_homophones
    text = fix_homophones("they went over their to get there things")
    # → "they went over there to get their things"
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Homophone Groups ─────────────────────────────────────────────────────────
# Each group: (words_in_group, context_rules)
# Context rules: list of (regex_pattern, replacement)
# Rules are tested in order; first match wins.

HOMOPHONE_RULES: list[tuple[re.Pattern, str]] = [
    # their/there/they're
    # "they're" = they + are (before verbs/adverbs)
    (re.compile(r"\b(their|there|they're)\b(?=\s+(going|coming|running|walking|doing|making|trying|getting|having|being|not|always|never|still|already|just|also|probably|really|actually))", re.I),
     "they're"),
    # "there" = location (after go/went/over/right/out/up)
    (re.compile(r"\b(over|go|went|going|right|out|up|down|get)\s+(their|they're)\b", re.I),
     lambda m: m.group(1) + " there"),
    # "their" = possessive (before nouns — fallback when followed by a word)
    (re.compile(r"\b(there|they're)\s+(house|car|things?|stuff|way|place|name|family|friend|home|work|own|new|old|big|little|first|last)\b", re.I),
     lambda m: "their " + m.group(2)),

    # to/too/two — context-aware disambiguation
    #  "two" when followed by words that are clearly countable nouns
    #  Uses the number system: "to" → "two" only before obvious plural nouns
    (re.compile(r"\bto\s+(robots?|databases?|servers?|hundred|thousand|million|billion|trillion|people|things?|times?|ways?|days?|years?|hours?|minutes?|seconds?|months?|weeks?|items?|files?|pages?|lines?|words?|parts?|steps?|points?|types?|nodes?|sets?|pairs?|more|or\s+three|or\s+more|of\s+them)\b", re.I),
     lambda m: "two " + m.group(1)),
    #  "too" before degree adjectives
    (re.compile(r"\b(to)\s+(much|many|late|early|fast|slow|long|short|big|small|hard|easy|hot|cold|far|close|bad|good|often|little)\b", re.I),
     lambda m: "too " + m.group(2)),
    (re.compile(r"\bme (too|two)\b", re.I), "me too"),

    # its/it's
    (re.compile(r"\bits\s+(a|an|the|not|been|going|coming|just|really|very|about|always|never|still)\b", re.I),
     lambda m: "it's " + m.group(1)),
    (re.compile(r"\b(it's)\s+(own|way|name|place|color|size|weight|length|shape)\b", re.I),
     lambda m: "its " + m.group(2)),

    # your/you're
    (re.compile(r"\b(your)\s+(going|coming|doing|making|trying|getting|not|right|wrong|welcome|sure|done|ready|here|there)\b", re.I),
     lambda m: "you're " + m.group(2)),
    (re.compile(r"\b(you're)\s+(house|car|things?|name|family|friend|home|work|own|new|old)\b", re.I),
     lambda m: "your " + m.group(2)),

    # then/than
    (re.compile(r"\b(bigger|smaller|faster|slower|better|worse|more|less|older|younger|higher|lower|longer|shorter|rather|other)\s+then\b", re.I),
     lambda m: m.group(1) + " than"),

    # affect/effect
    (re.compile(r"\bthe\s+affect\b", re.I), "the effect"),
    (re.compile(r"\bno\s+affect\b", re.I), "no effect"),

    # accept/except
    (re.compile(r"\bexcept\s+(the|this|that|my|your|our|his|her|it)\b", re.I),
     lambda m: "accept " + m.group(1)),
]


def fix_homophones(text: str) -> str:
    """Apply context-aware homophone corrections to text."""
    for pattern, replacement in HOMOPHONE_RULES:
        text = pattern.sub(replacement, text)
    return text
