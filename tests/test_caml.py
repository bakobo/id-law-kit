"""CAML (California markup) -> readable, citable text.

California serves codified law as CAML XML inside .lob members of the leginfo bulk database.
Structurally simpler than Formex, but with its own trap: subdivision labels are separated from
their text by <span class="EnSpace"/> rather than by a space character, so a naive tag-strip
yields "(a)A business that controls..." and a search for "(a) A business" finds nothing.
"""

import pytest

from lawcorpus.caml import CamlError, heading, to_text

DOC = (
    '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
    "<p>General Duties of Businesses that Collect Personal Information</p>"
    '<p>(a)<span class="EnSpace"/>A business shall inform consumers of the following:</p>'
    '<p>(1)<span class="EnSpace"/>The categories of personal information collected.</p>'
    "<p>(b)<span class=\"EnSpace\"/>A business that operates a website.</p>"
    "</caml:Content>"
)


class TestToText:
    def test_extracts_the_text(self):
        assert "A business shall inform consumers" in to_text(DOC)

    def test_puts_a_space_after_a_subdivision_label(self):
        # The EnSpace span is the separator. Without this, "(a)A business" is unsearchable.
        assert "(a) A business shall inform" in to_text(DOC)

    def test_separates_paragraphs_with_newlines(self):
        assert to_text(DOC).count("\n") >= 3

    def test_leaves_no_markup(self):
        out = to_text(DOC)
        assert "<" not in out
        assert "EnSpace" not in out

    def test_accepts_bytes(self):
        assert "A business" in to_text(DOC.encode("utf-8"))

    def test_rejects_malformed_xml(self):
        with pytest.raises(CamlError) as e:
            to_text("<caml:Content><p></caml:Content>")
        assert e.value.transient is False

    def test_rejects_empty_input(self):
        with pytest.raises(CamlError):
            to_text("")

    def test_normalises_layout_only_characters(self):
        doc = '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#"><p>Section 1798.100</p></caml:Content>'
        assert "Section 1798.100" in to_text(doc)


class TestHeading:
    def test_returns_the_first_paragraph(self):
        assert heading(DOC) == "General Duties of Businesses that Collect Personal Information"

    def test_is_empty_when_the_first_paragraph_is_operative_text(self):
        # Many sections have no heading; the first <p> is subdivision (a). Returning that as a
        # title would put a sentence fragment in the manifest.
        doc = (
            '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
            '<p>(a)<span class="EnSpace"/>A business shall do the thing.</p></caml:Content>'
        )
        assert heading(doc) == ""

    def test_empty_document_has_no_heading(self):
        doc = '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#"></caml:Content>'
        assert heading(doc) == ""


class TestCamlEdges:
    def test_ignores_non_paragraph_elements(self):
        doc = (
            '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
            "<note>editorial</note><p>Operative text.</p></caml:Content>"
        )
        out = to_text(doc)
        assert "Operative text." in out
        assert "editorial" not in out

    def test_child_tail_text_is_kept(self):
        doc = (
            '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
            "<p>before<i>mid</i>after</p></caml:Content>"
        )
        out = to_text(doc)
        for fragment in ("before", "mid", "after"):
            assert fragment in out

    def test_a_child_with_no_text_or_tail_is_just_a_separator(self):
        doc = (
            '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
            '<p>(a)<span class="EnSpace"/>Text.</p></caml:Content>'
        )
        assert to_text(doc) == "(a) Text.\n"

    def test_an_empty_paragraph_is_dropped(self):
        doc = (
            '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
            "<p></p><p>Real text.</p></caml:Content>"
        )
        assert to_text(doc) == "Real text.\n"

    def test_a_paragraph_with_no_leading_text_still_renders(self):
        doc = (
            '<caml:Content xmlns:caml="http://lc.ca.gov/legalservices/schemas/caml.1#">'
            "<p><i>Italic opener.</i></p></caml:Content>"
        )
        assert "Italic opener." in to_text(doc)
