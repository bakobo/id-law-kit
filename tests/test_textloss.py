"""@sqxbhlk2 — the only oracle here that reads words rather than declared structure."""

import pytest

from lawcorpus.japanese import clean_japanese_pages
from lawcorpus.pdf import clean_pages
from lawcorpus.textloss import (
    CHARACTERS,
    WORDS,
    TextLossError,
    compare,
    refuse_fabrication,
)


class TestCompare:
    def test_a_word_only_in_the_source_is_reported_as_removed(self):
        delta = compare("the Minister may prescribe 2016", "the Minister may prescribe")
        assert delta.removed == {"2016": 1}
        assert delta.added == {}

    def test_a_word_only_in_the_output_is_reported_as_added(self):
        delta = compare("the Minister may", "the Minister may not")
        assert delta.added == {"not": 1}

    def test_repetition_is_counted_not_collapsed(self):
        # A running head removed from 40 pages and a year removed from one are the same word
        # to a set and very different evidence, so the report counts.
        delta = compare("Act Act Act", "Act")
        assert delta.removed == {"Act": 2}

    def test_rewrapping_is_not_a_change(self):
        assert not compare("means the California\nAgency.", "means the California Agency.").any()

    def test_normalisation_is_applied_to_both_sides(self):
        # A no-break space in the source becomes an ordinary one in the output. That is the same
        # two words either way, and reporting it would be this check's first false positive.
        assert not compare("section 7001 applies", "section 7001 applies").any()

    def test_characters_are_available_for_a_script_that_writes_no_spaces(self):
        # Japanese rejoins with no separator, so two tokens become one and a whitespace tokeniser
        # sees a fabrication on every legitimate rejoin.
        assert compare("発行者の\n電子署名", "発行者の電子署名", tokens=WORDS).any()
        assert not compare("発行者の\n電子署名", "発行者の電子署名", tokens=CHARACTERS).any()


class TestRefuseFabrication:
    def test_a_source_that_survives_intact_is_allowed(self):
        assert refuse_fabrication("a b c", "a b") is None

    def test_an_invented_word_is_refused(self):
        with pytest.raises(TextLossError) as e:
            refuse_fabrication("the Minister may", "the Minister may not")
        assert "not" in str(e.value)
        assert e.value.transient is False
        assert e.value.code == "e.self.corrupt.text.f"

    def test_the_refusal_names_what_appeared_and_says_where_to_look(self):
        with pytest.raises(TextLossError) as e:
            refuse_fabrication("a b", "a b xyzzy plugh")
        assert "xyzzy" in str(e.value) and "plugh" in str(e.value)

    def test_the_message_is_bounded_when_everything_is_new(self):
        with pytest.raises(TextLossError) as e:
            refuse_fabrication("a", " ".join(f"word{n}" for n in range(200)))
        assert len(str(e.value)) < 2000


class TestTheCleanersCheckThemselves:
    def test_clean_pages_still_returns_text(self):
        assert "business" in clean_pages(["A business shall comply.", "A second page here."])

    def test_clean_pages_refuses_a_cleaning_that_invents_a_word(self, monkeypatch):
        import lawcorpus.pdf as pdf

        monkeypatch.setattr(pdf, "_rejoin_wrapped_lines", lambda text, _: text + "\nfabricated")
        with pytest.raises(TextLossError):
            clean_pages(["A business shall comply.", "A second page here."])

    def test_clean_japanese_pages_still_returns_text(self):
        pages = ["第一条　発行者の\n電子署名から構成される。", "第二条　二頁目の本文である。"]
        assert "発行者の電子署名から構成される。" in clean_japanese_pages(pages)

    def test_clean_japanese_pages_refuses_an_invented_character(self, monkeypatch):
        import lawcorpus.japanese as japanese

        monkeypatch.setattr(japanese, "_BLANKS", _Fabricator())
        with pytest.raises(TextLossError):
            clean_japanese_pages(["第一条　本文である。", "第二条　二頁目である。"])


class _Fabricator:
    def sub(self, _replacement, text):
        return text + "偽"
