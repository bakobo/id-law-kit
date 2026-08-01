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
from .formex import _TYPOGRAPHY_TABLE

# How many lines at each edge of a page can be furniture.
EDGE_LINES = 3
# A line must appear at the same edge on at least this fraction of pages to count as furniture.
FURNITURE_THRESHOLD = 0.6

_PAGE_NUMBER = re.compile(
    r"^\s*(?:page\s+)?\d+\s*(?:of\s+\d+)?\s*$|^\s*-\s*\d+\s*-\s*$", re.IGNORECASE
)
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
      | \d+\.                       # 1.
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


def strip_repeated_furniture(pages: list) -> list:
    """Drop running headers, footers, and page numbers.

    Frequency alone is not enough: "Page 1 of 127" never repeats verbatim, so it is matched by
    shape instead. And frequency is measured only at the *edges* of a page — a phrase appearing in
    the body of every page is a defined term, not furniture.
    """
    if len(pages) < 2:
        return list(pages)

    edge_counts = Counter()
    for page in pages:
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        # The head and tail slices must not overlap, or a short page counts its own lines twice
        # and a line appearing once crosses the threshold on its own.
        head, tail = lines[:EDGE_LINES], lines[max(EDGE_LINES, len(lines) - EDGE_LINES):]
        # One vote per page per distinct line, for the same reason.
        edge_counts.update(set(head + tail))

    threshold = max(2, int(len(pages) * FURNITURE_THRESHOLD))
    furniture = {line for line, n in edge_counts.items() if n >= threshold}

    out = []
    for page in pages:
        lines = page.splitlines()
        keep, n = [], len(lines)
        for index, line in enumerate(lines):
            stripped = line.strip()
            at_edge = index < EDGE_LINES or index >= n - EDGE_LINES
            if at_edge and (stripped in furniture or _PAGE_NUMBER.match(stripped)):
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

    text = "\n".join(strip_repeated_furniture(pages))
    text = text.replace("\f", "\n").translate(_TYPOGRAPHY_TABLE)
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


def extract(path, layout: bool = True) -> str:
    """Extract `path` to text with poppler, then clean it."""
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
    return clean_pages(result.stdout.decode("utf-8", "replace").split("\f"))
