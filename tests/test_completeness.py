"""The completeness oracle: an extraction that is full but short must not be stored.

The case that motivates it is UU 27/2022, Indonesia's Personal Data Protection Law. It is a 400-dpi
CCITT scan with an OCR text layer; it extracts to 52 KB of entirely plausible Indonesian, passes the
empty-extraction guard cleanly, and has lost Pasal 22, 70 and 72 and the whole of BAB XI-XII. The
positive control Phase 0 ran is reproduced below as a test, because it is the only thing that
distinguished "the law says nothing there" from "our copy says nothing there".

See this.i @zpycgven and @oym7gzus.
"""

import pytest

from lawcorpus.completeness import (
    TruncatedTextError,
    check_not_truncated,
    CompletenessError,
    Expectation,
    OracleError,
    Provision,
    provision,
    japanese_article_range,
    korean_gapless,
    scan,
    validity_from_status_hukum,
)
from lawcorpus.store import CorpusStore, StoreError
from lawcorpus.validity import Validity

# The damaged extraction, in miniature: Pasal 22 is gone, 21 and 23 are present, and the tail
# stops short of Pasal 26.
DAMAGED = "\n".join(
    [
        "BAB IV",
        "Pasal 20",
        "Setiap orang berhak...",
        "Pasal 21",
        "Pengendali Data Pribadi wajib...",
        "Pasal 23",
        "Dalam hal...",
        "Pasal 24",
        "Ketentuan lebih lanjut...",
    ]
)
INTACT = DAMAGED.replace("Pasal 23", "Pasal 22\nTeks yang hilang...\nPasal 23")


class TestScan:
    def test_finds_arabic_provision_numbers_in_document_order(self):
        assert scan(DAMAGED, "Pasal") == [20, 21, 23, 24]

    def test_only_counts_line_anchored_headings(self):
        # A "Pasal 175" inside a sentence is a cross-reference to another instrument, not a
        # heading here. Counting it would invent a provision and then report it missing.
        text = "Pasal 3\nsebagaimana dimaksud dalam Pasal 175 Undang-Undang Dasar\nPasal 4"
        assert scan(text, "Pasal") == [3, 4]

    def test_reads_roman_numerals(self):
        assert scan("BAB IX\nx\nBAB X\ny", "BAB", numerals="roman") == [9, 10]

    def test_reads_japanese_article_numbers(self):
        assert scan("第一条　総則\n第五十七条　罰則", "第", numerals="kanji") == [1, 57]

    def test_reads_thai_numerals_in_either_system(self):
        assert scan("มาตรา ๙\nx\nมาตรา 10", "มาตรา", numerals="thai") == [9, 10]

    def test_a_branch_article_is_neither_its_base_nor_a_two_digit_number(self):
        # Japanese 枝番: 第六条の二 is an article inserted after article 6, not article 62 — and
        # @kolycpun reverses the rest of it, because reading it as 6 made an insertion
        # indistinguishable from a duplicate heading.
        found = scan("第六条の二　x", "第", numerals="kanji")
        assert found == [Provision(6, (2,))]
        assert found != [6] and found != [62]

    def test_reads_kanji_numbers_past_a_hundred(self):
        # 道路交通法 runs to article 166, and 저작권법 to 142; three digits are ordinary.
        assert scan("第百条　x\n第百二十三条　y\n第二百条　z", "第", numerals="kanji") == [100, 123, 200]

    def test_an_unknown_numeral_system_is_refused_rather_than_guessed(self):
        with pytest.raises(OracleError):
            scan("Pasal 1", "Pasal", numerals="babylonian")


class TestExpectationCatchesTheIndonesianFailure:
    def test_an_interior_gap_is_refused(self):
        with pytest.raises(CompletenessError) as e:
            Expectation.over("Pasal", range(20, 25)).verify(DAMAGED)
        assert "Pasal 22" in str(e.value)

    def test_the_error_names_the_missing_provisions_not_a_count(self):
        with pytest.raises(CompletenessError) as e:
            Expectation.over("Pasal", [20, 21, 22, 23, 24]).verify(DAMAGED)
        message = str(e.value)
        assert "22" in message
        assert "Pasal" in message

    def test_a_truncated_tail_is_refused_and_named_as_a_tail(self):
        with pytest.raises(CompletenessError) as e:
            Expectation.over("Pasal", range(20, 27)).verify(INTACT)
        message = str(e.value)
        assert "25" in message and "26" in message
        assert "ends" in message.lower() or "tail" in message.lower()

    def test_an_interior_gap_and_a_truncated_tail_are_both_reported(self):
        # The Indonesian failure is both at once, which is why neither check may short-circuit.
        with pytest.raises(CompletenessError) as e:
            Expectation.over("Pasal", range(20, 27)).verify(DAMAGED)
        message = str(e.value)
        assert "22" in message
        assert "26" in message

    def test_lost_chapters_are_caught_by_the_same_machine(self):
        # BAB XI and XII vanished; one heading OCR'd as a bare "I" between IX and X.
        text = "BAB IX\na\nBAB I\nb\nBAB X\nc\nBAB XIII\nd"
        with pytest.raises(CompletenessError) as e:
            Expectation.over("BAB", range(9, 14), numerals="roman").verify(text)
        assert "11" in str(e.value) and "12" in str(e.value)

    def test_headings_out_of_sequence_are_refused(self):
        # The stray "I" is not a missing number, so a set comparison alone would pass it.
        text = "BAB IX\na\nBAB I\nb\nBAB X\nc"
        with pytest.raises(CompletenessError) as e:
            Expectation.over("BAB", [1, 9, 10], numerals="roman").verify(text)
        assert "order" in str(e.value).lower()

    def test_a_complete_extraction_passes_silently(self):
        assert Expectation.over("Pasal", range(20, 25)).verify(INTACT) is None

    def test_the_expectation_says_who_declared_it(self):
        # An oracle nobody can trace back to a source is just another guess.
        with pytest.raises(CompletenessError) as e:
            Expectation.over("Pasal", range(20, 25), source="BPK status record").verify(DAMAGED)
        assert "BPK status record" in str(e.value)


class TestPositiveControl:
    """`method.md` §4: interrogate the zero before reporting it."""

    def test_the_neighbours_of_a_missing_provision_are_present(self):
        found = scan(DAMAGED, "Pasal")
        assert 22 not in found  # the target
        assert 21 in found and 23 in found  # the controls
        assert len(found) == 4  # the tool works


class TestJapaneseTocOracle:
    # The oracle ships inside the instrument: <TOC> is authored by the publisher, not by us.
    TOC = (
        "（第一条―第六条の二）（第七条―第十六条）（第十六条の二―第十八条の六）（第十九条・第二十条）"
        "（第二十一条―第二十六条）"
    )

    def test_expands_every_declared_range(self):
        expectation = japanese_article_range(self.TOC)
        assert expectation.numbers == tuple(range(1, 27))

    def test_a_pair_joined_by_the_ideographic_middle_dot_is_two_articles(self):
        # （第十九条・第二十条） is a list of two, not a range. It happens to mean the same here,
        # and would not if the pair were not adjacent.
        assert japanese_article_range("（第十九条・第二十条）").numbers == (19, 20)

    def test_a_single_article_range_is_one_number(self):
        assert japanese_article_range("（第一条）").numbers == (1,)

    def test_branch_articles_do_not_inflate_the_range(self):
        assert japanese_article_range("（第一条―第六条の二）").numbers == tuple(range(1, 7))

    def test_it_names_the_toc_as_its_source(self):
        assert "TOC" in japanese_article_range(self.TOC).source

    def test_an_extraction_short_of_the_declared_range_is_refused(self):
        with pytest.raises(CompletenessError) as e:
            japanese_article_range("（第一条―第三条）").verify("第一条　x\n第三条　y")
        assert "2" in str(e.value)

    def test_a_toc_with_no_ranges_is_an_oracle_failure_not_a_pass(self):
        # Silently returning an empty expectation would make every extraction complete.
        with pytest.raises(OracleError):
            japanese_article_range("（目次）")

    def test_an_unparseable_article_number_is_refused(self):
        with pytest.raises(OracleError):
            japanese_article_range("（第〇〇条―第二条）")


class TestKoreanGaplessOracle:
    def test_expects_every_number_from_one_to_the_maximum(self):
        # Repealed articles survive as 삭제 placeholders, so the sequence has no holes. Held 7/7.
        text = "제1조 목적\n제2조 정의\n제3조 삭제\n제4조 적용"
        assert korean_gapless(text).numbers == (1, 2, 3, 4)

    def test_a_missing_repealed_placeholder_is_a_gap(self):
        text = "제1조 목적\n제2조 정의\n제4조 적용"
        with pytest.raises(CompletenessError) as e:
            korean_gapless(text).verify(text)
        assert "3" in str(e.value)

    def test_a_branch_article_does_not_extend_the_expectation(self):
        # 제24조의2 is inserted after article 24; it is not article 242.
        text = "제1조 x\n제2조 y\n제2조의2 z"
        assert korean_gapless(text).numbers == (1, 2)

    def test_an_empty_extraction_is_an_oracle_failure(self):
        with pytest.raises(OracleError):
            korean_gapless("no articles here")

    def test_it_says_it_cannot_see_a_truncated_tail(self):
        # Derived from the extraction itself, so a cut tail lowers the maximum and passes. Saying
        # so is the point; a check that quietly does less than it claims is worse than none.
        assert "tail" in korean_gapless("제1조 x\n제2조 y").source.lower()


class TestIndonesianStatusHukumOracle:
    def test_maps_the_vocabulary_onto_validity(self):
        assert validity_from_status_hukum("berlaku") is Validity.IN_FORCE
        assert validity_from_status_hukum("sebagian") is Validity.AMENDED
        assert validity_from_status_hukum("dicabut") is Validity.REPEALED

    def test_is_case_and_whitespace_insensitive(self):
        assert validity_from_status_hukum(" Berlaku ") is Validity.IN_FORCE

    def test_refuses_an_unknown_token_rather_than_defaulting_to_in_force(self):
        # A wrong validity is more dangerous than an absent one (taxonomy.md §3).
        with pytest.raises(OracleError) as e:
            validity_from_status_hukum("mungkin")
        assert "mungkin" in str(e.value)

    def test_refuses_an_empty_token(self):
        with pytest.raises(OracleError):
            validity_from_status_hukum("")


class TestStoreRefusesOnMismatch:
    def test_a_short_extraction_is_not_written(self, tmp_path):
        store = CorpusStore(tmp_path / "corpus")
        with pytest.raises(CompletenessError):
            store.write("uu27-2022", DAMAGED, expect=Expectation.over("Pasal", range(20, 25)))
        assert not store.exists("uu27-2022")

    def test_a_complete_extraction_is_written(self, tmp_path):
        store = CorpusStore(tmp_path / "corpus")
        written = store.write(
            "uu27-2022", INTACT, expect=Expectation.over("Pasal", range(20, 25))
        )
        assert written.bytes == len(INTACT.encode())

    def test_an_undeclared_structure_still_stores(self, tmp_path):
        # The oracle is opt-in per item: most corpora have no declared structure to check.
        store = CorpusStore(tmp_path / "corpus")
        assert store.write("x", DAMAGED).bytes

    def test_the_empty_guard_still_fires_first(self, tmp_path):
        store = CorpusStore(tmp_path / "corpus")
        with pytest.raises(StoreError):
            store.write("x", "", expect=Expectation.over("Pasal", [1]))


class TestABoundedScan:
    """@qd6p2f3x — a schedule restarts the numbering, so the scan has to be able to stop."""

    JAPANESE = "\n".join(
        [
            "第一条 この法律は...",
            "第二条 この法律において...",
            "第三条 国は...",
            "附則",
            "第一条 この法律は、公布の日から施行する。",
            "第二条 経過措置は...",
        ]
    )

    def test_an_unbounded_scan_reads_the_schedule_and_calls_it_out_of_order(self):
        assert scan(self.JAPANESE, "第", numerals="kanji") == [1, 2, 3, 1, 2]

    def test_a_boundary_stops_the_scan_at_the_line_that_matches(self):
        assert scan(self.JAPANESE, "第", numerals="kanji", boundary=r"^附則") == [1, 2, 3]

    def test_a_correct_document_with_a_schedule_verifies(self):
        Expectation.over("第", [1, 2, 3], numerals="kanji", boundary=r"^附則").verify(self.JAPANESE)

    def test_without_the_boundary_the_same_document_is_refused(self):
        with pytest.raises(CompletenessError) as e:
            Expectation.over("第", [1, 2, 3], numerals="kanji").verify(self.JAPANESE)
        assert "out of order" in str(e.value)

    def test_a_provision_surviving_only_in_the_schedule_does_not_count_as_present(self):
        """The reason to bound rather than to tolerate: otherwise a lost article reads as present."""
        text = "第一条 ...\n第三条 ...\n附則\n第二条 ..."
        with pytest.raises(CompletenessError) as e:
            Expectation.over("第", [1, 2, 3], numerals="kanji", boundary=r"^附則").verify(text)
        assert "第 2" in str(e.value)

    def test_a_boundary_that_matches_nothing_leaves_the_scan_whole(self):
        assert scan("Article 1\nArticle 2", "Article", boundary=r"^SCHEDULE") == [1, 2]

    def test_a_boundary_that_is_not_a_regex_is_an_oracle_failure(self):
        with pytest.raises(OracleError) as e:
            scan("Article 1", "Article", boundary="(unclosed")
        assert "boundary" in str(e.value)

    def test_the_boundary_travels_with_the_expectation_into_its_source_line(self):
        e = Expectation.over("第", [1], numerals="kanji", boundary=r"^附則", source="the TOC")
        assert e.boundary == r"^附則"


class TestTheJapaneseOracleKnowsItsOwnSchedules:
    TOC = "（第一条―第三条）"
    BODY = "\n".join(["第一条 ...", "第二条 ...", "第三条 ...", "附　則", "第一条 ..."])

    def test_it_bounds_itself_at_the_supplementary_provisions(self):
        japanese_article_range(self.TOC).verify(self.BODY)

    def test_the_boundary_reaches_the_letter_spaced_heading(self):
        assert "附" in japanese_article_range(self.TOC).boundary

    def test_it_also_reaches_the_label_prefixed_form(self):
        body = self.BODY.replace("附　則", "附則(令和七年法律第三十八号)")
        japanese_article_range(self.TOC).verify(body)


class TestACollapsedRepealRange:
    """「第十条から第十五条まで　削除」 — one heading standing for six articles. @y3aozl55."""

    TOC = "（第一条―第十六条）"
    BODY = "\n".join(
        [f"第{n}条 ..." for n in "一二三四五六七八九"]
        + ["第十条から第十五条まで 削除", "第十六条 ..."]
    )

    def test_without_the_titles_the_collapsed_articles_read_as_missing(self):
        with pytest.raises(CompletenessError) as e:
            japanese_article_range(self.TOC).verify(self.BODY)
        assert "第 11" in str(e.value)

    def test_the_declared_titles_drop_them_from_the_expectation(self):
        expectation = japanese_article_range(
            self.TOC, article_titles=["第十条から第十五条まで", "第十六条"]
        )
        assert 11 not in expectation.numbers
        assert 15 not in expectation.numbers
        assert 10 in expectation.numbers  # the heading that is actually present
        assert 16 in expectation.numbers

    def test_the_source_says_how_many_were_dropped_and_why(self):
        expectation = japanese_article_range(self.TOC, article_titles=["第十条から第十五条まで"])
        assert "5" in expectation.source
        assert "削除" in expectation.source or "collapse" in expectation.source

    def test_an_ordinary_article_title_drops_nothing(self):
        plain = japanese_article_range(self.TOC, article_titles=["第一条", "第十六条"])
        assert plain.numbers == japanese_article_range(self.TOC).numbers

    def test_a_document_declaring_the_range_now_verifies(self):
        japanese_article_range(
            self.TOC, article_titles=["第十条から第十五条まで"]
        ).verify(self.BODY)


class TestAPartialInstrument:
    """e-Gov's `<MainProvision Extract="true">`: the TOC describes more than the response. @y3aozl55."""

    TOC = "（第一条―第二十条）"

    def test_the_declared_articles_are_dropped(self):
        assert japanese_article_range(self.TOC, partial=True).numbers == ()

    def test_a_part_of_the_instrument_no_longer_reads_as_damaged(self):
        japanese_article_range(self.TOC, partial=True).verify("第一条 ...\n第十八条 ...")

    def test_order_is_still_checked_because_that_is_what_is_left(self):
        with pytest.raises(CompletenessError) as e:
            japanese_article_range(self.TOC, partial=True).verify("第十八条 ...\n第一条 ...")
        assert "order" in str(e.value)

    def test_the_refusal_does_not_claim_zero_of_zero_provisions(self):
        with pytest.raises(CompletenessError) as e:
            japanese_article_range(self.TOC, partial=True).verify("第二条 ...\n第一条 ...")
        assert "0 of 0" not in str(e.value)

    def test_the_source_announces_that_it_checks_almost_nothing(self):
        source = japanese_article_range(self.TOC, partial=True).source
        assert "order" in source
        assert "part" in source

    def test_a_partial_instrument_still_needs_a_readable_toc(self):
        with pytest.raises(OracleError):
            japanese_article_range("(nothing here)", partial=True)


class TestTheKoreanOracleIsBoundedToo:
    def test_a_supplementary_block_no_longer_makes_a_document_out_of_order(self):
        text = "제1조 ...\n제2조 ...\n부칙\n제1조 이 법은..."
        korean_gapless(text).verify(text)

    def test_the_schedule_does_not_raise_the_maximum(self):
        text = "제1조 ...\n제2조 ...\n부칙\n제9조 ..."
        assert korean_gapless(text).numbers == (1, 2)


class TestThePublicKanjiReader:
    """@ooyin3yr — a caller should not have to assemble a fake heading to reach a parser."""

    @pytest.mark.parametrize(
        "raw,expected",
        [("一", 1), ("十", 10), ("十五", 15), ("五十七", 57), ("百", 100), ("二百三十四", 234)],
    )
    def test_it_reads_a_number(self, raw, expected):
        from lawcorpus.completeness import kanji_number

        assert kanji_number(raw) == expected

    def test_it_refuses_a_character_it_does_not_know(self):
        from lawcorpus.completeness import kanji_number

        with pytest.raises(OracleError):
            kanji_number("五千")


class TestProvision:
    """@kolycpun — the value a sub-numbered heading reads as. It has to behave as its own base
    integer where there is no sub-number, or every expectation declared over integers breaks."""

    def test_a_bare_provision_equals_its_number(self):
        assert Provision(32) == 32
        assert 32 == Provision(32)

    def test_a_bare_provision_hashes_as_its_number(self):
        # The membership test in `verify` is a set lookup, so equality without hashing is silent.
        assert hash(Provision(32)) == hash(32)
        assert Provision(32) in {32, 33}

    def test_a_sub_numbered_provision_does_not_equal_its_base(self):
        assert Provision(32, (2,)) != 32
        assert Provision(32, (2,)) not in {32}

    def test_two_provisions_with_the_same_parts_are_equal_whatever_they_render_as(self):
        assert Provision(6, (2,), "の") == Provision(6, (2,), "/")

    def test_it_is_not_equal_to_something_that_is_not_a_provision_or_a_number(self):
        assert Provision(32) != "32"

    def test_a_sub_number_sorts_between_its_base_and_the_next_provision(self):
        assert sorted([Provision(7), Provision(32, (2,)), Provision(32), Provision(6)]) == [
            Provision(6), Provision(7), Provision(32), Provision(32, (2,))
        ]

    def test_sub_numbers_sort_numerically_rather_than_as_text(self):
        assert Provision(6, (2,)) < Provision(6, (10,))

    def test_a_letter_suffix_sorts_after_the_bare_number_and_before_the_next(self):
        assert Provision(23) < Provision(23, ("A",)) < Provision(23, ("B",)) < Provision(24)

    def test_it_compares_against_a_plain_integer_in_both_directions(self):
        assert Provision(23, ("A",)) > 23
        assert 24 > Provision(23, ("A",))

    def test_it_is_not_ordered_against_something_it_cannot_compare_with(self):
        with pytest.raises(TypeError):
            Provision(23) < "24"

    def test_index_reaches_the_base_so_range_and_int_still_work(self):
        assert int(Provision(23, ("A",))) == 23
        assert list(range(Provision(3))) == [0, 1, 2]

    def test_it_renders_the_way_its_own_drafting_tradition_writes_it(self):
        assert str(Provision(32, (2,), "/")) == "32/2"
        assert str(Provision(6, (2,), "の")) == "6の2"
        assert str(Provision(23, ("A",))) == "23A"
        assert str(Provision(23)) == "23"

    def test_provision_parses_the_form_a_table_of_contents_hands_you(self):
        assert provision("23A") == Provision(23, ("A",))
        assert provision("32/2") == Provision(32, (2,))
        assert provision("17") == 17

    def test_provision_refuses_what_it_cannot_read_rather_than_guessing(self):
        with pytest.raises(OracleError):
            provision("Schedule")


class TestScanReadsSubNumbering:
    """@kolycpun — four jurisdictions, one collapse. `มาตรา ๓๒/๒` read as 32, so an inserted
    section was indistinguishable from a duplicate heading."""

    def test_thai_reads_the_slash_form(self):
        text = "มาตรา ๓๒ ความ\nมาตรา ๓๒/๒ ความ\nมาตรา ๓๓ ความ"
        assert scan(text, "มาตรา", numerals="thai") == [32, Provision(32, (2,)), 33]

    def test_a_thai_inserted_section_is_no_longer_its_parent(self):
        found = scan("มาตรา ๓๒/๒ ความ", "มาตรา", numerals="thai")
        assert found != [32]
        assert str(found[0]) == "32/2"

    def test_japanese_reads_the_branch_article(self):
        text = "第六条　目的\n第六条の二　定義\n第七条　適用"
        assert scan(text, "第", numerals="kanji") == [6, Provision(6, (2,)), 7]

    def test_a_japanese_branch_article_still_satisfies_a_declaration_of_its_base(self):
        # The TOC declares article 6; the body carries 第六条 and 第六条の二.
        text = "第六条　目的\n第六条の二　定義"
        Expectation.over("第", [6], numerals="kanji").verify(text)

    def test_a_common_law_letter_suffix_is_read(self):
        text = "Section 23 Interpretation\nSection 23A Registration\nSection 24 Offences"
        assert scan(text, "Section") == [23, Provision(23, ("A",)), 24]

    def test_an_indonesian_inserted_article_is_read(self):
        assert scan("Pasal 13A Ketentuan", "Pasal") == [Provision(13, ("A",))]

    def test_a_korean_branch_article_still_reads_as_its_base(self):
        # 조의2 needs a Korean particle in the pattern, which the arabic system does not carry.
        assert scan("제24조의2 목적", "제") == [24]

    def test_an_ordinary_heading_is_unchanged(self):
        assert scan("Pasal 21\nPasal 23", "Pasal") == [21, 23]

    def test_deeper_sub_numbering_is_read_in_order(self):
        assert scan("มาตรา ๓๒/๒/๑ ความ", "มาตรา", numerals="thai") == [Provision(32, (2, 1))]

    def test_roman_numerals_carry_no_sub_numbering(self):
        assert scan("BAB IV\nBAB V", "BAB", numerals="roman") == [4, 5]

    def test_a_missing_inserted_section_is_now_visible_to_an_oracle(self):
        text = "มาตรา ๓๒ ความ\nมาตรา ๓๓ ความ"
        expect = Expectation.over("มาตรา", [32, provision("32/2"), 33], numerals="thai")
        with pytest.raises(CompletenessError) as e:
            expect.verify(text)
        assert "32/2" in str(e.value)


class TestAnInstrumentWithNoProvisionLabels:
    """@q5fyyb4q — a Singapore section heading is a bare `3.—(1)`, and the PDF prints its own
    contents page before the body."""

    SSO = "\n".join(
        [
            "ARRANGEMENT OF SECTIONS",
            "1. Short title",
            "17. Registration",
            "23A. Identity documents",
            "An Act to provide for the registration of persons.",
            "1.—(1) This Act is the National Registration Act 1965.",
            "17.—(1) The Registrar must register every person.",
            "23A.—(1) The Registrar may issue an identity card.",
            "FIRST SCHEDULE",
            "1. Form of application",
        ]
    )

    def test_a_label_less_scan_needs_a_terminator_or_it_is_refused(self):
        with pytest.raises(OracleError) as e:
            scan("1. Short title", "")
        assert "terminator" in str(e.value)

    def test_a_terminator_anchors_a_heading_that_has_no_label(self):
        found = scan("1.—(1) This Act is the Act.\n(a) a wrapped item", "", terminator=r"\.")
        assert found == [1]

    def test_the_contents_page_is_cut_off_the_front(self):
        found = scan(self.SSO, "", terminator=r"\.", start=r"^An Act\b", boundary=r"^FIRST SCHEDULE")
        assert found == [1, 17, Provision(23, ("A",))]

    def test_the_whole_thing_verifies_as_a_declared_structure(self):
        Expectation.over(
            "",
            [1, 17, provision("23A")],
            terminator=r"\.",
            start=r"^An Act\b",
            boundary=r"^FIRST SCHEDULE",
            source="the instrument's own table of contents, as SSO renders it",
        ).verify(self.SSO)

    def test_without_the_start_a_sound_document_fails_on_its_own_contents_page(self):
        # Every section number appears twice, so the order check fires on a good extraction.
        # This is the second half of what made the class unusable for singapore-id.
        expect = Expectation.over(
            "", [1, 17, provision("23A")], terminator=r"\.", boundary=r"^FIRST SCHEDULE"
        )
        with pytest.raises(CompletenessError) as e:
            expect.verify(self.SSO)
        assert "out of order" in str(e.value)

    def test_with_the_start_a_truncated_body_is_caught_rather_than_vouched_for(self):
        # The contents page still lists 23A. Scanning from the body opener is what stops the
        # document's own index certifying a section its body no longer carries.
        truncated = self.SSO.replace("23A.—(1) The Registrar may issue an identity card.\n", "")
        with pytest.raises(CompletenessError) as e:
            Expectation.over(
                "", [1, 17, provision("23A")], terminator=r"\.",
                start=r"^An Act\b", boundary=r"^FIRST SCHEDULE",
            ).verify(truncated)
        assert "23A" in str(e.value)

    def test_a_start_that_is_not_found_refuses_rather_than_scanning_everything(self):
        with pytest.raises(OracleError) as e:
            scan(self.SSO, "", terminator=r"\.", start=r"^In exercise of the powers\b")
        assert "body" in str(e.value)

    def test_an_unusable_start_regex_is_named_as_such(self):
        with pytest.raises(OracleError) as e:
            scan(self.SSO, "", terminator=r"\.", start="[")
        assert "regular expression" in str(e.value)

    def test_the_refusal_reads_without_a_label_to_hang_it_on(self):
        expect = Expectation.over("", [1, 17, 99], terminator=r"\.", start=r"^An Act\b",
                                  boundary=r"^FIRST SCHEDULE")
        with pytest.raises(CompletenessError) as e:
            expect.verify(self.SSO)
        message = str(e.value)
        assert "' '" not in message
        assert "99" in message


class TestARoundLengthWithNoTerminator:
    """@k4w7rvit — India Code's bundle for the DPDP Rules 2025 stops at exactly 100,000
    characters, mid-sentence, with no marker, where an inventory check cannot see it.
    """

    def test_a_cap_at_a_round_number_mid_sentence_is_refused(self):
        with pytest.raises(TruncatedTextError) as excinfo:
            check_not_truncated("a" * 99_980 + " and the Board shall", "the DPDP Rules 2025")
        message = str(excinfo.value)
        assert "the DPDP Rules 2025" in message
        assert "100000" in message

    def test_a_round_length_that_ends_in_a_full_stop_is_a_document(self):
        # One document in a thousand has a round length by chance. That alone is not evidence.
        assert check_not_truncated("a" * 99_999 + ".") is None

    def test_an_unround_length_that_ends_mid_sentence_is_a_source_that_serves_an_excerpt(self):
        assert check_not_truncated("a" * 99_980 + " and the Board shal") is None

    def test_a_power_of_two_is_a_cap_too(self):
        with pytest.raises(TruncatedTextError):
            check_not_truncated("a" * (65_536 - 20) + " and the Board shall")

    def test_a_small_power_of_two_is_below_the_floor(self):
        assert check_not_truncated("a" * (2048 - 20) + " and the Board shall") is None

    def test_trailing_whitespace_does_not_hide_the_ending(self):
        with pytest.raises(TruncatedTextError):
            check_not_truncated("a" * 99_980 + " and the Board shal\n")

    @pytest.mark.parametrize("text", ["", None, "   "])
    def test_nothing_at_all_is_not_a_truncation(self, text):
        assert check_not_truncated(text) is None

    @pytest.mark.parametrize("ending", ["。", "」", "?", ")", "”"])
    def test_a_terminator_in_any_script_the_programme_holds_ends_a_document(self, ending):
        assert check_not_truncated("a" * (100_000 - 1) + ending) is None
