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

**A numeral system is a third.** Thai statutes number their provisions in Thai digits and the stored
text keeps them, because they are the authentic text rather than layout. So `มาตรา 7` and `มาตรา ๗`
have to meet in the query, which is why `normalise_query` now rewrites ASCII — reversing @liv2lsxs's
refusal to — and why it has to understand enough regex syntax to leave `[0-9]` and `\\d{1,3}` alone
while doing it. See @4zotolb5.
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

ASCII_DIGITS = "0123456789"

# Every non-Arabic decimal system the programme's corpora actually use, each written out in value
# order. Thailand's law list carries the PDPA twice, once as "พ.ศ. 2562" and once as "พ.ศ. ๒๕๖๒",
# and a filter in either system silently drops the other. The stored text keeps its own digits:
# they are the authentic text, not layout, so the two systems meet in the comparison and in the
# query rather than in the document.
#
# Deliberately a short declared list rather than every Unicode decimal script. A sixty-character
# class per digit buys reach into corpora nobody holds; a script is added here in one line when a
# corpus for it exists, and `tests/test_normalise.py` then asserts both folds agree about it.
# CJK numerals are deliberately **not** here, and that is no longer a refusal: 第六条 is
# positional (十, 百), so a kanji numeral is a multi-character token and cannot be a row in a
# per-character table at all. It is folded by `normalise_query` as a token instead, through
# `read_kanji_number` and `write_kanji_number` below. See @4zotolb5 and @kcznu7jq.
NUMERAL_SYSTEMS = {
    "thai": "๐๑๒๓๔๕๖๗๘๙",
}

# digit -> its value, and digit -> every spelling of that value across the systems above.
_DIGIT_VALUE = {ch: n for n in range(10) for ch in
                (ASCII_DIGITS[n], *(digits[n] for digits in NUMERAL_SYSTEMS.values()))}
_DIGIT_SYSTEM = {
    **{ch: "arabic" for ch in ASCII_DIGITS},
    **{ch: name for name, digits in NUMERAL_SYSTEMS.items() for ch in digits},
}
_SPELLINGS = {
    ch: ASCII_DIGITS[value] + "".join(digits[value] for digits in NUMERAL_SYSTEMS.values())
    for ch, value in _DIGIT_VALUE.items()
}
_DIGIT_FOLD = str.maketrans({ch: ASCII_DIGITS[value] for ch, value in _DIGIT_VALUE.items()})
DIGITS = "".join(sorted(_DIGIT_VALUE))

# A kanji numeral is positional, so it is a token rather than ten characters standing in for ten
# others — which is why it cannot live in `NUMERAL_SYSTEMS`. The range is 1..999, which is what
# provision numbering uses and what this reader has always covered; 千 and above are refused rather
# than guessed at. `japan-id` measured the spelling to be single-valued in statutory material: a
# search for a non-positional form (第二三条 for 第二十三条) returns 0 hits in 27,376 kanji article
# citations, so the inverse below is a function and not a generator. See @kcznu7jq.
_KANJI_UNITS = {ch: n for n, ch in enumerate("一二三四五六七八九", start=1)}
_UNIT_KANJI = {n: ch for ch, n in _KANJI_UNITS.items()}
KANJI_NUMERALS = "".join(_KANJI_UNITS) + "十百"
KANJI_MAX = 999


def read_kanji_number(raw: str) -> int:
    """Read a CJK numeral — `五十七` is 57.

    Raises `ValueError` carrying the character it could not read, so a caller that owes its own
    error type can name the offending character without parsing this one's prose.
    """
    total, current, hundreds = 0, 0, 0
    for ch in raw:
        if ch in _KANJI_UNITS:
            current = _KANJI_UNITS[ch]
        elif ch == "十":
            total += (current or 1) * 10
            current = 0
        elif ch == "百":
            hundreds += (current or 1) * 100
            total, current = 0, 0
        else:
            raise ValueError(ch)
    return hundreds + total + current


def write_kanji_number(value: int) -> str:
    """Spell a number the way a statute does — 57 is `五十七`.

    The inverse of `read_kanji_number` over 1..999, and single-valued there. Refuses anything
    outside that range rather than inventing a spelling, for the reason every reader here refuses.
    """
    if not isinstance(value, int) or not 1 <= value <= KANJI_MAX:
        raise ValueError(value)
    hundreds, rest = divmod(value, 100)
    tens, units = divmod(rest, 10)
    out = []
    if hundreds:
        out.append("" if hundreds == 1 else _UNIT_KANJI[hundreds])
        out.append("百")
    if tens:
        out.append("" if tens == 1 else _UNIT_KANJI[tens])
        out.append("十")
    if units:
        out.append(_UNIT_KANJI[units])
    return "".join(out)


_COMPARISON_TABLE = str.maketrans(
    {**LAYOUT_ONLY, **{ch: ASCII_DIGITS[v] for ch, v in _DIGIT_VALUE.items()},
     **{ch: _SEPARATOR_CANONICAL for ch in SEPARATORS}}
)

_WHITESPACE = re.compile(r"\s+")
_ANY_DIGIT_RUN = re.compile(f"[{re.escape(DIGITS)}]+")
_KANJI_RUN = re.compile(f"[{KANJI_NUMERALS}]+")

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


# Above this share of the alphabetic characters, text is CJK prose and the Latin cleaning path in
# `pdf.py` will damage it. Japanese statutory text scores above 0.95; an English page quoting a
# term or two scores in the low hundredths, so the band between is wide.
MAX_CJK_RATIO_FOR_LATIN_PATH = 0.3
# Below this many CJK characters there is nothing to protect, and a check would fire on an English
# document that happens to quote 個人情報.
MIN_CJK_CHARS = 20


def is_cjk(ch: str) -> bool:
    """Is this a character from a script that writes no space between words?"""
    return any(low <= ch <= high for low, high in _CJK_RANGES)


def cjk_ratio(text: str) -> float:
    """CJK characters as a share of the alphabetic characters, 0.0 for text with no letters."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if is_cjk(ch)) / len(letters)


def looks_cjk(text: str) -> bool:
    """Would a Latin-shaped cleaner damage this text?

    Two conditions, because either alone misfires: a ratio alone trips on a four-word fragment, and
    a count alone trips on an English page quoting a Japanese term twice. Lives here rather than in
    `japanese.py` so that `pdf.py` can ask the question without importing the module it points at.
    """
    return (
        sum(1 for ch in text if is_cjk(ch)) >= MIN_CJK_CHARS
        and cjk_ratio(text) > MAX_CJK_RATIO_FOR_LATIN_PATH
    )


def normalise_text(text: str) -> str:
    """Fold layout-only characters out of a document. Unconditional, for every language.

    This is a character fold and nothing else — whitespace policy, line rejoining and furniture
    removal belong to the renderer that calls it.
    """
    return text.translate(_LAYOUT_TABLE)


def fold_digits(text: str) -> str:
    """Rewrite every digit of every declared system as its Arabic spelling.

    The one table both folds read. Public because furniture detection in `pdf.py` needs to read a
    page number written in Thai digits, and because a caller comparing two provision numbers wants
    this without `search_key`'s casefolding and whitespace collapse.
    """
    return text.translate(_DIGIT_FOLD)


def _class_member(text: str) -> str:
    """A folded character rendered safe for the inside of a character class.

    Escaped rather than inserted bare: U+2011 folds to `-`, which would silently turn `[a‑z]`
    into the range `a-z`.
    """
    return re.escape(text)


def _range_expansion(low: str, high: str) -> str:
    """`0-9` plus the same range in every other system, or the caller's own text unchanged.

    Unchanged when the ends are from different systems or descending, because both are the
    caller's error and rewriting one would hide it behind ours.
    """
    if _DIGIT_SYSTEM[low] != _DIGIT_SYSTEM[high] or _DIGIT_VALUE[low] > _DIGIT_VALUE[high]:
        return f"{low}-{high}"
    first, last = _DIGIT_VALUE[low], _DIGIT_VALUE[high]
    spans = [f"{ASCII_DIGITS[first]}-{ASCII_DIGITS[last]}"]
    spans += [f"{digits[first]}-{digits[last]}" for digits in NUMERAL_SYSTEMS.values()]
    return "".join(spans)


def _numeral_token(pattern: str, index: int):
    """A whole numeral run at `index`, folded across scripts, or None if there is not one there.

    The fourth scanner state @kcznu7jq is about. The three states `normalise_query` already tracks
    decide *whether* to rewrite a character; this one decides how much of the pattern one rewrite
    covers, because a kanji numeral is a multi-character token and a per-character substitution
    cannot reach it.

    Returns `(end, regex, head, tail)`. `head` and `tail` are the characters the rest of the
    scanner should treat as standing at each end of what was consumed, so that @ux7izhdj's optional
    space still lands between 第 and the numeral and between the numeral and 条 — which it must,
    because the caller may have typed the arabic spelling of a heading e-Gov letter-spaces.

    A kanji run is folded only when it is the canonical spelling of what it reads. `二三` reads as 3
    under the positional rules and is not how 3 or 23 is written, so it keeps its own characters
    rather than being given a wrong arabic alternative.
    """
    match = _ANY_DIGIT_RUN.match(pattern, index)
    if match:
        run = match.group()
        members = "".join(f"[{_SPELLINGS[ch]}]" for ch in run)
        try:
            kanji = write_kanji_number(int(run.translate(_DIGIT_FOLD)))
        except ValueError:
            # Outside 1..999: no kanji spelling this package will invent, so the per-character
            # expansion @4zotolb5 built is the whole answer, exactly as before.
            return match.end(), members, run[0], run[-1]
        return match.end(), f"(?:{_letter_spaced(kanji)}|{members})", kanji[0], kanji[-1]

    match = _KANJI_RUN.match(pattern, index)
    if match:
        run = match.group()
        value = read_kanji_number(run)
        if not 1 <= value <= KANJI_MAX or write_kanji_number(value) != run:
            return match.end(), _letter_spaced(run), run[0], run[-1]
        members = "".join(f"[{_SPELLINGS[ch]}]" for ch in str(value))
        return match.end(), f"(?:{_letter_spaced(run)}|{members})", run[0], run[-1]
    return None


def _letter_spaced(text: str) -> str:
    """A CJK literal with @ux7izhdj's optional space between each pair of characters."""
    return _LETTER_SPACE.join(text)


def normalise_query(pattern: str) -> str:
    """Rewrite a search pattern so it can reach text that has been through `normalise_text`.

    Four rewrites. Three of them were once confined to non-ASCII input:

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

    The fourth rewrites ASCII, which @liv2lsxs had refused to do: **a digit expands to a class
    holding that digit's spelling in every system in `NUMERAL_SYSTEMS`**, so `มาตรา 7` reaches
    `มาตรา ๗`. A provision is addressed by its number, so a corpus whose digits are Thai is
    unreachable to a user typing Arabic — a zero that reads as a finding, produced by the tool
    built to prevent it. See @4zotolb5.

    Rewriting ASCII costs a scanner, because `[0-9]`, `\\d{1,3}` and `\\1` must survive it. Three
    states are tracked and **nothing is rewritten in two of them**: after a backslash, and inside
    a `{...}` quantifier. Inside a character class a digit is *added to* the class rather than
    nested inside one, and a range of digits gains the parallel range in each system, so `[0-9]`
    becomes `[0-9๐-๙]`. A `{` that never closes suppresses the fold to the end of the pattern
    rather than corrupting it.

    Class-awareness closes @liv2lsxs's documented hole as a side effect: a separator inside a class
    now contributes its five spellings as members instead of a nested class, and @ux7izhdj's
    optional space is no longer inserted inside a class, where it produced something that was not a
    character class at all. The space is otherwise inserted only where *both* neighbours are CJK,
    so it can never land beside a metacharacter, none of which is CJK.

    One known hole remains, documented rather than parsed for: a CJK phrase query can match across
    a genuine word separator — 「個人情報」 hits a line reading 「個人 情報」 — which is a false positive,
    visible as soon as the hit is read, where what it replaces is a zero that reads as a finding.
    """
    out, previous = [], ""
    escaped = in_class = in_quantifier = False
    index, chars, length = 0, list(pattern), len(pattern)

    while index < length:
        ch = chars[index]
        index += 1
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == "\\":
            out.append(ch)
            escaped = True
        elif in_quantifier:
            out.append(ch)
            in_quantifier = ch != "}"
        elif in_class:
            in_class = ch != "]"
            if not in_class:
                out.append(ch)
            elif (
                index + 1 < length
                and chars[index] == "-"
                and ch in _DIGIT_VALUE
                and chars[index + 1] in _DIGIT_VALUE
            ):
                out.append(_range_expansion(ch, chars[index + 1]))
                index += 2
            elif ch in _DIGIT_VALUE:
                out.append(_SPELLINGS[ch])
            elif ch in SEPARATORS:
                out.append("".join(sorted(SEPARATORS)))
            elif ch in LAYOUT_ONLY:
                out.append(_class_member(LAYOUT_ONLY[ch]))
            else:
                out.append(ch)
        else:
            token = _numeral_token(pattern, index - 1)
            if token:
                # A whole numeral run, in either script, folded as one token. @kcznu7jq.
                end, folded, head, tail = token
                if is_cjk(head) and is_cjk(previous):
                    out.append(_LETTER_SPACE)
                out.append(folded)
                index, ch = end, tail
            else:
                if is_cjk(ch) and is_cjk(previous):
                    out.append(_LETTER_SPACE)
                if ch == "[":
                    in_class = True
                    out.append(ch)
                elif ch == "{":
                    in_quantifier = True
                    out.append(ch)
                elif ch in SEPARATORS:
                    out.append(_SEPARATOR_CLASS)
                elif ch in LAYOUT_ONLY:
                    out.append(re.escape(LAYOUT_ONLY[ch]))
                else:
                    out.append(ch)
        previous = ch if not (escaped or in_class or in_quantifier) else ""
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
