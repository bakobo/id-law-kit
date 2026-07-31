"""Formex XML -> readable, citable text.

**Formex is where the text is.** This is the single most expensive thing to get wrong about
EUR-Lex, so it is stated plainly: the metadata notices carry no operative text.

    Accept: application/xml;notice=object   ->  7 KB   metadata only
    Accept: application/xml;notice=branch   ->  1.8 MB metadata, relations, provenance — no text
    Accept: application/zip;mtype=fmx4      ->  90 KB  a zip whose main member is the actual text

`Accept-Language` is mandatory on all three; omitting it returns HTTP 400 with a plain-text
explanation rather than a document.

Structure is preserved rather than flattened. A citation to "Article 5(1)(a) GDPR" has to be
locatable in the stored text, or quote-or-drop degrades into "the phrase appears somewhere in a
90,000-word file".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from defusedxml import ElementTree as SafeElementTree
from xml.etree import ElementTree

from .errors import LawcorpusError


class FormexError(LawcorpusError):
    """Formex input that will not parse, or a provision that is not in it."""

    code = "BK_FORMEX_PARSE"


@dataclass(frozen=True)
class Article:
    identifier: str
    number: str
    heading: str
    text: str


@dataclass(frozen=True)
class Recital:
    number: str
    text: str


_WS = re.compile(r"[ \t]*\n[ \t]*")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_BLANKS = re.compile(r"\n{3,}")

# Elements that should start a new line in the rendered text.
_BLOCK = {
    "ARTICLE",
    "TI.ART",
    "STI.ART",
    "PARAG",
    "ALINEA",
    "P",
    "ITEM",
    "NP",
    "CONSID",
    "TITLE",
    "TI",
    "STI",
    "VISA",
    "LIST",
    "NOTE",
    "DIVISION",
}


def _parse(source):
    if isinstance(source, bytes):
        source = source.decode("utf-8", "replace")
    if not source or not source.strip():
        raise FormexError(
            "The Formex input is empty. A zero-length body is a failed retrieval, not a document "
            "with no content."
        )
    try:
        # defusedxml: corpus XML is parsed, re-parsed, and may be hand-edited; billion-laughs
        # and external-entity attacks are cheap to foreclose and expensive to discover later.
        return SafeElementTree.fromstring(source)
    except ElementTree.ParseError as e:
        raise FormexError(
            f"This is not well-formed Formex XML: {e}. Check that the zip member you extracted is "
            f"the document body and not the small '.doc.xml' descriptor that ships beside it."
        ) from e


def _render(node, out):
    tag = node.tag

    if tag == "QUOT.START" or tag == "QUOT.END":
        code = node.get("CODE")
        if code:
            try:
                out.append(chr(int(code, 16)))
            except ValueError:  # pragma: no cover - CODE is hex in every observed document
                pass
        if node.tail:
            out.append(node.tail)
        return

    if tag in _BLOCK:
        out.append("\n")

    if node.text:
        out.append(node.text)

    for child in node:
        _render(child, out)

    if tag in ("NO.P", "NO.PARAG"):
        out.append(" ")
    if tag in ("TI.ART", "STI.ART", "NO.PARAG", "TXT", "P"):
        out.append("\n")

    if node.tail:
        out.append(node.tail)


def _clean(raw: str) -> str:
    # Source XML wraps mid-sentence for readability. Left alone, those newlines split phrases
    # and defeat a line-oriented search for "processed lawfully, fairly and in a transparent
    # manner" — which is exactly the kind of phrase a sweep looks for.
    text = raw.replace("\r\n", "\n")
    # Strip indentation off both sides of every newline FIRST, so the mid-sentence test below
    # sees the real next character rather than the XML's leading whitespace.
    text = _WS.sub("\n", text)
    text = re.sub(r"(?<![.:;)\]])\n(?=[a-z(])", " ", text)
    text = _MULTISPACE.sub(" ", text)
    text = _BLANKS.sub("\n\n", text)
    return text.strip() + "\n"


def _text_of(node) -> str:
    out = []
    _render(node, out)
    return _clean("".join(out))


def to_text(source) -> str:
    """The whole instrument as plain text, with headings and numbering preserved."""
    return _text_of(_parse(source))


def _article_number(el) -> str:
    title = "".join(el.find("TI.ART").itertext()) if el.find("TI.ART") is not None else ""
    m = re.search(r"(\d+[a-z]?)", title)
    if m:
        return m.group(1)
    # No TI.ART: fall back to the IDENTIFIER attribute ("005" -> "5").
    identifier = el.get("IDENTIFIER", "")
    return identifier.lstrip("0") or identifier


def articles(source) -> list:
    """Every article, in document order, each scoped to its own text."""
    root = _parse(source)
    found = []
    for el in root.iter("ARTICLE"):
        heading_el = el.find("STI.ART")
        found.append(
            Article(
                identifier=el.get("IDENTIFIER", ""),
                number=_article_number(el),
                heading=" ".join("".join(heading_el.itertext()).split()) if heading_el is not None else "",
                text=_text_of(el),
            )
        )
    return found


def article_text(source, number) -> str:
    """One article's text, looked up by its number."""
    wanted = str(number).strip().lower()
    found = articles(source)
    for art in found:
        if art.number.lower() == wanted:
            return art.text
    available = ", ".join(a.number for a in found[:12]) or "(none)"
    raise FormexError(
        f"There is no Article {wanted} in this document. Articles present include: {available}."
    )


def recitals(source) -> list:
    """The recitals, which for a GDPR-style instrument carry much of the operative meaning.

    Kept separate from the articles deliberately: a finding must be able to say whether it rests
    on binding enacting terms or on a recital, and flattening the two makes that unsayable.
    """
    root = _parse(source)
    out = []
    for el in root.iter("CONSID"):
        label = "".join(el.itertext())
        m = re.search(r"\((\d+)\)", label)
        out.append(Recital(number=m.group(1) if m else "", text=_text_of(el)))
    return out
