"""Japanese PDFs, where the general cleaning path corrupts the text without saying so.

`pdf.py` infers a reading order and rejoins the hard wrapping poppler inherits from the page. Both
rules are English, and both fail silently on Japanese:

- `_UNTERMINATED` treats a line as mid-sentence unless it ends in `.:;?!`, so every Japanese line
  ending in 。 is judged unfinished and welded to the line below, fusing two sentences the source
  does not contain.
- The weld inserts **a space**. Japanese writes none between words. Over a Digital Agency slide
  「③発行者の電子署名から構成される。」 comes out as 「③発行者の 電子署名から構成される。」, and the phrase
  is no longer findable — the cleaner manufacturing the silent false negative that `method.md` §4
  is about, rather than the PDF.

Same shape as `thai.py`, so the same treatment (this.i @7xsnhink, @3i2xqflu). `pdf.clean_pages`
**refuses** an extraction whose CJK share crosses a threshold and names this module, because text
stored after being welded is the failure that looks like success. The working path is here.

The rejoin is conservative in both directions. It joins only where the previous line ends
mid-sentence *by Japanese punctuation* and the next opens with a Japanese character rather than a
bullet or an enumerator; a blank line, a bullet or a terminator ends a join. Welding two unrelated
slide fragments together invents a phrase, which is the same failure pointing the other way.

Hangul is deliberately outside all of this. Korean writes spaces between words, so the English
rejoiner is approximately right there and a gate would refuse documents it can handle.
"""

from __future__ import annotations

import re
from pathlib import Path

from .errors import LawcorpusError
from .normalise import (
    MAX_CJK_RATIO_FOR_LATIN_PATH,
    cjk_ratio,
    looks_cjk,
    normalise_text,
)
from .pdf import raw_pages, strip_repeated_furniture

__all__ = [
    "JapaneseScriptError",
    "JapaneseEmptyError",
    "JapaneseScriptMismatchError",
    "cjk_ratio",
    "clean_japanese_pages",
    "extract_japanese",
    "looks_cjk",
]

# A line ending in one of these is a finished sentence and never absorbs the line below.
TERMINATORS = "。！？!?：:）)」』】"
# A line opening with one of these begins a new block: a bullet, a circled enumerator, a note mark,
# a number. Matching the *opener* is `pdf.py`'s own rule, which transfers; what does not transfer is
# what counts as a finished sentence.
_OPENERS = re.compile(r"^[○●◯◇◆■□▲△▼▽・※＊*\-–—①-⓿㉑-㊿(（\[【\d]")
# Japanese script: kana, kanji, the iteration mark and the long-vowel mark. A line opening in Latin
# is a new block — an ISO reference, a URL, an English gloss.
_JAPANESE = re.compile(r"^[ぁ-んァ-ヶー一-龥々]")

_BLANKS = re.compile(r"\n{3,}")


class JapaneseScriptError(LawcorpusError):
    """A Japanese extraction that must not be stored.

    The root of the family and the prefix a caller matches on, in the shape `thai.py` established:
    `e.input.format.japanese-text.` gathers every way a Japanese extraction can be unusable.
    """

    code = "e.input.format.japanese-text.f"


class JapaneseEmptyError(JapaneseScriptError):
    """No text layer at all — `pdf.py`'s case, restated for this path."""

    code = "e.input.format.japanese-text.empty.f"


class JapaneseScriptMismatchError(JapaneseScriptError):
    """Text routed to this path that is not predominantly CJK, so its rules do not apply."""

    code = "e.input.format.japanese-text.script.f"


def _gate(pages: list) -> None:
    """Refuse before anything is cleaned, so a refusal cannot be mistaken for a cleaning bug."""
    if not any(page.strip() for page in pages):
        raise JapaneseEmptyError(
            "Every page extracted to whitespace, so this PDF has no text layer. It is a scanned "
            "image and needs OCR before it can be quoted. Storing it would put a blank entry in "
            "the corpus that reads like a successful extraction."
        )
    # The ratio alone, with no floor on the character count. `looks_cjk` carries that floor because
    # it answers the opposite question — "should `pdf.py` refuse a document nobody routed here?" —
    # where firing on an English page that quotes 個人情報 would be the failure. A caller reaching
    # this module has chosen the path, so a short Japanese fragment is not suspicious; Latin-
    # dominant text is.
    joined = "\n".join(pages)
    ratio = cjk_ratio(joined)
    if ratio <= MAX_CJK_RATIO_FOR_LATIN_PATH:
        raise JapaneseScriptMismatchError(
            f"This extraction is {ratio:.0%} CJK by letter, which is not Japanese prose. The rules "
            f"here — rejoining with no separator, treating 。 as a sentence end — are wrong for "
            f"Latin text and would run words together, which is the same damage in the other "
            f"direction. Use lawcorpus.pdf.extract, or check that the right document was fetched."
        )


def clean_japanese_pages(pages: list) -> str:
    """Turn extracted pages into one searchable Japanese document.

    The counterpart of `pdf.clean_pages`, sharing its furniture removal and its layout fold and
    replacing its rejoiner.
    """
    pages = list(pages)
    _gate(pages)
    text = normalise_text("\n".join(strip_repeated_furniture(pages)).replace("\f", "\n"))

    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if (
            out
            and stripped
            and out[-1].strip()
            and out[-1].rstrip()[-1] not in TERMINATORS
            and not _OPENERS.match(stripped)
            and _JAPANESE.match(stripped)
        ):
            out[-1] = out[-1].rstrip() + stripped
        else:
            out.append(stripped)
    return _BLANKS.sub("\n\n", "\n".join(out)).strip() + "\n"


def extract_japanese(path, reader=None) -> str:
    """Extract a Japanese PDF with poppler, then clean it by Japanese rules.

    `reader` is injected so the gate and the rejoiner can be tested on text that carries the traps,
    rather than on a PDF that happens to reproduce them.
    """
    return clean_japanese_pages((reader or (lambda p: raw_pages(p)))(Path(path)))
