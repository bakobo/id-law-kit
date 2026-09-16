"""One normalisation set, applied to every document whatever its language.

Phase 0 falsified the language-conditional design before it was written: Japanese uses U+3001 and
zero U+FF0C, Korean has no full-width punctuation at all, Singapore's English carries U+2011, and
the English-language CTID specification contains stray full-width parentheses. A document's
language tag does not predict its characters. See this.i @amdvdsah and @liv2lsxs.
"""

import re

import pytest

from lawcorpus.normalise import (
    NUMERAL_SYSTEMS,
    SEPARATORS,
    fold_digits,
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

    def test_a_character_class_still_works_now_that_ascii_is_folded(self):
        # @4zotolb5 reverses the "ASCII is never touched" rule; the class must survive it.
        assert normalise_query(r"Pasal [0-9]{1,3}") == "Pasal [0-9\u0e50-\u0e59]{1,3}"

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


class TestACjkQueryReachesLetterSpacedText:
    """@ux7izhdj — e-Gov letter-spaces 附　則, so 附則 must reach it without the text being edited."""

    def test_a_query_of_two_adjacent_cjk_characters_tolerates_a_space(self):
        rx = re.compile(normalise_query("附則"))
        assert rx.search("附則")
        assert rx.search("附 則")
        assert rx.search("附　則")

    def test_it_still_finds_the_cross_references_that_already_worked(self):
        rx = re.compile(normalise_query("附則"))
        assert len(rx.findall("附則第一条 ... 附則 ... 附則")) == 3

    def test_kana_counts_as_cjk(self):
        assert re.compile(normalise_query("この法律")).search("この 法律")

    def test_hangul_does_not_because_korean_writes_word_spaces(self):
        assert normalise_query("부칙") == "부칙"

    def test_a_character_class_still_works_now_that_ascii_is_folded(self):
        assert normalise_query("[0-9]{2}") == "[0-9\u0e50-\u0e59]{2}"
        assert normalise_query("law(fully|ful)") == "law(fully|ful)"

    def test_nothing_is_inserted_where_only_one_side_is_cjk(self):
        """Keeps the rewrite away from every regex metacharacter, which is never CJK."""
        assert normalise_query("(法)") == "(法)"
        assert normalise_query("法+") == "法+"
        assert normalise_query("A法") == "A法"

    def test_a_separator_still_expands_to_its_five_spellings(self):
        out = normalise_query("ㆍ")
        assert "・" in out and "·" in out

    def test_a_separator_between_two_cjk_characters_does_not_gain_a_space(self):
        """The separator expansion is a class; an optional space beside it would be noise."""
        out = normalise_query("法ㆍ令")
        assert "[ 　]?" not in out

    def test_a_full_width_character_is_still_folded_and_escaped(self):
        assert normalise_query("（") == re.escape("(")


class TestTheTwoFoldsAgreeAboutNumerals:
    """@4zotolb5 — `search_key` folded Thai digits and `normalise_query` did not, so
    `lawcite --grep 'มาตรา 7'` returned zero against a corpus holding `มาตรา ๗`.

    The agreement is asserted per system rather than per case, so a system added to
    `NUMERAL_SYSTEMS` without a query-side fold fails here rather than in a corpus repo.
    """

    @pytest.mark.parametrize("system", sorted(NUMERAL_SYSTEMS))
    def test_search_key_folds_every_digit_of_every_system_onto_arabic(self, system):
        for value, digit in enumerate(NUMERAL_SYSTEMS[system]):
            assert search_key(digit) == str(value)

    @pytest.mark.parametrize("system", sorted(NUMERAL_SYSTEMS))
    def test_an_arabic_query_reaches_every_digit_of_every_system(self, system):
        for value, digit in enumerate(NUMERAL_SYSTEMS[system]):
            assert re.search(normalise_query(str(value)), digit), (system, value)

    @pytest.mark.parametrize("system", sorted(NUMERAL_SYSTEMS))
    def test_a_native_query_still_reaches_arabic_text(self, system):
        for value, digit in enumerate(NUMERAL_SYSTEMS[system]):
            assert re.search(normalise_query(digit), str(value)), (system, value)

    def test_the_positive_control_for_thai_is_the_provision_that_returned_zero(self):
        # thailand-id: the stored text carries the source's own digits throughout.
        rx = re.compile(normalise_query("มาตรา 7"))
        assert rx.search("มาตรา ๗")
        assert rx.search("มาตรา 7")

    def test_the_positive_control_for_arabic_is_a_latin_corpus_left_working(self):
        rx = re.compile(normalise_query("Pasal 22"))
        assert rx.search("Pasal 22")
        assert not rx.search("Pasal 23")

    def test_fold_digits_is_the_one_table_both_sides_read(self):
        assert fold_digits("มาตรา ๓๒/๒") == "มาตรา 32/2"
        assert fold_digits("Pasal 22") == "Pasal 22"


class TestAQueryDigitIsExpandedWithoutBreakingTheRegex:
    """The price of @4zotolb5: `normalise_query` now tracks where in a regex it is standing."""

    def test_a_bare_digit_becomes_a_class_of_its_spellings(self):
        assert normalise_query("7") == "[7๗]"

    def test_a_digit_range_in_a_class_gains_the_parallel_range(self):
        # The case @liv2lsxs refused the whole fold over.
        assert normalise_query("[0-9]") == "[0-9๐-๙]"
        assert re.search(normalise_query("มาตรา [0-9]+"), "มาตรา ๓๒")

    def test_a_native_digit_range_gains_arabic_too(self):
        assert normalise_query("[๐-๙]") == "[0-9๐-๙]"

    def test_a_bare_digit_inside_a_class_is_added_to_it_rather_than_nested(self):
        assert normalise_query("[37]") == "[3๓7๗]"

    def test_a_quantifier_is_left_alone(self):
        assert normalise_query(r"\d{1,3}") == r"\d{1,3}"
        assert re.search(normalise_query(r"[0-9]{1,3}"), "๒๕๖๒")

    def test_an_escaped_digit_is_left_alone_so_a_backreference_still_works(self):
        assert normalise_query(r"(a)\1") == r"(a)\1"

    def test_an_escaped_class_delimiter_does_not_open_a_class(self):
        assert normalise_query(r"\[7\]") == r"\[[7๗]\]"

    def test_a_range_whose_ends_are_from_different_systems_is_left_alone(self):
        assert normalise_query("[0-๙]") == "[0-๙]"

    def test_a_descending_range_is_left_as_the_caller_wrote_it(self):
        # An invalid range stays invalid, so `cite.py` reports the caller's error, not ours.
        assert normalise_query("[9-0]") == "[9-0]"

    def test_a_hyphen_a_layout_fold_produces_is_escaped_inside_a_class(self):
        # U+2011 folds to '-', which would silently become a range inside a class.
        assert re.search(normalise_query("[a‑z]"), "-")
        assert not re.search(normalise_query("[a‑z]"), "m")

    def test_a_separator_inside_a_class_no_longer_nests_one(self):
        # @liv2lsxs documented this as a hole it would not parse for; the scanner closes it.
        rx = re.compile(normalise_query("[·x]"))
        assert rx.search("ㆍ") and rx.search("x")

    def test_no_optional_space_is_inserted_inside_a_class(self):
        # `[個人]` had been rewritten into something that is not a character class at all.
        rx = re.compile(normalise_query("[個人]"))
        assert rx.search("個") and rx.search("人")

    def test_an_unclosed_quantifier_brace_suppresses_the_fold_rather_than_corrupting_it(self):
        assert normalise_query("a{7") == "a{7"
