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

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from .errors import LawcorpusError
from .normalise import DIGITS, fold_digits, looks_cjk, normalise_text

# How many lines at each edge of a page can be furniture.
EDGE_LINES = 3
# A line must appear at the same edge on at least this fraction of pages to count as furniture.
FURNITURE_THRESHOLD = 0.6
# A *shape* must recur on at least this fraction, which is lower, and the difference is forced
# rather than tuned. Printed legal publishing mirrors its running heads between recto and verso —
# SSO puts the page number on the left of an even page and the right of an odd one — so a mirrored
# header is two shapes each appearing on about half the pages, and any threshold above one half
# structurally cannot see one. See @ly7tho4y.
SHAPE_THRESHOLD = 0.4

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
_STRUCTURAL = re.compile(
    r"""^\s*(?:
        \u00a7                      # section sign
      | \([a-zA-Z0-9]{1,4}\)        # (a) (1) (iii) (A)
      | \d+[A-Z]{0,2}\.             # 1.  23A.  16O.  — see @zr3b5ll2
      | ARTICLE\b | CHAPTER\b | DIVISION\b | TITLE\b
      | Note:
      | [A-Z][A-Z \u2019'\-]{6,}\s*$   # an all-caps heading line
    )""",
    re.VERBOSE,
)
# A line that ends mid-sentence: no terminal punctuation.
_UNTERMINATED = re.compile(r"[^.:;?!\)\]\u2019\"]\s*$")


class PdfError(LawcorpusError):
    """A PDF that will not extract, or a missing extractor."""

    code = "BK_PDF_EXTRACT"


def _edge_lines(page: str) -> list:
    """The lines at the top and bottom of one page, stripped, with no line counted twice.

    The head and tail slices must not overlap, or a short page counts its own lines twice and a
    line appearing once crosses the threshold on its own.
    """
    lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
    return lines[:EDGE_LINES] + lines[max(EDGE_LINES, len(lines) - EDGE_LINES):]


def _shape(line: str) -> str:
    """One line with its whitespace collapsed and every numeric field masked out."""
    return _MULTISPACE.sub(" ", _DIGIT_RUN.sub(_FIELD, line))


def _fields(line: str) -> tuple:
    """The value of each numeric field in `line`, read through the one numeral table."""
    return tuple(int(fold_digits(m.group())) for m in _DIGIT_RUN.finditer(line))


def _counts_up(values: list) -> bool:
    """Does some one field strictly increase across the pages carrying this shape?

    The condition that makes the shape rule safe. "Constant except for a varying number" on its
    own also describes the edge rows of a long numbered table, and a rule that eats content to
    remove furniture is worse than the furniture. A field that counts up with the pages is a page
    number, and nothing else in a statute behaves that way. See @ly7tho4y.
    """
    return any(
        all(row[field] < nxt[field] for row, nxt in zip(values, values[1:]))
        for field in range(len(values[0]))
    )


def _furniture_shapes(pages: list, threshold: int) -> set:
    """Shapes that recur at the page edges with a page number embedded in them.

    `strip_repeated_furniture` matches a running head by its exact text, and a publisher that
    prints the page number *inside* the header defeats that completely, because no two pages then
    carry the same string. SSO writes `2020 Ed.   National Registration Act 1965   6`; measured on
    the PDPA, 124 of 124 footers were stripped and the header survived on 120 of 123 pages,
    landing mid-provision through a 194,000-character document.
    """
    seen = {}
    for page in pages:
        for shape, fields in {_shape(ln): _fields(ln) for ln in reversed(_edge_lines(page))}.items():
            seen.setdefault(shape, []).append(fields)
    return {
        shape
        for shape, values in seen.items()
        if len(values) >= threshold
        and _FIELD in shape
        and any(ch.isalpha() for ch in shape)
        and _counts_up(values)
    }


def strip_repeated_furniture(pages: list) -> list:
    """Drop running headers, footers, and page numbers.

    Frequency alone is not enough, and it fails in two directions. "Page 1 of 127" never repeats
    verbatim, so it is matched by shape instead. And a running head carrying its own page number
    never repeats either, so it is matched by a second shape rule — a line constant except for a
    field that counts up with the pages. Frequency is measured only at the *edges* of a page: a
    phrase appearing in the body of every page is a defined term, not furniture.
    """
    if len(pages) < 2:
        return list(pages)

    edge_counts = Counter()
    for page in pages:
        # One vote per page per distinct line, for the reason `_edge_lines` gives.
        edge_counts.update(set(_edge_lines(page)))

    threshold = max(2, int(len(pages) * FURNITURE_THRESHOLD))
    furniture = {line for line, n in edge_counts.items() if n >= threshold}
    shapes = _furniture_shapes(pages, max(2, int(len(pages) * SHAPE_THRESHOLD)))

    out = []
    for page in pages:
        lines = page.splitlines()
        keep, n = [], len(lines)
        for index, line in enumerate(lines):
            stripped = line.strip()
            at_edge = index < EDGE_LINES or index >= n - EDGE_LINES
            if at_edge and (
                stripped in furniture
                or _PAGE_NUMBER.match(stripped)
                or (stripped and _shape(stripped) in shapes)
            ):
                continue
            keep.append(line)
        out.append("\n".join(keep))
    return out


def clean_pages(pages: list) -> str:
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

    text = "\n".join(strip_repeated_furniture(pages))
    text = normalise_text(text.replace("\f", "\n"))
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = _rejoin_wrapped_lines(text)
    text = _MULTISPACE.sub(" ", text)
    text = _BLANKS.sub("\n\n", text)
    return text.strip() + "\n"


def _rejoin_wrapped_lines(text: str) -> str:
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
            and not _STRUCTURAL.match(line)
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


def extract(path, layout: bool = True) -> str:
    """Extract `path` to text with poppler, then clean it."""
    return clean_pages(raw_pages(path, layout))
