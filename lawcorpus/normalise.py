"""One normalisation set, applied to every document whatever its language.

`this.i` @f5mvj6 established the rule for EU text: characters whose sole function is layout are
folded out at extraction, because they are invisible, so a sweep that misses them returns a zero
that reads as a finding. Phase 0 of the Asia programme extended that in one direction and refuted a
design in another.

**Refuted: any rule keyed on a document's language.** Japanese uses U+3001 and *zero* U+FF0C; Korean
has no U+3000 and no full-width punctuation, but 4,966 instances of U+318D `ㆍ`; Chinese uses U+FF0C
69 times and U+3001 79; Singapore's English carries U+2011, the EU trap. And the
**English-language** CTID specification contains stray full-width parentheses — the case that
settles it, because no language tag would have routed that document to a CJK fold. So the set below
is unconditional. See @amdvdsah.

**Rejected: NFKC.** It looks like the general form of this fold and is a trap. Applied to Thai it
decomposes U+0E33 `ำ` into U+0E4D+U+0E32, so a search for `สำนักงาน` typed the normal way goes from
18 hits to 0 — the standard remedy generating the exact failure this module exists to prevent.

**The line the set draws** is width and invisibility, which is @f5mvj6's "layout only" stated
precisely enough to decide new cases. A full-width parenthesis is a *presentation variant*: it means
what an ASCII parenthesis means, and folds. U+3001 IDEOGRAPHIC COMMA, U+3002, and U+318D are
characters in their own right carrying their own meaning, and stay — as curly quotes and en dashes
already did.

Two traps cannot be fixed on this side at all, and `normalise_query` carries them instead: full-width
enumerators are structural, so provision addressing breaks if they are stripped, and U+318D must
survive in the text while still being reachable by a user who types a middle dot. See @liv2lsxs.
"""

from __future__ import annotations

import re

# Characters whose only function is layout: they are invisible, or they are a width variant of a
# character that already exists in ASCII.
LAYOUT_ONLY = {
    "\u00a0": " ",  # NO-BREAK SPACE — inside "Article 22", 232x in C-634/21 alone
    "\u202f": " ",  # NARROW NO-BREAK SPACE
    "\u2007": " ",  # FIGURE SPACE
    "\u205f": " ",  # MEDIUM MATHEMATICAL SPACE
    "\u3000": " ",  # IDEOGRAPHIC SPACE — between a Japanese chapter number and its title
    "\u2011": "-",  # NON-BREAKING HYPHEN — inside case numbers like "C-311/18"
    "\u00ad": "",   # SOFT HYPHEN — invisible, splits words mid-token
    "\u200b": "",   # ZERO WIDTH SPACE
    "\u2060": "",   # WORD JOINER
    "\ufeff": "",   # ZERO WIDTH NO-BREAK SPACE / BOM
}
# The EN QUAD..HAIR SPACE run, all of them typesetting spaces.
LAYOUT_ONLY.update({chr(c): " " for c in range(0x2000, 0x200B)})
# Halfwidth and Fullwidth Forms: U+FF01..U+FF5E are the full-width variants of ASCII !..~, offset
# by a constant. U+FF65 (halfwidth middle dot) is deliberately excluded — it is a separator, and
# separators are handled below rather than folded away.
LAYOUT_ONLY.update({chr(c): chr(c - 0xFEE0) for c in range(0xFF01, 0xFF5F)})
# U+200C ZERO WIDTH NON-JOINER and U+200D ZERO WIDTH JOINER are *not* here. They are invisible but
# they are not layout: in Indic and Arabic scripts they change which glyph is correct.

_LAYOUT_TABLE = str.maketrans(LAYOUT_ONLY)

# The list separator, in its five observed spellings. Korean statutes use U+318D HANGUL LETTER
# ARAEA 4,966 times where a reader would type U+00B7; a search for one finds none of the others.
# These stay in the stored text — they are visible and they mean "and" — so the equivalence is
# expressed in the query instead.
SEPARATORS = frozenset("\u318d\u00b7\u2022\u30fb\uff65")
_SEPARATOR_CLASS = "[" + "".join(sorted(SEPARATORS)) + "]"
_SEPARATOR_CANONICAL = "\u00b7"

# Thai digits, for the comparison fold only. Thailand's law list carries the PDPA twice, once as
# "พ.ศ. 2562" and once as "พ.ศ. ๒๕๖๒", and a filter in either numeral system silently drops the
# other. The stored text keeps its own digits: they are the authentic text.
_THAI_DIGITS = {chr(0x0E50 + n): str(n) for n in range(10)}
_COMPARISON_TABLE = str.maketrans(
    {**LAYOUT_ONLY, **_THAI_DIGITS, **{ch: _SEPARATOR_CANONICAL for ch in SEPARATORS}}
)

_WHITESPACE = re.compile(r"\s+")

# The scripts that write no space between words: hiragana, katakana, the CJK ideographs and their
# extension A, plus the iteration mark and the long-vowel mark. **Hangul is deliberately absent** —
# Korean writes word spaces, so an optional space between two syllables would find matches across
# a genuine word boundary and buy nothing.
_CJK_RANGES = (
    ("々", "〇"),  # 々 iteration mark, 〆, 〇
    ("ぁ", "ヿ"),  # hiragana and katakana, including ー
    ("㐀", "䶿"),  # CJK Unified Ideographs Extension A
    ("一", "鿿"),  # CJK Unified Ideographs
)
# A query-side class matching nothing, an ASCII space, or an ideographic space. Text-side the fold
# has already turned U+3000 into a space, but a query is also run over raw corpora and over text
# this package did not extract.
_LETTER_SPACE = "[ 　]?"


def is_cjk(ch: str) -> bool:
    """Is this a character from a script that writes no space between words?"""
    return any(low <= ch <= high for low, high in _CJK_RANGES)


def normalise_text(text: str) -> str:
    """Fold layout-only characters out of a document. Unconditional, for every language.

    This is a character fold and nothing else — whitespace policy, line rejoining and furniture
    removal belong to the renderer that calls it.
    """
    return text.translate(_LAYOUT_TABLE)


def normalise_query(pattern: str) -> str:
    """Rewrite a search pattern so it can reach text that has been through `normalise_text`.

    Three rewrites, all confined to non-ASCII input:

    - a character the text-side fold rewrites is rewritten the same way here, then regex-escaped,
      so that a user who types a full-width parenthesis gets a literal rather than a capturing
      group;
    - a list separator expands to a class matching all five spellings, so typing a middle dot
      finds the Korean araea;
    - **two adjacent CJK characters gain an optional space between them**, because Japanese heading
      typography letter-spaces short words: e-Gov writes the supplementary-provision heading as
      「附　則」 in 76 of one Act's 77 blocks, so `附則` finds none of them while finding 312
      cross-references in body text. That cannot be fixed on the text side — collapsing the space
      unconditionally would weld `第一章　総則` into one token, and telling the two cases apart needs
      a lexicon — so it is carried here, which is what @liv2lsxs is for. See @ux7izhdj.

    ASCII is never touched, which is what keeps `[0-9]` and `law(fully|ful)` working. The space is
    inserted only where *both* neighbours are CJK, so it can never land beside a metacharacter,
    none of which is CJK.

    Two known holes, both documented rather than parsed for. A separator typed *inside* a character
    class the caller wrote produces a nested class. And a CJK phrase query can now match across a
    genuine word separator — 「個人情報」 hits a line reading 「個人 情報」 — which is a false positive,
    visible as soon as the hit is read, where what it replaces is a zero that reads as a finding.
    """
    out, previous = [], ""
    for ch in pattern:
        if is_cjk(ch) and is_cjk(previous):
            out.append(_LETTER_SPACE)
        if ch in SEPARATORS:
            out.append(_SEPARATOR_CLASS)
        elif ch in LAYOUT_ONLY:
            out.append(re.escape(LAYOUT_ONLY[ch]))
        else:
            out.append(ch)
        previous = ch
    return "".join(out)


def search_key(text: str) -> str:
    """An aggressive fold for *comparing* two strings — never for storing one.

    Its use is `method.md` §2's expected-phrase check, which Phase 0 saw abort on a correct Thai
    document: the title was line-wrapped across four lines of the PDF, and the numeral systems
    differed. A harvester that compares raw strings rejects good documents, and an agent seeing
    that abort is liable to weaken the check rather than fix the comparison.

    Folds numeral systems together, canonicalises every separator spelling, collapses all
    whitespace, and casefolds. Anything this returns is a key, not text: it is never stored and
    never quoted.
    """
    folded = text.translate(_COMPARISON_TABLE)
    return _WHITESPACE.sub(" ", folded).strip().casefold()
