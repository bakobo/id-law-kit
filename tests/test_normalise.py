"""One normalisation set, applied to every document whatever its language.

Phase 0 falsified the language-conditional design before it was written: Japanese uses U+3001 and
zero U+FF0C, Korean has no full-width punctuation at all, Singapore's English carries U+2011, and
the English-language CTID specification contains stray full-width parentheses. A document's
language tag does not predict its characters. See this.i @amdvdsah and @liv2lsxs.
"""

import re

import pytest

from lawcorpus.normalise import (
    SEPARATORS,
    normalise_query,
    normalise_text,
    search_key,
)


class TestLayoutOnlyCharactersGo:
    def test_no_break_space_becomes_a_space(self):
        # "Article 22" in EU text: 232 occurrences in judgment C-634/21 alone.
        assert normalise_text("Article 22") == "Article 22"

    def test_narrow_and_figure_spaces_become_spaces(self):
        assert normalise_text("a b c") == "a b c"

    def test_non_breaking_hyphen_becomes_a_hyphen(self):
        # Without this, a search for "C-311/18" finds nothing in a judgment that cites it.
        assert normalise_text("C‑311/18") == "C-311/18"

    def test_soft_hyphen_disappears(self):
        assert normalise_text("pro­cessing") == "processing"

    def test_ideographic_space_becomes_a_space(self):
        # The separator between a chapter number and its title in Japanese statutes.
        assert normalise_text("第一章　総則") == "第一章 総則"

    def test_zero_width_and_joiner_characters_disappear(self):
        assert normalise_text("a​b⁠c﻿d") == "abcd"

    def test_full_width_parentheses_fold_to_ascii(self):
        # The decisive Phase 0 case: these turned up in an *English* specification.
        assert normalise_text("（a）") == "(a)"

    def test_full_width_comma_digits_and_letters_fold_to_ascii(self):
        assert normalise_text("Ａ１，２") == "A1,2"


class TestVisibleMeaningfulCharactersStay:
    def test_the_ideographic_comma_is_not_a_full_width_comma(self):
        # Japanese statutes use U+3001 2,681 times and U+FF0C zero times. It is a character in
        # its own right, not a width variant of ",".
        assert "、" in normalise_text("個人番号、法人番号")

    def test_the_ideographic_full_stop_stays(self):
        assert "。" in normalise_text("とする。")

    def test_the_korean_araea_separator_stays(self):
        # 4,966 occurrences across ten Korean instruments. Visible, and it means "and".
        assert normalise_text("헌법ㆍ법률") == "헌법ㆍ법률"

    def test_curly_quotes_and_dashes_stay(self):
        # EU drafting marks defined terms with the quotes; the dash is visible punctuation.
        assert normalise_text("‘personal data’ – defined") == "‘personal data’ – defined"

    def test_thai_sara_am_is_left_alone(self):
        # NFKC would decompose this into U+0E4D U+0E32 and turn 18 hits into 0.
        assert normalise_text("กำหนด") == "กำหนด"
        assert "ำ" in normalise_text("กำหนด")

    def test_thai_digits_stay_in_the_stored_text(self):
        # They are the authentic text. The numeral-system fold belongs to matching, not storage.
        assert "๒" in normalise_text("พ.ศ. ๒๕๖๒")


class TestPositiveControlsPerScript:
    """One control per script, so a regression fails loudly instead of quietly.

    Each pins the *operative* string a sweep would search for, after normalisation.
    """

    @pytest.mark.parametrize(
        "script, raw, must_contain",
        [
            ("japanese", "第一章　総則（第一条―第六条の二）", "第一章 総則(第一条―第六条の二)"),
            ("korean", "물리적ㆍ기술적ㆍ관리적 조치", "물리적ㆍ기술적ㆍ관리적"),
            ("chinese", "第一条（一）本规定、适用于", "第一条(一)本规定、适用于"),
            ("thai", "มาตรา ๙ กำหนดให้สำนักงาน", "กำหนดให้สำนักงาน"),
            ("latin", "Article 22 ‘personal data’ in C‑311/18", "Article 22"),
        ],
    )
    def test_the_operative_string_survives_normalisation(self, script, raw, must_contain):
        assert must_contain in normalise_text(raw)

    def test_no_script_loses_characters_it_needs(self):
        # A blunt guard against a future fold that eats a whole script: every one of these must
        # come back non-empty and no shorter than its non-layout content.
        for raw in ("個人番号", "개인정보", "个人信息", "ข้อมูลส่วนบุคคล", "personal data"):
            assert normalise_text(raw).strip() == raw


class TestNormaliseQuery:
    def test_a_full_width_parenthesis_in_a_query_is_a_literal_not_a_group(self):
        # Provision addressing: （一） is structural. The query must reach the folded text without
        # the parentheses turning into a capturing group.
        pattern = normalise_query("（一）")
        assert re.search(pattern, normalise_text("第一条（一）本规定"))

    def test_a_no_break_space_in_a_query_matches_the_normalised_text(self):
        assert re.search(normalise_query("Article 22"), normalise_text("Article 22"))

    def test_any_separator_spelling_finds_any_other(self):
        # A user typing the middle dot must find the araea, and vice versa.
        text = normalise_text("물리적ㆍ기술적")
        for typed in SEPARATORS:
            assert re.search(normalise_query(f"물리적{typed}기술적"), text)

    def test_ascii_is_left_alone_so_a_character_class_still_works(self):
        assert normalise_query(r"Pasal [0-9]{1,3}") == r"Pasal [0-9]{1,3}"

    def test_regex_metacharacters_survive(self):
        assert normalise_query(r"law(fully|ful)\b") == r"law(fully|ful)\b"

    def test_an_ideographic_comma_in_a_query_is_left_alone(self):
        assert re.search(normalise_query("番号、法人"), normalise_text("番号、法人"))


class TestSearchKey:
    """The comparison fold: for verifying an expected phrase, never for storing text."""

    def test_folds_thai_digits_onto_arabic(self):
        # The PDPA appears twice in Thailand's law list, once per numeral system.
        assert search_key("พ.ศ. ๒๕๖๒") == search_key("พ.ศ. 2562")

    def test_collapses_wrapped_whitespace(self):
        # method.md section 2's expected-phrase check failed on a correct document because the
        # title was line-wrapped across four lines in the PDF.
        assert search_key("Royal Decree\n   on Supervision") == search_key("Royal Decree on Supervision")

    def test_is_case_insensitive(self):
        assert search_key("ROYAL DECREE") == search_key("royal decree")

    def test_treats_every_separator_spelling_as_one(self):
        assert search_key("물리적ㆍ기술적") == search_key("물리적·기술적")

    def test_still_distinguishes_different_text(self):
        assert search_key("Pasal 22") != search_key("Pasal 23")


class TestExtractorsNormaliseUnconditionally:
    """Every renderer goes through the one set — nothing is conditional on a language."""

    def test_formex_normalises(self):
        from lawcorpus.formex import to_text

        out = to_text("<ACT><P>Article 22（a）</P></ACT>")
        assert "Article 22(a)" in out

    def test_pdf_normalises(self):
        from lawcorpus.pdf import clean_pages

        assert "Article 22(a)" in clean_pages(["Article 22（a）"])

    def test_caml_normalises(self):
        from lawcorpus.caml import to_text

        out = to_text("<div class='section'><p>Article 22（a）</p></div>")
        assert "Article 22(a)" in out
