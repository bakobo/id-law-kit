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

import functools
import itertools
import re
from dataclasses import dataclass

from .errors import LawcorpusError
from .normalise import normalise_text, read_kanji_number
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


def kanji_number(raw: str) -> int:
    """Read a CJK numeral — `五十七` is 57. Japanese article numbers are written this way, always.

    Public because a caller that needs one number has no other way to reach this, and the
    alternative it reaches for is assembling a fake heading (`scan("第五十七条", "第",
    numerals="kanji")[0]`) to get at a private parser. Not Japanese but CJK: the same characters
    number Chinese provisions. Korean statutes use arabic digits and need nothing here. See
    this.i @ooyin3yr.

    Covers 一..九, 十 and 百, which is the whole range article numbering uses. 千 and above are
    refused rather than guessed at, for the reason every oracle here refuses: a reader that invents
    an answer produces an expectation that passes documents it should not.

    The reading itself moved to `normalise.read_kanji_number` when `normalise_query` gained the
    other direction, so that the two cannot disagree about what 五十七 means (@kcznu7jq). This
    keeps the published name and the `OracleError` a corpus repo catches.
    """
    try:
        return read_kanji_number(raw)
    except ValueError as e:
        raise OracleError(
            f"'{e.args[0]}' is not a kanji numeral this reader knows, in '{raw[:20]}'. The article "
            f"range cannot be expanded, and guessing at it would produce an oracle that "
            f"passes everything."
        ) from e


class TruncatedTextError(LawcorpusError):
    """A text whose length is a round number and which stops mid-sentence.

    A sibling of `CompletenessError` under `e.state.missing.`, because it is the same obstacle —
    text we hold and can prove is fragmentary — reached by a different route. @zpycgven's oracle
    cannot see this one: a truncated tail of an instrument whose schedules restart their numbering
    contributes no heading the body has not already used.
    """

    code = "e.state.missing.truncated.f"


# A publisher's own extraction may stop at a cap with no marker: India Code's text bundle for the
# DPDP Rules 2025 ends at exactly 100,000 characters, mid-sentence. Neither half of that is
# evidence on its own — a source may serve an excerpt that ends mid-sentence, and one document in a
# thousand has a round length by chance — but nothing except a cap produces both. See @k4w7rvit.
_ROUND_STEP = 1000
_ROUND_POWER_FLOOR = 4096
# What a document that was allowed to finish ends with, in every script the programme holds.
TERMINATORS = ".!?)]\"'’”。！？」』】"


def _is_round(size: int) -> bool:
    """A length nobody's prose lands on by accident: a whole thousand, or a power of two."""
    return (size >= _ROUND_STEP and size % _ROUND_STEP == 0) or (
        size >= _ROUND_POWER_FLOOR and size & (size - 1) == 0
    )


def check_not_truncated(text: str, what: str = "this text") -> None:
    """Raise if `text` looks like it was cut at a cap rather than allowed to end.

    Returns None on success, so it reads as an assertion at a call site rather than as a predicate
    somebody might forget to test — the shape `Expectation.verify` already uses.
    """
    body = "" if text is None else str(text)
    stripped = body.rstrip()
    if not stripped or not _is_round(len(body)) or stripped[-1] in TERMINATORS:
        return None
    raise TruncatedTextError(
        f"{what} is exactly {len(body)} characters long and ends mid-sentence, on "
        f"'...{stripped[-40:]}'. A round number is a cap rather than a document length, and an "
        f"unmarked cap is invisible to a structure check, because an instrument's trailing "
        f"schedules restart their numbering and contribute no heading the body has not already "
        f"used. Refetch, or extract the source document yourself, before storing this."
    )


@functools.total_ordering
@dataclass(frozen=True, eq=False)
class Provision:
    """A provision number, and the sub-number an amendment inserted under it. @kolycpun.

    Thailand writes `มาตรา ๓๒/๒`, Japan `第六条の二`, common-law drafting `23A`. All three insert a
    provision without renumbering the ones after it, and reading them as their base — which is what
    `scan` did — makes an inserted section indistinguishable from a duplicate heading, so an oracle
    declaring 32 is satisfied by a document carrying only 32/2.

    It **equals and hashes as its own base integer when it has no sub-number**, so an `Expectation`
    declared over ordinary integers — which is every consumer today — needs no change. `separator`
    is how the tradition renders it and takes no part in equality or ordering.
    """

    number: int
    sub: tuple = ()
    separator: str = ""

    def _key(self):
        """Sort key. Each sub-token carries its own kind, so `23 < 23A` and `6/2 < 6/10`."""
        return (
            self.number,
            tuple((1, t, "") if isinstance(t, int) else (2, 0, t) for t in self.sub),
        )

    def __eq__(self, other) -> bool:
        if isinstance(other, Provision):
            return self._key() == other._key()
        if isinstance(other, int):
            return not self.sub and self.number == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.number) if not self.sub else hash(self._key())

    def __lt__(self, other) -> bool:
        if isinstance(other, int):
            other = Provision(other)
        if not isinstance(other, Provision):
            return NotImplemented
        return self._key() < other._key()

    def __index__(self) -> int:
        """The base, so `int()` and `range()` reach through to it."""
        return self.number

    def __str__(self) -> str:
        return str(self.number) + "".join(f"{self.separator}{t}" for t in self.sub)


def _letter_sub(raw: str) -> tuple:
    return (raw,) if raw else ()


def _split_sub(separator: str, read):
    def parse(raw: str) -> tuple:
        return tuple(read(part) for part in (raw or "").split(separator) if part)

    return parse


# Per numeral system: how a provision number is spelled, how to read it, how a sub-number is
# spelled under it, how to read that, and how the tradition renders one. A Japanese article number
# is followed by 条, which is what bounds it.
#
# Korea's `제24조의2` is deliberately absent: matching it needs `조` in the pattern, and the arabic
# entry is the one every Latin-script corpus uses. A Korean branch article still reads as its base,
# as it always did. @kolycpun.
_NUMERALS = {
    "arabic": (r"(\d{1,4})", _arabic, r"([A-Z]{1,3})?", _letter_sub, ""),
    "roman": (r"([IVXLCDMivxlcdm]{1,9})\b", _roman, "()", _letter_sub, ""),
    "kanji": (
        r"([一二三四五六七八九十百]{1,6})条",
        kanji_number,
        r"((?:の[一二三四五六七八九十百]{1,6})*)",
        _split_sub("の", kanji_number),
        "の",
    ),
    "thai": (r"([๐-๙\d]{1,4})", _thai, r"((?:/[๐-๙\d]{1,4})*)", _split_sub("/", _thai), "/"),
}


def provision(raw: str) -> Provision:
    """Read the form a table of contents hands you — `23A`, `32/2`, `17` — as a `Provision`.

    A TOC gives a corpus repo strings, and an `Expectation` needs values that compare against what
    `scan` returns. Refuses anything it cannot read, for the reason every oracle here refuses:
    guessing produces an expectation that passes documents it should not.
    """
    text = ("" if raw is None else str(raw)).strip()
    match = re.fullmatch(r"(\d{1,4})(?:([A-Z]{1,3})|((?:/\d{1,4})+))?", text)
    if not match:
        raise OracleError(
            f"'{text[:20]}' is not a provision number this package reads. Expected a number, "
            f"optionally with a letter suffix ('23A') or a slash sub-number ('32/2')."
        )
    base, letters, slashed = match.groups()
    sub = _letter_sub(letters or "") or _split_sub("/", _arabic)(slashed or "")
    return Provision(int(base), sub, "" if letters else "/")


def _compile(pattern: str, name: str, consequence: str):
    try:
        return re.compile(pattern)
    except re.error as e:
        raise OracleError(
            f"The {name} '{str(pattern)[:40]}' is not a regular expression: {e}. {consequence}"
        ) from e


def _window(text: str, start: str, boundary: str) -> str:
    """The main body: from the first line matching `start` to the first matching `boundary`.

    `start` fails closed when it does not match. An SSO PDF prints its own table of contents before
    the body, so a truncated extraction still lists its missing tail on its own index — scanning
    the whole text would let that index vouch for sections the body does not contain, which is the
    one thing this module exists to stop. @q5fyyb4q.
    """
    lines = text.splitlines(keepends=True)
    if start:
        rx = _compile(
            start,
            "start",
            "It marks where the main body begins, so an unusable one would silently scan the "
            "instrument's own contents page as though it were the text.",
        )
        opening = next((n for n, line in enumerate(lines) if rx.search(line)), None)
        if opening is None:
            raise OracleError(
                f"No line matches the declared body opener '{str(start)[:40]}', so the body cannot "
                f"be separated from the front matter. Checking the extraction against the whole "
                f"text would let the contents page vouch for provisions the body may not carry. "
                f"Read the extraction by hand before storing it."
            )
        lines = lines[opening:]
    if boundary:
        rx = _compile(
            boundary,
            "boundary",
            "It marks where the main body ends, so an unusable one would silently scan the "
            "schedules too.",
        )
        lines = list(itertools.takewhile(lambda line: not rx.search(line), lines))
    return "".join(lines)


def scan(
    text: str,
    label: str,
    numerals: str = "arabic",
    boundary: str = "",
    terminator: str = "",
    start: str = "",
) -> list:
    """Every provision number appearing as a heading, in document order.

    **Line-anchored, deliberately.** `มาตรา ๑๗๕` inside a sentence is a cross-reference to another
    instrument: Phase 0 saw an unanchored scan of one Thai Royal Decree return 38 distinct numbers
    spanning 1..175, of which the Decree contains a handful. Counting those invents provisions and
    then reports them missing.

    Duplicates are kept, because a heading appearing twice is itself a signal — a running header
    landing mid-list produced exactly that in UU 28/2014.

    **A sub-number is read, not collapsed onto its base.** `มาตรา ๓๒/๒`, `第六条の二` and `Pasal 13A`
    are inserted provisions, and reading them as 32, 6 and 13 makes an insertion indistinguishable
    from a duplicate heading. Each is returned as a `Provision`, which equals its own base integer
    when it has no sub-number. See @kolycpun.

    `boundary` is a regex marking the line where the main body ends; the scan stops there.
    Japanese 附則, a UK schedule, a French annexe and a US appendix all restart their numbering, so
    an unbounded scan reads a correct document as out of order. Bounding rather than tolerating a
    descending step matters twice: a descending step is also what an OCR misread of a heading looks
    like, and a provision surviving only inside a schedule must not satisfy a declaration about the
    main body. See this.i @qd6p2f3x.

    `start` is its mirror, marking where the body begins, for a document that prints its own table
    of contents first. `terminator` is a regex the number must be followed by, which is what makes
    a **label-less** scan safe: a Singapore section heading is a bare `3.—(1)`, and `^\\s*\\d+`
    alone would match most of a document. An empty label with no terminator is therefore refused.
    See @q5fyyb4q.
    """
    if numerals not in _NUMERALS:
        raise OracleError(
            f"'{str(numerals)[:20]}' is not a numeral system this package reads. Use one of: "
            f"{', '.join(sorted(_NUMERALS))}."
        )
    if not label and not terminator:
        raise OracleError(
            "A scan with no label needs a terminator — a pattern the number must be followed by, "
            "such as r'\\.' for a heading written '23A.'. Without one this matches every line "
            "opening with a digit, and an oracle that matches everything passes everything."
        )
    pattern, read, sub_pattern, read_sub, separator = _NUMERALS[numerals]
    rx = re.compile(
        rf"^[ \t]*{re.escape(label)}[ \t　]*{pattern}{sub_pattern}{terminator}", re.MULTILINE
    )
    return [
        Provision(read(m.group(1)), read_sub(m.group(2) or ""), separator)
        for m in rx.finditer(_window(text, start, boundary))
    ]


@dataclass(frozen=True)
class Expectation:
    """What an independent source says this instrument contains."""

    label: str
    numbers: tuple
    numerals: str = "arabic"
    source: str = ""
    boundary: str = ""
    terminator: str = ""
    start: str = ""

    @classmethod
    def over(
        cls,
        label,
        numbers,
        numerals: str = "arabic",
        source: str = "",
        boundary: str = "",
        terminator: str = "",
        start: str = "",
    ) -> "Expectation":
        return cls(
            label=label,
            numbers=tuple(numbers),
            numerals=numerals,
            source=source,
            boundary=boundary,
            terminator=terminator,
            start=start,
        )

    def verify(self, text: str) -> None:
        """Raise unless `text` carries every declared provision, in order.

        Returns None on success, so it reads as an assertion at a call site rather than as a
        predicate somebody might forget to test.
        """
        found = scan(
            text, self.label, self.numerals, self.boundary, self.terminator, self.start
        )
        present = set(found)
        missing = [n for n in self.numbers if n not in present]
        last = max(found) if found else None
        tail = [n for n in missing if last is None or n > last]
        interior = [n for n in missing if n not in set(tail)]
        out_of_order = found != sorted(found)
        if not missing and not out_of_order:
            return None

        if self.numbers:
            parts = [
                f"Refusing this extraction: it does not match the structure declared for it. "
                f"{len(present & set(self.numbers))} of {len(self.numbers)} declared "
                f"{self._kind} provisions are present."
            ]
        else:
            # A partial instrument declares nothing, so "0 of 0 are present" would read as a
            # complete loss rather than as the only check there was.
            parts = [
                f"Refusing this extraction: nothing was declared about which {self._kind} "
                f"provisions it should carry, because the source serves only part of this "
                f"instrument — but the headings it does carry are not in ascending order."
            ]
        if interior:
            parts.append(
                f"Missing from the middle, with their neighbours present, so the text was damaged "
                f"rather than cut short: {self._name(interior)}."
            )
        if tail:
            where = f"{self.label} {last}".strip() if last is not None else "nothing at all"
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

    @property
    def _kind(self) -> str:
        """What to call these provisions in a message. Singapore's carry no label at all."""
        return f"'{self.label}'" if self.label else "unlabelled"

    def _name(self, numbers) -> str:
        return ", ".join(f"{self.label} {n}".strip() for n in numbers)


_TOC_GROUP = re.compile(r"\(([^)]*)\)")
_TOC_ARTICLE = re.compile(r"第([^条()]{1,12})条")

# 「第十条から第十五条まで　削除」 — consecutive repealed articles collapsed into a single heading. It
# is ordinary Japanese drafting and it defeats a heading scan, which reads the first number and
# then reports the other five missing.
_COLLAPSED_TITLE = re.compile(
    r"^第([一二三四五六七八九十百]{1,6})条から第([一二三四五六七八九十百]{1,6})条まで"
)

# The `<TOC>` this reads is produced by `japan-id/tools/egov.py`, a 法令標準XML renderer that stays
# in that repo until a second consumer of e-Gov's schema exists. ~43gp
#
# Where a Japanese instrument's main body ends. 附則 restarts at 第一条 in every supplementary block,
# and an Act carries one per amending act. The ideographic space is optional because e-Gov writes
# the heading as 「附　則」, letter-spacing the word (@ux7izhdj); the trailing form matches a renderer
# that prefixes supplementary lines with a labelled 附則(令和七年法律第三十八号).
SUPPLEMENTARY_BOUNDARY = r"^附[ \t　]?則"

# Korea's equivalent. 부칙 restarts at 제1조 for the same reason 附則 does.
KOREAN_SUPPLEMENTARY_BOUNDARY = r"^부[ \t]?칙"


def _collapsed_articles(article_titles) -> set:
    """The article numbers a collapsed heading stands for *after* the first, which is present.

    Taken from the instrument's own `<ArticleTitle>` values, so it is still the publisher declaring
    the shape. The alternative — emitting five headings the source does not contain so that the
    count comes out — is an oracle editing its own evidence.
    """
    collapsed = set()
    for title in article_titles or ():
        match = _COLLAPSED_TITLE.match(" ".join(str(title).split()))
        if match:
            first, last = (kanji_number(g) for g in match.groups())
            collapsed.update(range(first + 1, last + 1))
    return collapsed


def japanese_article_range(toc: str, article_titles=(), partial: bool = False) -> Expectation:
    """Japan's oracle, which ships inside every instrument.

    e-Gov serves a `<TOC>` whose `<ArticleRange>` values state the article span of each chapter —
    `（第一条―第六条の二）（第七条―第十六条）…`. It is authored by the publisher rather than by our
    parser, which is what makes it independent evidence and a better oracle than the California OAL
    notice: it needs no second document.

    `―` (U+2015) joins the ends of a range; `・` (U+30FB) lists two articles. Branch articles
    (枝番, 第六条の二) read as their base, so the range ends at article 6.

    Two shapes made a correct document read as damaged, and both are handled here rather than in
    each Japanese corpus's harvester (this.i @y3aozl55):

    - `article_titles` — pass the instrument's `<ArticleTitle>` values and a collapsed repeal
      range, 「第十条から第十五条まで　削除」, drops the articles it stands for from the expectation.
    - `partial` — set it for a `<MainProvision Extract="true">` response, where e-Gov serves part of
      an instrument whose table of contents still describes the whole. The declared set is dropped
      and **only ordering is checked**, which is nearly nothing and is still worth running: order is
      what caught a renderer dropping sub-item numbers, where 「第九条第四号に掲げる…」 read as article
      9 arriving after article 10.
    """
    numbers = set()
    for group in _TOC_GROUP.finditer(normalise_text(toc)):
        body = group.group(1)
        found = [kanji_number(m.group(1)) for m in _TOC_ARTICLE.finditer(body)]
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

    source = "the instrument's own <TOC><ArticleRange>, authored by e-Gov"
    if partial:
        return Expectation.over(
            "第",
            (),
            numerals="kanji",
            source=(
                "nothing: e-Gov serves this instrument in part (MainProvision Extract=\"true\") "
                "while its <TOC> describes the whole, so only the order of the articles present "
                "is checked. This expectation cannot see a missing provision — cite the item as "
                "（抄） and record it as a known gap."
            ),
            boundary=SUPPLEMENTARY_BOUNDARY,
        )

    collapsed = _collapsed_articles(article_titles)
    if collapsed:
        kept = sorted(n for n in numbers if n not in collapsed)
        source = (
            f"{source}, less {len(numbers) - len(kept)} article(s) the instrument itself collapses "
            f"into a 「…から…まで　削除」 heading"
        )
        numbers = kept

    return Expectation.over(
        "第",
        sorted(numbers),
        numerals="kanji",
        source=source,
        boundary=SUPPLEMENTARY_BOUNDARY,
    )


def korean_gapless(text: str) -> Expectation:
    """Korea's oracle, derived from the extraction itself.

    Korean statute numbering is gapless from 1 to the maximum, because a repealed article survives
    as a `삭제` placeholder rather than being removed. Phase 0 held it 7 for 7, across instruments
    from 26 to 166 articles. Branch articles (제24조의2) read as their base and do not extend the
    range.

    Being self-derived, it catches an interior gap and is **blind to a truncated tail** — a cut
    tail simply lowers the maximum. Use it as one of two checks where the tail matters.

    Bounded at 부칙, Korea's supplementary provisions, which restart at 제1조 the way Japan's 附則 do
    (@qd6p2f3x). Derivation and verification use the same boundary, or the expectation would be
    built from a different document than the one it checks.
    """
    found = scan(text, "제", numerals="arabic", boundary=KOREAN_SUPPLEMENTARY_BOUNDARY)
    if not found:
        raise OracleError(
            "No 제N조 article headings were found, so the gapless-numbering oracle has nothing to "
            "work from. Either the extraction failed outright or this is not a Korean statute; "
            "returning an empty expectation would pass every document."
        )
    return Expectation.over(
        "제",
        range(1, max(found).number + 1),
        source=(
            "Korean gapless article numbering, where a repealed article survives as a 삭제 "
            "placeholder. Derived from the extraction, so it cannot see a truncated tail."
        ),
        boundary=KOREAN_SUPPLEMENTARY_BOUNDARY,
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
