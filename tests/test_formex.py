"""Formex XML -> readable, citable text.

Formex is the EU's authoring format, and it is what Cellar actually serves as the *text* of an
instrument. The metadata notices (`notice=branch`, `notice=object`) carry provenance and relations
but no operative text at all — a distinction that costs a wasted harvest if you get it wrong.

Structure is preserved rather than flattened, because a citation to "Article 5(1)(a) GDPR" has to
be locatable in the stored text for quote-or-drop to mean anything.
"""

import pytest

from lawcorpus.formex import (
    FormexError,
    article_text,
    articles,
    recitals,
    to_text,
)

DOC = """<?xml version="1.0" encoding="UTF-8"?>
<ACT>
  <PREAMBLE>
    <GR.CONSID>
      <CONSID><NP><NO.P>(1)</NO.P><TXT>The protection of natural persons is a fundamental
      right.</TXT></NP></CONSID>
      <CONSID><NP><NO.P>(2)</NO.P><TXT>This Regulation respects the
      <QUOT.START CODE="2018" ID="QS1" REF.END="QE1"/>Charter<QUOT.END CODE="2019" ID="QE1"
      REF.START="QS1"/>.</TXT></NP></CONSID>
    </GR.CONSID>
  </PREAMBLE>
  <ENACTING.TERMS>
    <DIVISION><TITLE><TI><P><HT TYPE="ITALIC">CHAPTER II</HT></P></TI>
      <STI><P><HT TYPE="BOLD">Principles</HT></P></STI></TITLE>
      <ARTICLE IDENTIFIER="005">
        <TI.ART>Article 5</TI.ART>
        <STI.ART>Principles relating to processing of personal data</STI.ART>
        <PARAG IDENTIFIER="005.001"><NO.PARAG>1.</NO.PARAG>
          <ALINEA><P>Personal data shall be:</P>
            <LIST TYPE="alpha">
              <ITEM><NP><NO.P>(a)</NO.P><TXT>processed lawfully, fairly and in a transparent
              manner;</TXT></NP></ITEM>
              <ITEM><NP><NO.P>(b)</NO.P><TXT>collected for specified purposes;</TXT></NP></ITEM>
            </LIST>
          </ALINEA>
        </PARAG>
        <PARAG IDENTIFIER="005.002"><NO.PARAG>2.</NO.PARAG>
          <ALINEA><P>The controller shall be responsible.</P></ALINEA>
        </PARAG>
      </ARTICLE>
      <ARTICLE IDENTIFIER="006">
        <TI.ART>Article 6</TI.ART>
        <STI.ART>Lawfulness of processing</STI.ART>
        <PARAG IDENTIFIER="006.001"><NO.PARAG>1.</NO.PARAG>
          <ALINEA><P>Processing shall be lawful only if...</P></ALINEA>
        </PARAG>
      </ARTICLE>
    </DIVISION>
  </ENACTING.TERMS>
</ACT>
"""


class TestToText:
    def test_produces_text(self):
        assert "Personal data shall be:" in to_text(DOC)

    def test_keeps_article_headings(self):
        out = to_text(DOC)
        assert "Article 5" in out
        assert "Principles relating to processing of personal data" in out

    def test_keeps_paragraph_numbers(self):
        # Without these, "Article 5(1)" cannot be located in the stored text.
        assert "1." in to_text(DOC)

    def test_keeps_list_item_labels(self):
        out = to_text(DOC)
        assert "(a)" in out
        assert "(b)" in out

    def test_keeps_recital_numbers(self):
        assert "(1)" in to_text(DOC)

    def test_keeps_chapter_headings(self):
        assert "CHAPTER II" in to_text(DOC)

    def test_resolves_quotation_markers_to_real_characters(self):
        # QUOT.START CODE="2018" is U+2018. Left as tags, the text reads as markup soup;
        # dropped silently, quoted phrases lose their delimiters.
        out = to_text(DOC)
        assert "‘Charter’" in out
        assert "QUOT.START" not in out

    def test_leaves_no_angle_brackets_behind(self):
        assert "<" not in to_text(DOC)

    def test_collapses_the_whitespace_the_xml_indentation_introduces(self):
        # Source XML wraps mid-sentence; a naive extraction leaves ragged internal newlines
        # that break phrase searching across a line boundary.
        assert "lawfully, fairly and in a transparent manner" in to_text(DOC)

    def test_accepts_bytes(self):
        assert "Article 5" in to_text(DOC.encode("utf-8"))

    def test_rejects_malformed_xml(self):
        with pytest.raises(FormexError) as e:
            to_text("<ACT><ARTICLE></ACT>")
        assert e.value.transient is False

    def test_rejects_empty_input(self):
        with pytest.raises(FormexError):
            to_text("")


class TestArticles:
    def test_lists_articles_in_order(self):
        assert [a.number for a in articles(DOC)] == ["5", "6"]

    def test_carries_the_identifier(self):
        assert articles(DOC)[0].identifier == "005"

    def test_carries_the_heading(self):
        assert articles(DOC)[0].heading == "Principles relating to processing of personal data"

    def test_carries_the_text(self):
        assert "processed lawfully" in articles(DOC)[0].text

    def test_article_text_is_scoped_to_that_article(self):
        assert "Lawfulness of processing" not in articles(DOC)[0].text


class TestArticleText:
    def test_looks_an_article_up_by_number(self):
        assert "processed lawfully" in article_text(DOC, "5")

    def test_accepts_an_integer(self):
        assert "processed lawfully" in article_text(DOC, 5)

    def test_unknown_article_says_what_is_there(self):
        with pytest.raises(FormexError) as e:
            article_text(DOC, "99")
        assert "99" in str(e.value)
        assert "5" in str(e.value)


class TestRecitals:
    def test_lists_recitals_in_order(self):
        assert [r.number for r in recitals(DOC)] == ["1", "2"]

    def test_carries_the_text(self):
        assert "fundamental" in recitals(DOC)[0].text

    def test_recitals_are_separate_from_articles(self):
        # GDPR's meaning lives substantially in its 173 recitals; conflating them with the
        # articles would make it impossible to say which one a finding rests on.
        assert all("fundamental right" not in a.text for a in articles(DOC))


class TestFormexOddities:
    def test_a_quotation_marker_without_a_code_is_dropped_not_crashed(self):
        doc = '<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>a<QUOT.START/>b</P></ARTICLE></ACT>'
        assert "ab" in to_text(doc).replace("\n", "")

    def test_a_quotation_marker_with_no_trailing_text(self):
        doc = '<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>a<QUOT.END CODE="2019"/></P></ARTICLE></ACT>'
        assert "’" in to_text(doc)

    def test_an_article_with_no_subtitle_gets_an_empty_heading(self):
        # Amending acts and short regulations routinely omit STI.ART.
        doc = '<ACT><ARTICLE IDENTIFIER="001"><TI.ART>Article 1</TI.ART><P>Text.</P></ARTICLE></ACT>'
        assert articles(doc)[0].heading == ""
        assert articles(doc)[0].number == "1"

    def test_an_article_with_no_title_element_falls_back_to_its_identifier(self):
        doc = '<ACT><ARTICLE IDENTIFIER="007"><P>Text.</P></ARTICLE></ACT>'
        assert articles(doc)[0].number == "7"

    def test_an_article_with_neither_title_nor_identifier_is_not_a_crash(self):
        assert articles("<ACT><ARTICLE><P>Text.</P></ARTICLE></ACT>")[0].number == ""


class TestTypographicNormalisation:
    """EU documents are typeset, not typed.

    'Article 22' in a CJEU judgment contains U+00A0 between the word and the number — 232 times in
    C-634/21 alone — and case numbers use U+2011 non-breaking hyphen, so 'C-311/18' does not match
    'C‑311/18'. Left alone, a sweep for 'Article 22' returns zero hits and reads as a finding.
    That is the same class of defect the utah-id-law adversarial review caught in its own sweep
    patterns on 2026-07-29, and it is worse here because it is invisible on screen.
    """

    def test_no_break_space_becomes_an_ordinary_space(self):
        doc = "<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>See Article 22(1).</P></ARTICLE></ACT>"
        assert "Article 22(1)" in to_text(doc)

    def test_non_breaking_hyphen_becomes_an_ordinary_hyphen(self):
        doc = "<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>Case C‑311/18.</P></ARTICLE></ACT>"
        assert "C-311/18" in to_text(doc)

    def test_narrow_no_break_space_is_normalised_too(self):
        doc = "<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>See Article 5.</P></ARTICLE></ACT>"
        assert "Article 5" in to_text(doc)

    def test_soft_hyphens_are_removed(self):
        doc = "<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>pro­cessing</P></ARTICLE></ACT>"
        assert "processing" in to_text(doc)

    def test_curly_quotes_are_preserved(self):
        # These carry meaning in EU drafting — defined terms are wrapped in them — and unlike a
        # no-break space they are visible, so a reader can search for what they see.
        doc = "<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>the ‘Charter’</P></ARTICLE></ACT>"
        assert "‘Charter’" in to_text(doc)

    def test_en_dashes_are_preserved(self):
        doc = "<ACT><ARTICLE><TI.ART>Article 1</TI.ART><P>2016–2018</P></ARTICLE></ACT>"
        assert "2016–2018" in to_text(doc)
