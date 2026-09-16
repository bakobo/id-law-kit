"""Thai PDFs, where the general extraction path loses the text without saying so.

Three findings from Phase 0, every one observed on real Royal Gazette bytes.

**`pdftotext` drops U+0E33 `ำ`, 100% of the time.** Not reordered — gone. `กำหนด`, "to prescribe"
and among the highest-frequency verbs in any statute, occurs 87 times in the PDPA and matches zero;
`สำนักงาน` 119 times and matches zero. An analyst greps a Thai corpus for `กำหนด`, finds nothing,
and concludes the instrument prescribes nothing. It is producer-dependent — the Word-produced
มธอ. 11 extraction carries `ำ` 699 times — so a spot check finds nothing wrong and the corpus has a
silent per-document reliability difference.

**NFKC makes it worse.** It decomposes every `ำ` into U+0E4D+U+0E32, so after "normalising" a corpus
a query typed the normal way matches nothing at all: 18 hits become 0. The standard remedy is the
failure mode, which is why `normalise.py` folds width and invisibility only and why nothing here
calls `unicodedata.normalize`.

**Mojibake extracts non-empty.** An embedded subset font with a non-standard `/Encoding` and no
ToUnicode CMap yields output that is plausibly Thai-looking and semantically noise, so `method.md`
§6's "refuse empty extractions" never fires. Worse, the running header extracts *correctly* while
the body does not, so a header-based sanity check passes.

**A third corruption mode passes both of those gates.** The DOPA/ThaID manual extracts with its
sara am intact and every tone mark gone — `สราง` for `สร้าง`, `ใหม` for `ใหม่` — so it is readable,
wrong, and greps wrong. See @h4srdl2g.

So this module gates rather than repairs: a page whose Thai character ratio collapses, a document
with no `ำ` at all, and a document with no tone mark at all, are **refused** and routed to OCR. See
`this.i` @7xsnhink, @psletl4a and @h4srdl2g.

The ratio gate alone refused four sound documents for every one it caught, because a bibliography
page inside a Thai instrument is legitimately more Latin than Thai. A page it suspects is now put
to a second question — does the Latin read as words — before it is refused. See @szp4xt3n.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .errors import LawcorpusError
from .normalise import normalise_text, search_key
from .pdf import raw_pages, strip_repeated_furniture

# Thai block. Everything in it is Thai; nothing outside it is.
_THAI_FIRST, _THAI_LAST = "฀", "๿"
SARA_AM = "ำ"

# Below this share of alphabetic characters, a page carrying Thai is not Thai prose.
_MIN_THAI_RATIO = 0.5
# Fewer Thai characters than this and the page is Latin — an English translation, not a failure.
_MIN_THAI_CHARS = 10
# The sara-am check needs enough text to be conclusive: at roughly 1.5% of Thai prose, zero U+0E33
# in this many characters is not a document without the vowel, it is a typesetter that lost it.
_SARA_AM_FLOOR = 500

# The tone marks, U+0E48..U+0E4B. Thai writes one roughly every twenty characters, so the same
# floor carries a wider margin here than it does for sara am: a document this long with none of
# them lost them. @h4srdl2g.
TONE_MARKS = "่้๊๋"
_TONE_MARK_FLOOR = 500

# @szp4xt3n. A Latin run is two letters or more; it "reads as a word" at three or more with a
# vowel. Crude on purpose — the point is not to recognise English but to tell prose from the
# residue of a broken encoding, and `thailand-id` measured those at 0.92-0.97 against 0.12.
_LATIN_RUN = re.compile(r"[A-Za-z]{2,}")
_VOWEL = re.compile(r"[aeiouAEIOU]")
# Above this share of Latin runs reading as words, the Latin on the page is real text.
WORDS_AT = 0.5
# Below this many runs the share is noise, and a page the ratio gate suspects stays refused.
MIN_LATIN_RUNS = 8

# A tone mark that has landed after a following-vowel. This sequence is never correct Thai, which
# is what makes the repair safe; the ambiguous cluster case is deliberately left alone. @psletl4a.
_MISORDERED_MARK = re.compile("([าำๅ])([่-๋])")

# The Gazette masthead, which appears on every page immediately after the form feed. `เล่ม` and
# `หน้า` are matched in their reordered spellings too (`เลม่`, `หนา้`), because the header is where
# the reordering was observed.
_GAZETTE_FURNITURE = re.compile(
    r"^[ \t]*(?:"
    r"ราชกิจจานุเบกษา"
    r"|เล[ม่้]+[ \t]*[๐-๙\d]"
    r"|หน[า่้]+[ \t]*[๐-๙\d]"
    r"|.*ตอน(?:ที่|พิเศษ)"
    r").*$",
    re.MULTILINE,
)

_WATERMARK_MAX_CHARS = 4
_WATERMARK_MIN_REPEATS = 2
_BLANKS = re.compile(r"\n{3,}")


class ThaiTextError(LawcorpusError):
    """A Thai extraction that must not be stored.

    Never raised directly: it is the root of the family and the prefix a caller matches on —
    `e.input.format.thai-text.` gathers every way a Thai extraction can be unusable, including
    ones minted after the caller was written.
    """

    code = "e.input.format.thai-text.f"


class ThaiMojibakeError(ThaiTextError):
    """Output that is plausibly Thai-looking and semantically noise."""

    code = "e.input.format.thai-text.mojibake.f"


class ThaiSaraAmError(ThaiTextError):
    """A Thai document that has lost every U+0E33, which its typesetter does silently."""

    code = "e.input.format.thai-text.sara-am.f"


class ThaiToneMarkError(ThaiTextError):
    """A Thai document that has lost every tone mark, which passes both the other gates."""

    code = "e.input.format.thai-text.tone-marks.f"


class ThaiEmptyError(ThaiTextError):
    """No text layer at all — the case `pdf.py` already refuses, restated for this path."""

    code = "e.input.format.thai-text.empty.f"


def is_thai(ch: str) -> bool:
    return _THAI_FIRST <= ch <= _THAI_LAST


def thai_ratio(text: str) -> float:
    """Thai characters as a share of the alphabetic characters, 0.0 for text with no letters.

    The mojibake signal. Real Thai statutory prose scores above 0.9; the noise an encoding-less
    subset font produces scores far below, because it lands as Latin letters and digits.
    """
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if is_thai(ch)) / len(letters)


def word_likeness(text: str) -> tuple:
    """The share of the Latin runs in `text` that read as words, and how many runs there were.

    Three letters or more with at least one vowel. Lifted from `thailand-id/tools/adjudicate.py`,
    where it separated four sound bibliography pages from one genuinely damaged page: 0.92, 0.94,
    0.94 and 0.97 against 0.12. Public so that the consumer which measured it can stop carrying
    its own copy.
    """
    runs = _LATIN_RUN.findall(text)
    if not runs:
        return 0.0, 0
    words = sum(1 for run in runs if len(run) >= 3 and _VOWEL.search(run))
    return words / len(runs), len(runs)


def compose_sara_am(text: str) -> str:
    """Fold the decomposed spelling U+0E4D+U+0E32 onto U+0E33.

    The two render identically and are different bytes, and the ETDA Establishment Act is spelled
    the second way, so a search for its correct name does not find it. This is the opposite
    direction from NFKC, deliberately.
    """
    return text.replace("ํา", SARA_AM)


def repair_marks(text: str) -> str:
    """Move a tone mark that landed after a following-vowel back in front of it.

    `pdftotext` orders glyphs by horizontal position, so a mark sitting above its base is emitted
    after the next glyph: `หน้า` extracts as `หนา้`, and nothing in Unicode normalisation repairs
    it. Only this sequence is repaired, because only this one can never be correct. The other
    observed shape, `เล่ม` → `เลม่`, is indistinguishable from the correct consonant cluster in
    `กล่าว` without a lexicon, and guessing there would corrupt good text. ~4fdi
    """
    return _MISORDERED_MARK.sub(r"\2\1", text)


def thai_search_key(text: str) -> str:
    """`normalise.search_key`, with the Thai folds applied first.

    For `method.md` §2's expected-phrase check, which Phase 0 saw abort on a *correct* Royal Decree:
    the title was wrapped across four lines of the PDF and every `ำ` had been eaten. An agent seeing
    that abort is liable to weaken the check rather than fix the comparison.
    """
    return search_key(repair_marks(compose_sara_am(text)))


def strip_gazette_furniture(page: str) -> str:
    """Drop the Royal Gazette masthead, which appears on all 44 pages of the PDPA.

    Frequency-based furniture removal reaches it only when a run of pages happens to agree; the
    fixed `เล่ม … ตอนที่ … / หน้า … / ราชกิจจานุเบกษา / <date>` signature is reliable on its own.
    """
    return _GAZETTE_FURNITURE.sub("", page)


def strip_watermark_fragments(text: str) -> str:
    """Remove a diagonal watermark that `pdftotext` emits as fragments between sentences.

    ETDA's English translations carry "Unofficial Translated" as a rotated overlay, which lands as
    `Uno` / `ffic` / `ial` / `Tra` / `nsl` / `ate` / `d` in the middle of the text. Harmless to a
    reader, fatal to a phrase search that straddles one.
    """
    lines = text.splitlines()
    counts = Counter(line.strip() for line in lines)
    kept = [
        line
        for line in lines
        if not (
            0 < len(line.strip()) <= _WATERMARK_MAX_CHARS
            and line.strip().isascii()
            and line.strip().isalpha()
            and counts[line.strip()] >= _WATERMARK_MIN_REPEATS
        )
    ]
    return "\n".join(kept)


def _poppler_pages(path):
    """The default reader: poppler, without this package's Latin-shaped cleaning."""
    return raw_pages(path)


def _gate(pages: list) -> None:
    """Refuse before anything is cleaned, so a refusal cannot be mistaken for a cleaning bug."""
    if not any(page.strip() for page in pages):
        raise ThaiEmptyError(
            "Every page extracted to whitespace, so this PDF has no text layer. It is a scanned "
            "image and needs OCR before it can be quoted."
        )
    thai_total = 0
    for number, page in enumerate(pages, start=1):
        thai_here = sum(1 for ch in page if is_thai(ch))
        thai_total += thai_here
        if thai_here < _MIN_THAI_CHARS:
            continue  # A Latin page: ETDA publishes English translations, which are not failures.
        ratio = thai_ratio(page)
        if ratio < _MIN_THAI_RATIO:
            _judge_the_latin(number, ratio, page)
    if thai_total >= _SARA_AM_FLOOR and not any(SARA_AM in page for page in pages):
        raise ThaiSaraAmError(
            f"This extraction holds {thai_total} Thai characters and not one U+0E33 (sara am, "
            f"'ำ'), which is impossible in Thai prose of that length: the typesetter dropped every "
            f"one. 'กำหนด' occurs 87 times in the Gazette PDPA and matches zero times in its "
            f"extraction, so a sweep over this text would report that the instrument prescribes "
            f"nothing. Re-extract with OCR."
        )
    if thai_total >= _TONE_MARK_FLOOR and not any(
        mark in page for page in pages for mark in TONE_MARKS
    ):
        raise ThaiToneMarkError(
            f"This extraction holds {thai_total} Thai characters and not one tone mark "
            f"(U+0E48-U+0E4B, '่ ้ ๊ ๋'), which is impossible in Thai prose of that length: Thai "
            f"writes one roughly every twenty characters, so the typesetter dropped every one. "
            f"This is the corruption the other two gates cannot see — the DOPA manual keeps its "
            f"sara am and its Thai character ratio while extracting 'สราง' for 'สร้าง' and 'ใหม' "
            f"for 'ใหม่', so it reads as sound Thai and matches nothing a reader would type. "
            f"Re-extract with OCR."
        )


def _judge_the_latin(number: int, ratio: float, page: str) -> None:
    """A page the ratio suspects is refused unless its Latin reads as words. @szp4xt3n.

    The ratio gate on its own refused four sound documents for every one it caught, and every
    refusal was a bibliography page — Latin citations inside a Thai instrument, where the Thai
    share of the letters legitimately falls below half. A gate that refuses good documents is
    worse than no gate, because the remedy a person reaches for is turning it off.
    """
    share, runs = word_likeness(page)
    if runs < MIN_LATIN_RUNS:
        raise ThaiMojibakeError(
            f"Page {number} carries Thai characters but only {ratio:.0%} of its letters are Thai, "
            f"which is what an embedded subset font with no ToUnicode CMap produces: output that "
            f"is non-empty, looks Thai, and means nothing. There are too few Latin runs on this "
            f"page ({runs}) to tell that apart from a page of citations, so it is refused rather "
            f"than guessed at. Note that fidelity varies within one document — the running header "
            f"often extracts correctly while the body does not — so re-extract with OCR rather "
            f"than trusting any part of the embedded text layer."
        )
    if share < WORDS_AT:
        raise ThaiMojibakeError(
            f"Page {number} carries Thai characters but only {ratio:.0%} of its letters are Thai, "
            f"and only {share:.0%} of its {runs} Latin runs read as words. That is the signature "
            f"of an embedded subset font with no ToUnicode CMap: output that is non-empty, looks "
            f"Thai, and means nothing. A page of Latin citations inside a Thai instrument scores "
            f"above 90% here and is not refused. Note that fidelity varies within one document — "
            f"the running header often extracts correctly while the body does not — so re-extract "
            f"with OCR rather than trusting any part of the embedded text layer."
        )


def extract_thai(path, reader=None) -> str:
    """Extract a Thai PDF, refusing the two failures the general path cannot see.

    `reader` is injected so the gates can be tested on the text that carries the traps rather than
    on a PDF that happens to reproduce them; by default it is poppler.

    Nothing here calls `unicodedata.normalize`, and nothing rejoins wrapped lines with a space:
    Thai has no inter-word spaces, so a rejoin would insert a break inside a word rather than
    remove one.
    """
    pages = list((reader or _poppler_pages)(Path(path)))
    _gate(pages)

    # Which rule takes a Thai cover page's standard number is undiagnosed: ~6key.
    pages = [strip_gazette_furniture(page) for page in strip_repeated_furniture(pages)]
    text = normalise_text("\n".join(pages).replace("\f", "\n"))
    text = repair_marks(compose_sara_am(text))
    text = strip_watermark_fragments(text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return _BLANKS.sub("\n\n", text).strip() + "\n"
