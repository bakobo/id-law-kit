"""PDF text extraction, via poppler's `pdftotext`.

The last resort of the three renderers here, and the only one whose output cannot be trusted
structurally. Formex and CAML are markup — what comes out is what the publisher put in. A PDF is a
page description, so extraction has to *infer* a reading order and it interleaves furniture into
the middle of sentences:

    ...for purposes of this definition, to "substantially replace human
    CA PRIVACY PROTECTION AGENCY - TEXT OF REGULATIONS
    Page 1 of 127
    decisionmaking" means a business uses the technology's output...

Nothing about that looks broken, and it both greps wrong and reads wrong. So furniture removal is
not cosmetic: it is the difference between a corpus and a pile of pages.

Requires `pdftotext` (poppler-utils). It is used rather than a pure-Python library because its
layout analysis on multi-column legal documents is markedly better, and because a bad extraction
is worse than no extraction — it looks like text.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from .errors import LawcorpusError
from .normalise import DIGITS, fold_digits, looks_cjk, normalise_text
from .textloss import refuse_fabrication

# How many lines at each edge of a page a page number may be looked for in. The window says where
# a page number would be if there were one; it is not evidence that the line found there is one.
# That evidence is a numbering run — see `_numbering_offsets` and @fu7njgwq.
EDGE_LINES = 3
# How many lines at each edge the two rules that prove furniture from repetition may reach. They
# carry their own evidence and do not need position to supply it, which is what lets them see past
# a scanner's emblem: `indonesia-id` measured Perpres 95/2018 OCR'ing the Garuda into three to six
# lines of noise, landing the real running head at line index 5 to 7 and outside a window of 3.
#
# Eight was one sample when it was chosen. Measured since over 24 PDFs from two corpora, the
# deepest rank a *sound* document needs is 5, several want 4, and the Garuda document itself gains
# one further line only at a window of 12; everything deeper in the sample is a watermarked PDF
# whose glyph fragments pad the head of the page, which is not a document this package can store.
# So 8 sits above every sound case with margin and below the point where it would be chasing a
# watermark, and it stays a single default rather than becoming a per-source knob nobody has the
# evidence to set. See @zga5midk.
FURNITURE_LINES = 8
# A line must appear at the same edge on at least this fraction of pages to count as furniture.
FURNITURE_THRESHOLD = 0.6
# A *shape* must recur on at least this fraction of the pages it spans, which is lower, and the
# difference is forced rather than tuned. Printed legal publishing mirrors its running heads
# between recto and verso — SSO puts the page number on the left of an even page and the right of
# an odd one — so a mirrored header is two shapes each appearing on about half the pages it runs
# through. Mirrored shapes are counted together (@lbqi475m), so the margin this leaves is for a
# title page and a landscape insert rather than for the mirror. See @ly7tho4y.
SHAPE_THRESHOLD = 0.4
# No shape is furniture on the evidence of one page, whatever the fractions come to.
MIN_FURNITURE_PAGES = 2

_PAGE_NUMBER = re.compile(
    r"^\s*(?:page\s+)?\d+\s*(?:of\s+\d+)?\s*$|^\s*-\s*\d+\s*-\s*$", re.IGNORECASE
)
# A run of digits in any numeral system the package declares, so a Thai page number is a field
# here and not a word.
_DIGIT_RUN = re.compile(f"[{re.escape(DIGITS)}]+")
_FIELD = "\x00"
_BLANKS = re.compile(r"\n{3,}")
_MULTISPACE = re.compile(r"[ \t]{2,}")
# Structural openers: a line starting with one of these begins a new block and must never be
# joined to the line above. Everything else that follows an unterminated line is a wrapped
# sentence. Matching on the *opener* rather than on "is it lower case" matters because legal
# prose wraps before capitalised proper nouns constantly ("...means the California\nPrivacy
# Protection Agency"), and a lower-case-only rule leaves those split.
# One entry per drafting tradition, because the original list was number-leading throughout and
# that is common-law drafting rather than a universal: Indonesian, Thai and Japanese all put the
# label first. Substituting the common-law entry alone for `indonesia-id`'s own pattern refuses 8
# of that repo's 11 stored instruments. A tradition is added here in one line and both consumers
# of the idea — the rejoiner and the furniture rule — gain it together. See @zzqzaku4.
#
# Written for `re.VERBOSE`, so a literal space must be escaped or live inside a character class.
STRUCTURAL_OPENERS = {
    "common-law": r"""
        §                      # section sign
      | \([a-zA-Z0-9]{1,4}\)        # (a) (1) (iii) (A)
      # 1.  23A.  16O.  — see @zr3b5ll2. The lookahead is @avcicqvb: a heading is `27.—(1)` or
      # `30. The Controller`, so the stop is followed by an em-dash or by the provision, while a
      # year wrapped onto a line of its own is followed by nothing. Without it `1994.` opens a
      # block and `completeness.scan` reads it as section 1994, which refused a correct extraction
      # in 4 of `singapore-id`'s 20 instruments. The `indonesian` entry below already required
      # its trailing space; this entry was the inconsistent one. A date opening a line is still
      # read as an opener, and the shape that would separate it from a decimal paragraph number
      # has not been found: ~7dgz.
      | \d+[A-Z]{0,2}\.(?=[ \t]*\S)
      | ARTICLE\b | CHAPTER\b | DIVISION\b | TITLE\b
      | Note:
      | [A-Z][A-Z ’'\-]{6,}\s*$   # an all-caps heading line
    """,
    # `indonesia-id/tools/indonesian.py`, measured over eleven instruments. `BAB` is the case that
    # settles the design: the all-caps rule above matches `BAB XVII` and fails `BAB I`, which is
    # the worst shape of all, because it welds exactly the chapters an ordering check would catch.
    "indonesian": r"""
        BAB\b | BAGIAN\b | Bagian\b | PARAGRAF\b | Paragraf\b
      | PASAL\b | Pasal\b
      # A label, and nothing a word can be. `[a-z0-9]{1,3}\.` used to stand here and matched
      # `out. `, so an English sentence wrapping after "choice to opt-" opened a block and one of
      # `ccpa`'s regulation sections was split down the middle; `in.` and `to.` qualify too. A
      # label is a single letter, or a short run carrying a digit — which keeps this corpus's
      # OCR-mangled numbers (`t4.` for `14.`, `2o8.` for `208.`) and admits no English word.
      # The space after the stop is what keeps a decimal out. See @o3dodx44.
      # The lookahead is @avcicqvb's, which the common-law entry above already carries: a label is
      # followed by the thing it labels, and `2017.` alone on a line is a wrapped year.
      | [a-z]\.(?=[ \t]+\S)                       # a.  b.
      | [a-z0-9]{0,2}\d[a-z0-9]{0,2}\.(?=[ \t]+\S)   # 1.  12.  123.  t4.  284a.
      | MEMUTUSKAN | MENETAPKAN | Menimbang | Mengingat | Menetapkan
      | PRESIDEN\b | UNDANG-UNDANG\b | PERATURAN\b | PENJELASAN\b | LAMPIRAN\b
    """,
    # The label `thailand-id` already hands `completeness.scan`, plus the divisions above a
    # section. No `\b` anywhere: Thai writes no word boundaries, and a `\b` there under-counts
    # partially, which reads like a successful search.
    "thai": r"""
        มาตรา       # section
      | หมวด             # chapter
      | ส่วน                  # part
      | ภาค                   # book
      | ลักษณะ # title
    """,
    # 第N条 and the divisions above and below it, in both numeral systems, because `japan-id`'s
    # two corpora spell the same provision 第十八条 and 第18条. 附則 ends the main body.
    "japanese": r"""
        第[一二三四五六七八九十百〇\d]{1,6}
        [条章節款編項号]
      | 附[ \t　]?則
    """,
}


class UnknownTraditionError(LawcorpusError):
    """A drafting tradition that is not in `STRUCTURAL_OPENERS`.

    `input.format` rather than a leaf of our own: it is decidable by inspecting the argument
    alone, which is the standard's `input` boundary, and the obstacle is a declared token this
    package cannot read — the same obstacle as `e.input.format.oracle.f`.
    """

    code = "e.input.format.tradition.f"


def structural_pattern(*traditions):
    """The compiled opener pattern for the named traditions, or for every one of them.

    Every tradition by default rather than a `traditions=` argument the caller must get right,
    for @amdvdsah's reason: a document does not reliably declare its tradition and the caller
    frequently does not know either. The cost of carrying every tradition over an English corpus
    is a line opening `Pasal` or a Thai section label not being rejoined, which does not arise;
    the cost of defaulting to common-law is `indonesia-id`'s 8 refusals of 11. See @zzqzaku4.
    """
    names = traditions or tuple(STRUCTURAL_OPENERS)
    unknown = [n for n in names if n not in STRUCTURAL_OPENERS]
    if unknown:
        raise UnknownTraditionError(
            f"No drafting tradition named {', '.join(repr(n) for n in unknown)}. Known traditions "
            f"are: {', '.join(sorted(STRUCTURAL_OPENERS))}. Add one to STRUCTURAL_OPENERS rather "
            f"than passing a pattern, so the rejoiner and the furniture rule gain it together."
        )
    return re.compile(
        "^\\s*(?:" + "|".join(STRUCTURAL_OPENERS[n] for n in names) + ")", re.VERBOSE
    )


_STRUCTURAL = structural_pattern()
# A line that ends mid-sentence: no terminal punctuation.
_UNTERMINATED = re.compile(r"[^.:;?!\)\]\u2019\"]\s*$")


class PdfError(LawcorpusError):
    """A PDF that will not extract, or a missing extractor."""

    code = "BK_PDF_EXTRACT"


def _edge_lines(page: str, depth: int) -> list:
    """The lines at the top and bottom of one page, stripped, with no line counted twice.

    Blank lines do not count toward the depth — a page that opens with three blank lines has not
    used up its window — and `_line_ranks` below reads the page the same way, so the window means
    one thing in the counting and another nowhere. The head and tail slices must not overlap, or a
    short page counts its own lines twice and a line appearing once crosses the threshold on its
    own.
    """
    lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
    return lines[:depth] + lines[max(depth, len(lines) - depth):]


def _line_ranks(lines: list) -> tuple:
    """Each raw line's position among the non-blank lines, and how many there are.

    A blank line gets no rank and is never furniture. Returned rather than recomputed per rule so
    that both windows measure from the same origin. See @kbdz5bmq.
    """
    filled = [index for index, line in enumerate(lines) if line.strip()]
    return {index: rank for rank, index in enumerate(filled)}, len(filled)


def _page_marks(pages: list) -> dict:
    """Every edge line that is nothing but a number, keyed by page and line, with its value.

    Built once and consulted by both halves of the page-number rule — the run-finding below and
    the strip loop — so the window cannot come to mean one thing in the counting and another in
    the dropping. That disagreement is the defect @kbdz5bmq found in the version before it.
    """
    marks = {}
    for index, page in enumerate(pages):
        lines = page.splitlines()
        ranks, filled = _line_ranks(lines)
        for position, line in enumerate(lines):
            rank = ranks.get(position)
            if rank is None or not (rank < EDGE_LINES or rank >= filled - EDGE_LINES):
                continue
            stripped = line.strip()
            if _PAGE_NUMBER.match(stripped):
                marks[(index, position)] = int(fold_digits(_DIGIT_RUN.search(stripped).group()))
    return marks


def _numbering_offsets(pages: list, marks: dict) -> set:
    """The offsets at which this document's page numbers march with its pages.

    A page number is the page's index plus a constant — 1 for a document numbered from its first
    page, -24 for the explanatory part that restarts after it — so a real numbering run is a
    **cohort** of edge numbers sharing one offset. Three things must hold before the cohort is
    believed, and each was refuted on its own (@fu7njgwq):

    * enough pages carry it, which is `MIN_FURNITURE_PAGES`, the floor every rule here uses;
    * two of those pages are **adjacent**, because numbering advances one page at a time and two
      numbers agreeing across a gap agree by coincidence;
    * the offset is no larger than the document is long, because a 25-page instrument does not
      begin at printed page 1995 — which is what `2016` and `2017`, wrapped onto lines of their
      own on adjacent pages of `singapore-id`'s NRA 1965 RG 2, would otherwise claim.

    Two footnote markers on adjacent pages, one greater than the other, still satisfy all three:
    ~6mas. Without this the rule deletes on position alone, which is not evidence about the line
    that is there. It cost four words of Singapore law, two footnote markers in a Japanese report — where
    the rejoiner then welded one footnote onto another and made a sentence neither contains — and
    a standard's number from both cover pages of a Thai one.
    """
    carrying = {}
    for (index, _), value in marks.items():
        carrying.setdefault(value - index, set()).add(index)
    return {
        offset
        for offset, indices in carrying.items()
        if abs(offset) <= len(pages)
        and len(indices) >= MIN_FURNITURE_PAGES
        and any(index + 1 in indices for index in indices)
    }


def _shape(line: str) -> str:
    """One line with its whitespace collapsed and every numeric field masked out."""
    return _MULTISPACE.sub(" ", _DIGIT_RUN.sub(_FIELD, line))


def _fields(line: str) -> tuple:
    """The value of each numeric field in `line`, read through the one numeral table."""
    return tuple(int(fold_digits(m.group())) for m in _DIGIT_RUN.finditer(line))


def _head_group(shape: str) -> tuple:
    """What two mirrored spellings of one running head have in common.

    Printed legal publishing prints the page number on the left of a verso and the right of a
    recto, so `2020 Ed. … Act 1965 … 6` and `6 … Act 1965 … 2020 Ed.` are one head holding one
    body of evidence between two templates. Keyed on the multiset of non-numeric tokens, which is
    what survives the mirroring: order does not, and neither do the field positions. See
    @lbqi475m.
    """
    return tuple(sorted(shape.replace(_FIELD, " ").split()))


def _counts_up(rows: list) -> bool:
    """Does some one field advance at least one per page across the pages carrying this shape?

    Half of what makes the shape rule safe, and only half. "Constant except for a varying number"
    on its own also describes the edge rows of a long numbered table. @ly7tho4y claimed this was
    the whole of it — "a field that counts up with the pages is a page number, and nothing else in
    a statute behaves that way" — and `indonesia-id` refuted it with `Pasal N`, which counts up
    with the pages exactly as a page number does. The other half is `_STRUCTURAL`, applied in
    `_furniture_shapes`. See @lbqi475m.

    **Ascending alone is nearly free on two pages**, which is all `MIN_FURNITURE_PAGES` requires: a
    field ascends by chance half the time, so a three-field template clears it seven times in
    eight. So the rate is tested too, and against the **page indices** rather than the carrying
    rows, which is what lets a head printed on alternate pages rise two per appearance and still
    count one per page. `wef 03/10/2016]` and `wef 04/10/2016]` on pages 1 and 4 of seven rise 1
    across 3 and are not counting pages: they are two amendment dates this rule deleted from a
    Schedule. See @ykhhndj7.
    """
    indices = [index for index, _ in rows]
    values = [fields for _, fields in rows]
    span = indices[-1] - indices[0]
    return any(
        all(row[field] < nxt[field] for row, nxt in zip(values, values[1:]))
        and values[-1][field] - values[0][field] >= span
        for field in range(len(values[0]))
    )


def _shape_candidates(pages: list, structural) -> dict:
    """Every edge template that could be a running head, with the pages and field values it has.

    A line the package's structural grammar recognises is excluded here and nowhere else. That is
    the premise fix: the things other than page numbers that count up with the pages are provision
    headings, and `STRUCTURAL_OPENERS` is already the list of them. The *text* rule is left alone,
    because identical text on most pages cannot be distinct provisions — article numbers differ —
    so repetition of the literal string is proof of furniture in a way repetition of a template is
    not. See @lbqi475m.
    """
    seen = {}
    for index, page in enumerate(pages):
        rows = {}
        for line in reversed(_edge_lines(page, FURNITURE_LINES)):
            if structural.match(line):
                continue
            shape = _shape(line)
            if _FIELD not in shape:
                continue
            # A letter, or a line that is nothing but a page marker. `- 4 -` carries no letter and
            # is furniture; admitting it here is what lets a marker below a scanner's emblem be
            # reached on evidence rather than on position. See @kbdz5bmq.
            if not any(ch.isalpha() for ch in shape) and not _PAGE_NUMBER.match(line):
                continue
            rows[shape] = _fields(line)
        for shape, fields in rows.items():
            seen.setdefault(shape, []).append((index, fields))
    return seen


def _furniture_shapes(pages: list, structural) -> set:
    """Shapes that recur across the pages they span with a page number embedded in them.

    `strip_repeated_furniture` matches a running head by its exact text, and a publisher that
    prints the page number *inside* the header defeats that completely, because no two pages then
    carry the same string. SSO writes `2020 Ed.   National Registration Act 1965   6`; measured on
    the PDPA, 124 of 124 footers were stripped and the header survived on 120 of 123 pages,
    landing mid-provision through a 194,000-character document.

    The denominator is the **span** a head covers rather than the document, because a running head
    that starts after the contents page and stops before the schedules should be judged on the
    territory it runs through. `singapore-id` measured the old denominator on the Interpretation
    Act 1965: 63 pages of which 18 are front matter carrying no head, so each mirrored half is 22
    or 23 against a bar of 25 and nothing is stripped. The span must itself reach the document,
    which is what stops a template on pages 1 and 2 of sixty scoring two of two. See @lbqi475m.
    """
    bar = max(MIN_FURNITURE_PAGES, math.ceil(len(pages) * SHAPE_THRESHOLD))
    groups = {}
    for shape, rows in _shape_candidates(pages, structural).items():
        if _counts_up(rows):
            groups.setdefault(_head_group(shape), []).append((shape, rows))

    furniture = set()
    for members in groups.values():
        carrying = {index for _, rows in members for index, _ in rows}
        span = max(carrying) - min(carrying) + 1
        if span < bar:
            continue
        if len(carrying) < max(MIN_FURNITURE_PAGES, math.ceil(span * SHAPE_THRESHOLD)):
            continue
        furniture.update(shape for shape, _ in members)
    return furniture


def strip_repeated_furniture(pages: list, *, traditions=()) -> list:
    """Drop running headers, footers, and page numbers.

    Frequency alone is not enough, and it fails in two directions. "Page 1 of 127" never repeats
    verbatim, so it is matched by shape instead. And a running head carrying its own page number
    never repeats either, so it is matched by a second shape rule — a line constant except for a
    field that counts up with the pages, and which the structural grammar does not recognise as a
    provision heading. Frequency is measured only at the *edges* of a page: a phrase appearing in
    the body of every page is a defined term, not furniture.

    Two edge windows, not one. A page number is looked for in the tight `EDGE_LINES`, because that
    is where one would be; the two rules that prove furniture from repetition across pages reach
    `FURNITURE_LINES` deep, which is what lets them see a running head printed below a scanner's
    emblem. See @kbdz5bmq.

    **Every rule here now proves its case from other pages.** Being at the edge is where a page
    number is looked for and not why it is believed: a bare number is dropped only when the
    document's other numbers march with the pages around it (`_numbering_offsets`, @fu7njgwq).
    Position alone deleted a wrapped year from a table, and a footnote marker from a report.

    **All three rules match a whole line, and that is what makes dropping safe.** The text rule
    needs the entire line repeated across pages, the shape rule needs it repeated with only its
    numeric fields varying, and the page-number rule needs the line to be nothing but a number, so
    a line carrying unique body text satisfies none of them and cannot be taken from under a
    sentence.
    That is why this drops lines and `indonesia-id`'s `_FURNITURE_PREFIX`, which rewrites them, was
    not lifted: rewriting needs a rule about which part of a line to keep. See @zga5midk.
    """
    structural = structural_pattern(*traditions)
    if len(pages) < 2:
        return list(pages)

    edge_counts = Counter()
    for page in pages:
        # One vote per page per distinct line, for the reason `_edge_lines` gives.
        edge_counts.update(set(_edge_lines(page, FURNITURE_LINES)))

    threshold = max(MIN_FURNITURE_PAGES, int(len(pages) * FURNITURE_THRESHOLD))
    furniture = {line for line, n in edge_counts.items() if n >= threshold}
    shapes = _furniture_shapes(pages, structural)
    marks = _page_marks(pages)
    offsets = _numbering_offsets(pages, marks)

    out = []
    for number, page in enumerate(pages):
        lines = page.splitlines()
        ranks, filled = _line_ranks(lines)
        keep = []
        for index, line in enumerate(lines):
            stripped = line.strip()
            rank = ranks.get(index)
            deep = rank is not None and (
                rank < FURNITURE_LINES or rank >= filled - FURNITURE_LINES
            )
            marching = (number, index) in marks and marks[(number, index)] - number in offsets
            if (deep and (stripped in furniture or _shape(stripped) in shapes)) or marching:
                continue
            keep.append(line)
        out.append("\n".join(keep))
    return out


def clean_pages(pages: list, *, traditions=()) -> str:
    """Turn extracted pages into one searchable document."""
    if not pages:
        raise PdfError(
            "No pages were extracted. An empty page list is a failed extraction, not a document "
            "with no content."
        )
    if not any(p.strip() for p in pages):
        raise PdfError(
            "Every page extracted to whitespace, which means this PDF has no text layer. It is a "
            "scanned image and needs OCR (tesseract) before it can be quoted. Storing it would put "
            "a blank entry in the corpus that reads like a successful extraction."
        )
    if looks_cjk("\n".join(pages)):
        raise PdfError(
            "This extraction is predominantly CJK, and the cleaning below is English. "
            "`_UNTERMINATED` reads every line ending in 。 as mid-sentence and rejoins it with a "
            "space, which Japanese does not write between words — 「③発行者の電子署名から構成される」 "
            "comes out as 「③発行者の 電子署名から構成される」 and can no longer be found at all. That "
            "is a silent false negative manufactured by the cleaner, so this refuses rather than "
            "stores. Use lawcorpus.japanese.extract_japanese, which rejoins with no separator and "
            "reads Japanese sentence terminators. (Korean is not affected and does not arrive "
            "here: it writes spaces between words.)"
        )

    text = "\n".join(strip_repeated_furniture(pages, traditions=traditions))
    text = normalise_text(text.replace("\f", "\n"))
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = _rejoin_wrapped_lines(text, structural_pattern(*traditions))
    text = _MULTISPACE.sub(" ", text)
    text = _BLANKS.sub("\n\n", text)
    text = text.strip() + "\n"
    # @sqxbhlk2: everything above deletes lines or joins them with a space, so a token that is
    # here and in no source page means a step rewrote text instead of dropping it.
    refuse_fabrication("\n".join(pages), text, what="this PDF")
    return text


def _rejoin_wrapped_lines(text: str, structural) -> str:
    """Undo the hard wrapping pdftotext inherits from the page.

    Left wrapped, a search for a phrase spanning a line break fails — the same silent-false-
    negative failure as the no-break space in EU documents, from a different cause.
    """
    out = []
    for line in text.splitlines():
        if (
            out
            and line.strip()
            and out[-1].strip()
            and not structural.match(line)
            and _UNTERMINATED.search(out[-1])
        ):
            out[-1] = out[-1].rstrip() + " " + line.strip()
        else:
            out.append(line)
    return "\n".join(out)


def raw_pages(path, layout: bool = True) -> list:
    """Poppler's output for `path`, split into pages, with no cleaning applied.

    Separate from `extract` because a script with its own hazards needs the pages before this
    module's cleaning touches them — `thai.py` gates on the raw text and must not rejoin wrapped
    lines with a space, since Thai has no inter-word spaces.
    """
    path = Path(path)
    if not path.exists():
        raise PdfError(f"No PDF at {path}.")
    if shutil.which("pdftotext") is None:
        raise PdfError(
            "pdftotext is not on PATH. Install poppler-utils (Debian/Ubuntu: "
            "'apt-get install poppler-utils'; macOS: 'brew install poppler'). This package shells "
            "out to poppler rather than using a pure-Python reader because its layout analysis on "
            "multi-column legal documents is markedly better."
        )
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + [str(path), "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise PdfError(
            f"pdftotext failed on {path} with exit code {e.returncode}: "
            f"{e.stderr.decode('utf-8', 'replace')[:200]}"
        ) from e
    return result.stdout.decode("utf-8", "replace").split("\f")


# A watermark glyph as poppler leaves it in raw mode: a line that is nothing but one or two Latin
# letters. `aadhaar` measured India Code's diagonal stamp emitting `e`, `od`, `aC`, `di` and `In` on
# lines of their own — 140 in one 32-page instrument, against 0 in the publisher's own text of it.
# ASCII deliberately: a single CJK character on a line is ordinary in vertical setting, and a rule
# that counted it would refuse Japanese documents wholesale. See @k76mmqlc.
_GLYPH_LINE = re.compile(r"^[A-Za-z]{1,2}$")
# A watermark is stamped on every page, so the test is the share of pages carrying a glyph line
# rather than how many there are — structural, not magnitude.
#
# **This threshold does not separate, and that is why nothing calls it by default.** Measured over
# 11 India Code PDFs and 17 controls (@uf4epdvm): the 2021 Regulations score 0.966 and two
# watermarked Gazette PDFs score exactly 0.500, while `PUTTASWAMY-2018-SCR` — sound, stored, and a
# law report whose margin prints paragraph markers `A` to `H` one per line on every page — scores
# **0.998**. The control maximum is above the positive minimum, so no threshold admits the sound
# documents and refuses the spoiled ones. ~26ka
WATERMARK_PAGE_SHARE = 0.5


class ReadingOrderError(LawcorpusError):
    """A PDF stamped with a watermark, which poppler renders as text in both of its modes.

    `input.format` rather than a leaf of our own, for `TranslationStatusError`'s reason: the
    obstacle is the shape of the material we were given, at the level the standard fills.
    """

    code = "e.input.format.reading-order.f"


def watermark_share(pages: list) -> float:
    """The share of pages carrying a line that is nothing but a stray glyph or two.

    Read on the **raw-mode** rendering, because that is the one where the fragments stay visible.
    In layout mode poppler has already placed them by position, absorbing them into the lines they
    displaced, which is the failure rather than a way of seeing it.
    """
    if not pages:
        return 0.0
    stamped = sum(
        1
        for page in pages
        if any(_GLYPH_LINE.match(line.strip()) for line in page.splitlines())
    )
    return stamped / len(pages)


def check_reading_order(raw_mode_pages: list, what: str = "this PDF") -> None:
    """Refuse a PDF whose pages carry a watermark, in either rendering.

    Returns None on success, so it reads as an assertion at a call site. There is no rendering of
    a watermarked page this package can store: `-layout` moves the text the glyphs land in, and
    without it the glyphs sit on lines of their own that the rejoiner welds into a sentence. See
    @k76mmqlc.

    **Opt-in, for a caller that knows its publisher stamps every page.** Nothing calls this by
    default, because measured against the real PDFs the statistic does not separate: a law
    report's margin column of single letters scores higher than any watermark (@uf4epdvm, and the
    numbers are on `WATERMARK_PAGE_SHARE`). Assert it where you have judged the source; do not
    reach for it as a general check on an unknown one.
    """
    share = watermark_share(raw_mode_pages)
    if share <= WATERMARK_PAGE_SHARE:
        return None
    raise ReadingOrderError(
        f"{int(share * 100)}% of the pages of {what} carry a line that is nothing but one or two "
        f"stray letters, which is what a watermark stamped across a page leaves in poppler's "
        f"output. Neither rendering of such a page can be stored: with -layout the fragments are "
        f"placed by position and **displace** the text around them, so a phrase the document "
        f"contains greps to zero; without it they sit on lines of their own, where the rejoiner "
        f"welds them into the sentence beneath. Use the publisher's own text of this instrument if "
        f"there is one, or `raw_pages(path, layout=False)` and handle the fragments yourself."
    )


def extract(path, layout: bool = True, verify_order: bool = False, *, traditions=()) -> str:
    """Extract `path` to text with poppler, then clean it.

    `verify_order=True` asks for @k76mmqlc's watermark check, which renders the document a second
    time without `-layout` — layout mode does not merely pollute the text, it can move it, and
    once it has, the evidence that it did is gone.

    **It is off by default, and the default changed in @uf4epdvm.** Run against the PDFs it was
    built from, the check refuses sound documents: a law report scores 0.998 where the watermarked
    2021 Regulations score 0.966, and `aadhaar` extracts its judgments layer on exactly this path.
    A guard whose first firing is wrong is the one that gets turned off, so this one asks. The
    reordering it was built for is real and is now undetected here; catching it needs geometry
    (`pdftotext -bbox`), not a statistic over the text.
    """
    structural_pattern(*traditions)
    pages = raw_pages(path, layout)
    if layout and verify_order:
        check_reading_order(raw_pages(path, layout=False), str(path))
    return clean_pages(pages, traditions=traditions)
