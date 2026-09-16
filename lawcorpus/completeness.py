"""Does this extraction contain the whole instrument?

`method.md` §6's existing guard refuses an extraction that is *empty*. Indonesia produced the case
it cannot see. UU 27/2022 — the Personal Data Protection Law — is fifty 1-bit CCITT images at
400 dpi with a non-embedded OCR font. It extracts to 52 KB of entirely plausible Indonesian, it
passes every emptiness check, and **Pasal 22, 70 and 72 and the whole of BAB XI–XII are not in it**.
The positive control that found this is the only reason anyone knows:

    'Pasal 22' (target)  : 0        'Pasal 21' (control) : 3
    'Pasal 23' (control) : 2        'Pasal'    (tool)    : 199

A corpus exists to support negative claims — "the law nowhere requires X". A missing provision
manufactures one out of an OCR failure, and nothing about the output looks wrong. So an extraction
is compared against a **declared expected structure** and **refused** on a mismatch, the way the
California regulations harvest aborts against the Office of Administrative Law's notice rather than
accept a chapter that is short (`method.md` §2). See `this.i` @zpycgven.

Declaring a structure by hand for every instrument is the cost that would stop this being used, so
three sources that state their own shape are wired in — Japan's `<TOC><ArticleRange>`, Korea's
gapless numbering, and Indonesia's `status_hukum`. See @oym7gzus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import LawcorpusError
from .normalise import normalise_text
from .validity import Validity


class CompletenessError(LawcorpusError):
    """An extraction that is missing provisions the source says it should carry.

    `state.missing` per `dev/standards/error-codes.md`: this is text we hold and can *prove* is
    fragmentary, which the standard distinguishes from text we merely failed to fetch.
    """

    code = "e.state.missing.provisions.f"


class OracleError(LawcorpusError):
    """A declared structure that cannot be read, so nothing can be checked against it.

    Separate from `CompletenessError` because the remediation differs: there, re-extract the
    document; here, the oracle itself is wrong, and treating it as a pass would make every
    extraction complete.
    """

    code = "e.input.format.oracle.f"


_KANJI_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_ROMAN_DIGITS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _arabic(raw: str) -> int:
    return int(raw)


def _thai(raw: str) -> int:
    return int("".join(str(ord(ch) - 0x0E50) if "๐" <= ch <= "๙" else ch for ch in raw))


def _roman(raw: str) -> int:
    total, previous = 0, 0
    for ch in reversed(raw.upper()):
        value = _ROMAN_DIGITS[ch]
        total = total - value if value < previous else total + value
        previous = max(previous, value)
    return total


def _kanji(raw: str) -> int:
    """Japanese article numbers are written in kanji, always. `第57条` returns zero hits."""
    total, current, hundreds = 0, 0, 0
    for ch in raw:
        if ch in _KANJI_DIGITS:
            current = _KANJI_DIGITS[ch]
        elif ch == "十":
            total += (current or 1) * 10
            current = 0
        elif ch == "百":
            hundreds += (current or 1) * 100
            total, current = 0, 0
        else:
            raise OracleError(
                f"'{ch}' is not a kanji numeral this reader knows, in '{raw[:20]}'. The article "
                f"range cannot be expanded, and guessing at it would produce an oracle that "
                f"passes everything."
            )
    return hundreds + total + current


# Per numeral system: how a provision number is spelled, and how to read it. A Japanese article
# number is followed by 条, which is what bounds it; a branch article (第六条の二) therefore reads
# as its base, article 6, rather than as article 62.
_NUMERALS = {
    "arabic": (r"(\d{1,4})", _arabic),
    "roman": (r"([IVXLCDMivxlcdm]{1,9})\b", _roman),
    "kanji": (r"([一二三四五六七八九十百]{1,6})条", _kanji),
    "thai": (r"([๐-๙\d]{1,4})", _thai),
}


def scan(text: str, label: str, numerals: str = "arabic") -> list:
    """Every provision number appearing as a heading, in document order.

    **Line-anchored, deliberately.** `มาตรา ๑๗๕` inside a sentence is a cross-reference to another
    instrument: Phase 0 saw an unanchored scan of one Thai Royal Decree return 38 distinct numbers
    spanning 1..175, of which the Decree contains a handful. Counting those invents provisions and
    then reports them missing.

    Duplicates are kept, because a heading appearing twice is itself a signal — a running header
    landing mid-list produced exactly that in UU 28/2014.
    """
    if numerals not in _NUMERALS:
        raise OracleError(
            f"'{str(numerals)[:20]}' is not a numeral system this package reads. Use one of: "
            f"{', '.join(sorted(_NUMERALS))}."
        )
    pattern, read = _NUMERALS[numerals]
    rx = re.compile(rf"^[ \t]*{re.escape(label)}[ \t　]*{pattern}", re.MULTILINE)
    return [read(m.group(1)) for m in rx.finditer(text)]


@dataclass(frozen=True)
class Expectation:
    """What an independent source says this instrument contains."""

    label: str
    numbers: tuple
    numerals: str = "arabic"
    source: str = ""

    @classmethod
    def over(cls, label, numbers, numerals: str = "arabic", source: str = "") -> "Expectation":
        return cls(label=label, numbers=tuple(numbers), numerals=numerals, source=source)

    def verify(self, text: str) -> None:
        """Raise unless `text` carries every declared provision, in order.

        Returns None on success, so it reads as an assertion at a call site rather than as a
        predicate somebody might forget to test.
        """
        found = scan(text, self.label, self.numerals)
        present = set(found)
        missing = [n for n in self.numbers if n not in present]
        last = max(found) if found else None
        tail = [n for n in missing if last is None or n > last]
        interior = [n for n in missing if n not in set(tail)]
        out_of_order = found != sorted(found)
        if not missing and not out_of_order:
            return None

        parts = [
            f"Refusing this extraction: it does not match the structure declared for it. "
            f"{len(present & set(self.numbers))} of {len(self.numbers)} declared "
            f"'{self.label}' provisions are present."
        ]
        if interior:
            parts.append(
                f"Missing from the middle, with their neighbours present, so the text was damaged "
                f"rather than cut short: {self._name(interior)}."
            )
        if tail:
            where = f"{self.label} {last}" if last is not None else "nothing at all"
            parts.append(
                f"The text ends at {where}, so this tail is missing: {self._name(tail)}."
            )
        if out_of_order:
            parts.append(
                f"Headings also appear out of order ({self._name(found)}), which is what an OCR "
                f"misread of a heading looks like — UU 27/2022 has a BAB XI reading as a bare I "
                f"between IX and X."
            )
        if self.source:
            parts.append(f"The structure was declared by: {self.source}.")
        parts.append(
            "An extraction that is full and short is the failure this check exists to catch, and "
            "it reads as success. Re-extract — for a scanned instrument, OCR from the page images "
            "rather than trusting the embedded text layer — before storing anything."
        )
        raise CompletenessError(" ".join(parts))

    def _name(self, numbers) -> str:
        return ", ".join(f"{self.label} {n}" for n in numbers)


_TOC_GROUP = re.compile(r"\(([^)]*)\)")
_TOC_ARTICLE = re.compile(r"第([^条()]{1,12})条")


def japanese_article_range(toc: str) -> Expectation:
    """Japan's oracle, which ships inside every instrument.

    e-Gov serves a `<TOC>` whose `<ArticleRange>` values state the article span of each chapter —
    `（第一条―第六条の二）（第七条―第十六条）…`. It is authored by the publisher rather than by our
    parser, which is what makes it independent evidence and a better oracle than the California OAL
    notice: it needs no second document.

    `―` (U+2015) joins the ends of a range; `・` (U+30FB) lists two articles. Branch articles
    (枝番, 第六条の二) read as their base, so the range ends at article 6.
    """
    numbers = set()
    for group in _TOC_GROUP.finditer(normalise_text(toc)):
        body = group.group(1)
        found = [_kanji(m.group(1)) for m in _TOC_ARTICLE.finditer(body)]
        if not found:
            continue
        if "―" in body or "—" in body or "-" in body:
            numbers.update(range(min(found), max(found) + 1))
        else:
            numbers.update(found)
    if not numbers:
        raise OracleError(
            "This TOC declares no article ranges, so it cannot verify an extraction. An empty "
            "expectation would silently pass every document, which is worse than having no oracle "
            "at all — check that the <TOC> element was retrieved whole."
        )
    return Expectation.over(
        "第",
        sorted(numbers),
        numerals="kanji",
        source="the instrument's own <TOC><ArticleRange>, authored by e-Gov",
    )


def korean_gapless(text: str) -> Expectation:
    """Korea's oracle, derived from the extraction itself.

    Korean statute numbering is gapless from 1 to the maximum, because a repealed article survives
    as a `삭제` placeholder rather than being removed. Phase 0 held it 7 for 7, across instruments
    from 26 to 166 articles. Branch articles (제24조의2) read as their base and do not extend the
    range.

    Being self-derived, it catches an interior gap and is **blind to a truncated tail** — a cut
    tail simply lowers the maximum. Use it as one of two checks where the tail matters.
    """
    found = scan(text, "제", numerals="arabic")
    if not found:
        raise OracleError(
            "No 제N조 article headings were found, so the gapless-numbering oracle has nothing to "
            "work from. Either the extraction failed outright or this is not a Korean statute; "
            "returning an empty expectation would pass every document."
        )
    return Expectation.over(
        "제",
        range(1, max(found) + 1),
        source=(
            "Korean gapless article numbering, where a repealed article survives as a 삭제 "
            "placeholder. Derived from the extraction, so it cannot see a truncated tail."
        ),
    )


_STATUS_HUKUM = {
    "berlaku": Validity.IN_FORCE,
    "sebagian": Validity.AMENDED,
    "dicabut": Validity.REPEALED,
}


def validity_from_status_hukum(raw) -> Validity:
    """Indonesia's oracle: `validity`, given by the source rather than hand-curated.

    `jdih.setneg.go.id` carries `status_hukum` on every record, and it maps onto `taxonomy.md` §3
    directly. Very few sources hand you this, and `taxonomy.md` otherwise assumes the field is
    curated by hand and lags.

    An unknown token is refused rather than defaulted, for the reason the field exists: a wrong
    validity is more dangerous than an absent one. Note also that Phase 0 saw two endpoints on this
    host disagree — the search endpoint reporting `sebagian` where `/status` returned an empty
    amendment graph — so this mapping is an input to curation, not a substitute for it.
    """
    token = ("" if raw is None else str(raw)).strip().lower()
    if token not in _STATUS_HUKUM:
        legal = ", ".join(sorted(_STATUS_HUKUM))
        raise OracleError(
            f"'{token[:40]}' is not a status_hukum value this package maps. Known values are: "
            f"{legal}. Record the validity by hand rather than letting an unrecognised status "
            f"default to in-force."
        )
    return _STATUS_HUKUM[token]
