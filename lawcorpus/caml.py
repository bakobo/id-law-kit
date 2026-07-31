"""CAML (California markup) -> readable, citable text.

California publishes codified law inside the leginfo bulk database as CAML XML, one section per
`.lob` member. Structurally much simpler than Formex — essentially `<p>` elements — but it has its
own version of the trap that Formex has with no-break spaces:

    <p>(a)<span class="EnSpace"/>A business that controls the collection...</p>

The subdivision label is separated from its text by an **empty element**, not by a space. Strip
tags naively and you get "(a)A business that controls", so a search for "(a) A business" returns
nothing while the text looks correct on screen. Same failure shape as `formex.py`, different cause.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree

from defusedxml import ElementTree as SafeElementTree

from .errors import LawcorpusError
from .formex import _TYPOGRAPHY_TABLE

_MULTISPACE = re.compile(r"[ \t]{2,}")
_BLANKS = re.compile(r"\n{3,}")
# A heading is a short opening paragraph that is not itself a numbered subdivision.
_SUBDIVISION = re.compile(r"^\(\w+\)")


class CamlError(LawcorpusError):
    """CAML input that will not parse."""

    code = "BK_CAML_PARSE"


def _parse(source):
    if isinstance(source, bytes):
        source = source.decode("utf-8", "replace")
    if not source or not source.strip():
        raise CamlError(
            "The CAML input is empty. A zero-length .lob is a failed extraction, not a section "
            "with no text."
        )
    try:
        return SafeElementTree.fromstring(source)
    except ElementTree.ParseError as e:
        raise CamlError(
            f"This is not well-formed CAML: {e}. Check that the .lob member was extracted whole — "
            f"the leginfo archive stores one section per file."
        ) from e


def _paragraphs(root) -> list:
    out = []
    for el in root.iter():
        if not el.tag.endswith("}p") and el.tag != "p":
            continue
        parts = []
        if el.text:
            parts.append(el.text)
        for child in el:
            # The separator elements (EnSpace, EmSpace) carry no text; they *are* the space.
            parts.append(" ")
            if child.text:
                parts.append(child.text)
            if child.tail:
                parts.append(child.tail)
        text = " ".join("".join(parts).translate(_TYPOGRAPHY_TABLE).split())
        if text:
            out.append(text)
    return out


def to_text(source) -> str:
    """The section as plain text, one paragraph per line."""
    text = "\n\n".join(_paragraphs(_parse(source)))
    text = _MULTISPACE.sub(" ", text)
    return _BLANKS.sub("\n\n", text).strip() + "\n"


def heading(source) -> str:
    """The section's heading, or "" if its first paragraph is operative text.

    Many California sections have no heading and open at subdivision (a). Returning that as a
    title would put a sentence fragment in the manifest where an instrument name belongs.
    """
    paras = _paragraphs(_parse(source))
    if not paras or _SUBDIVISION.match(paras[0]):
        return ""
    return paras[0]
