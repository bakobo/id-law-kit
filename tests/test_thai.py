"""The Thai extraction path, against the traps Phase 0 observed on real Gazette bytes.

Three of them defeat everything already in this package. `pdftotext` drops U+0E33 `ำ` from Gazette
PDFs 100% of the time, so `กำหนด` occurs 87 times in the PDPA and matches zero. NFKC — the obvious
normalisation — makes it worse, taking `สำนักงาน` from 18 hits to 0. And a mojibake PDF extracts
*non-empty*, so the empty-extraction guard never fires.

See this.i @7xsnhink and @psletl4a, and `.asia-recon/thailand.md` traps T2, T5, T6, T7, T8.
"""

import unicodedata

import pytest

from lawcorpus.thai import (
    ThaiMojibakeError,
    ThaiSaraAmError,
    ThaiTextError,
    ThaiToneMarkError,
    compose_sara_am,
    extract_thai,
    repair_marks,
    strip_gazette_furniture,
    strip_watermark_fragments,
    thai_ratio,
    thai_search_key,
    word_likeness,
)

# A page of real-shaped Thai statutory prose.
GOOD_PAGE = (
    "มาตรา ๙ ให้สำนักงานคณะกรรมการคุ้มครองข้อมูลส่วนบุคคลกำหนดหลักเกณฑ์\n"
    "และวิธีการในการเก็บรวบรวมข้อมูลส่วนบุคคลตามที่คณะกรรมการกำหนด\n"
)
# The T7 case: a correct Thai running header over a body that is semantic noise.
MOJIBAKE_PAGE = (
    "เลม ๑๔๐ ตอนพิเศษ ๒๙๐ ง\n"
    "ราชกิจจานุเบกษา\n"
    "'1>@0ค>11/@1$B111/#@อ>N3O#1อ%>2์\n"
    "N1APอ %>!>&Bคค3อAP%#?P2@/@1\"N'็%(CO/?2>#$>0AP%คํ@อ1?&Q&อ%B@!\n"
    "Powered by TCPDF (www.tcpdf.org)\n"
)


class TestComposeSaraAm:
    def test_composes_the_decomposed_spelling(self):
        # U+0E4D U+0E32 and U+0E33 render identically and are different bytes. The ETDA
        # Establishment Act is spelled the second way, so the correct query does not find it.
        decomposed = "สํานักงาน"
        assert "ำ" not in decomposed
        assert compose_sara_am(decomposed) == "สำนักงาน"

    def test_leaves_the_composed_spelling_alone(self):
        assert compose_sara_am("สำนักงาน") == "สำนักงาน"

    def test_is_the_opposite_of_what_nfkc_does(self):
        # NFKC decomposes every ำ, so "normalising" a corpus takes 18 hits to 0. This is the
        # regression test for anyone who reaches for the standard tool.
        assert "ำ" not in unicodedata.normalize("NFKC", "สำนักงาน")
        assert "ำ" in compose_sara_am(unicodedata.normalize("NFKC", "สำนักงาน"))


class TestRepairMarks:
    def test_repairs_a_tone_mark_that_landed_after_a_following_vowel(self):
        # หน้า extracts as หนา้: the mark is ordered by horizontal position, not by base.
        assert repair_marks("หนา้") == "หน้า"

    def test_leaves_a_consonant_cluster_alone(self):
        # กล่าว is correct Thai with the mark on the *second* consonant of the cluster. It is
        # indistinguishable from the เลม่ corruption without a lexicon, so it is not touched.
        assert repair_marks("กล่าว") == "กล่าว"

    def test_leaves_correct_text_unchanged(self):
        assert repair_marks(GOOD_PAGE) == GOOD_PAGE

    def test_does_not_invent_a_mark_where_there_is_none(self):
        assert repair_marks("ข้อมูล") == "ข้อมูล"


class TestThaiRatio:
    def test_real_thai_prose_scores_high(self):
        assert thai_ratio(GOOD_PAGE) > 0.9

    def test_mojibake_scores_low(self):
        assert thai_ratio(MOJIBAKE_PAGE) < 0.5

    def test_pure_latin_scores_zero(self):
        assert thai_ratio("ROYAL DECREE ON SUPERVISION") == 0.0

    def test_an_empty_string_scores_zero_rather_than_dividing_by_it(self):
        assert thai_ratio("   ") == 0.0


class TestGazetteFurniture:
    def test_strips_the_masthead(self):
        page = "เลม่ ๑๓๖ ตอนที่ ๖๙ ก\n\nหนา้ ๕๗\nราชกิจจานุเบกษา\n\n๒๗ พฤษภาคม ๒๕๖๒\n\n" + GOOD_PAGE
        out = strip_gazette_furniture(page)
        assert "ราชกิจจานุเบกษา" not in out
        assert "ตอนที่" not in out

    def test_keeps_the_operative_text(self):
        page = "ราชกิจจานุเบกษา\n" + GOOD_PAGE
        assert "มาตรา ๙" in strip_gazette_furniture(page)


class TestWatermarkFragments:
    def test_removes_an_interleaved_watermark(self):
        # ETDA's "Unofficial Translated" watermark lands between sentences as Uno/ffic/ial/Tra.
        text = "Translation\nUno\nffic\nial\nTra\nROYAL DECREE\nnsl\nate\nd\nHis Majesty\nUno\nffic\nial\n"
        out = strip_watermark_fragments(text)
        assert "ROYAL DECREE" in out
        assert "His Majesty" in out
        assert "ffic" not in out

    def test_keeps_a_short_line_that_appears_once(self):
        assert "END" in strip_watermark_fragments("A sentence.\nEND\nAnother.")


class TestThaiSearchKey:
    def test_finds_a_title_across_numeral_systems_and_line_wrapping(self):
        # method.md §2's expected-phrase check aborted on a *correct* document for exactly this.
        wrapped = "พระราชกฤษฎีกา\n   ว่าด้วยการควบคุมดูแล พ.ศ. ๒๕๖๕"
        flat = "พระราชกฤษฎีกาว่าด้วยการควบคุมดูแล พ.ศ. 2565"
        assert thai_search_key(wrapped).replace(" ", "") == thai_search_key(flat).replace(" ", "")

    def test_folds_both_spellings_of_sara_am_together(self):
        assert thai_search_key("สํานักงาน") == thai_search_key("สำนักงาน")


class TestExtractThai:
    """`extract_thai` takes its pages from an injected reader, so the gates are testable without
    a Thai PDF — the traps live in the text, not in poppler."""

    def test_extracts_and_keeps_the_high_frequency_verb_searchable(self):
        out = extract_thai("gazette.pdf", reader=lambda path: [GOOD_PAGE])
        assert "กำหนด" in out

    def test_refuses_mojibake_rather_than_storing_plausible_garbage(self):
        with pytest.raises(ThaiMojibakeError) as e:
            extract_thai("bad.pdf", reader=lambda path: [MOJIBAKE_PAGE])
        assert "OCR" in str(e.value)

    def test_names_the_page_that_failed(self):
        # Fidelity varies within one document: the header extracts correctly while the body does
        # not, so "the file is bad" is not actionable and "page 2 is bad" is.
        with pytest.raises(ThaiMojibakeError) as e:
            extract_thai("bad.pdf", reader=lambda path: [GOOD_PAGE, MOJIBAKE_PAGE])
        assert "2" in str(e.value)

    def test_refuses_a_thai_document_with_no_sara_am_at_all(self):
        # In 241 KB of real Thai legal prose, zero U+0E33 is impossible; it means the typesetter
        # dropped every one. กำหนด occurs 87 times and matches zero.
        dropped = (GOOD_PAGE * 6).replace("ำ", "")
        with pytest.raises(ThaiSaraAmError) as e:
            extract_thai("gazette.pdf", reader=lambda path: [dropped])
        assert "U+0E33" in str(e.value)

    def test_a_short_thai_page_is_not_refused_for_want_of_a_sara_am(self):
        # At roughly 1.5% of Thai prose, a page can legitimately carry none. The check needs
        # enough text to be conclusive, or it aborts good documents.
        out = extract_thai("short.pdf", reader=lambda path: ["มาตรา ๙ ให้คณะกรรมการ\n"])
        assert "มาตรา" in out

    def test_both_refusals_share_a_prefix_so_a_caller_can_catch_the_family(self):
        with pytest.raises(ThaiTextError):
            extract_thai("bad.pdf", reader=lambda path: [MOJIBAKE_PAGE])
        assert ThaiMojibakeError.code.startswith("e.input.format.thai-text.")
        assert ThaiSaraAmError.code.startswith("e.input.format.thai-text.")

    def test_a_latin_page_is_not_judged_against_the_thai_gates(self):
        # ETDA publishes English translations. They are not mojibake for containing no Thai.
        out = extract_thai("en.pdf", reader=lambda path: ["ROYAL DECREE ON SUPERVISION\n"])
        assert "ROYAL DECREE" in out

    def test_never_applies_nfkc(self):
        out = extract_thai("gazette.pdf", reader=lambda path: [GOOD_PAGE])
        assert out == unicodedata.normalize("NFC", out)
        assert "ำ" in out

    def test_composes_sara_am_so_the_normal_spelling_finds_the_text(self):
        out = extract_thai("gazette.pdf", reader=lambda path: ["สํานักงานพัฒนาธุรกรรมทางอิเล็กทรอนิกส์\n"])
        assert "สำนักงาน" in out

    def test_strips_the_gazette_masthead_from_every_page(self):
        pages = ["ราชกิจจานุเบกษา\n" + GOOD_PAGE, "ราชกิจจานุเบกษา\n" + GOOD_PAGE]
        out = extract_thai("gazette.pdf", reader=lambda path: pages)
        assert "ราชกิจจานุเบกษา" not in out

    def test_refuses_an_empty_extraction_as_the_pdf_path_already_did(self):
        with pytest.raises(ThaiTextError) as e:
            extract_thai("blank.pdf", reader=lambda path: ["  ", ""])
        assert "OCR" in str(e.value)

    def test_the_refusal_is_permanent_not_transient(self):
        # Retrying pdftotext on the same bytes produces the same garbage.
        with pytest.raises(ThaiTextError) as e:
            extract_thai("bad.pdf", reader=lambda path: [MOJIBAKE_PAGE])
        assert e.value.transient is False


class TestExtractThaiWithPoppler:
    def test_the_default_reader_is_poppler(self, tmp_path):
        # The reader is injected for testing; by default it must be the real one, or the tests
        # above would be proving something about a stub.
        from lawcorpus import pdf, thai

        assert thai._poppler_pages.__module__ == thai.__name__
        with pytest.raises(pdf.PdfError):
            extract_thai(tmp_path / "nope.pdf")


# A bibliography page from a Thai instrument: Latin citations inside a Thai document. Four of the
# five documents `thailand-id` had refused looked like this, and all four were sound.
BIBLIOGRAPHY_PAGE = (
    "บรรณานุกรมและเอกสารอ้างอิงประกอบ\n"
    "Bygrave, Lee A. Data Privacy Law: An International Perspective. Oxford University Press, 2014.\n"
    "Greenleaf, Graham. Asian Data Privacy Laws: Trade and Human Rights Perspectives. Oxford, 2014.\n"
)


class TestWordLikeness:
    """@szp4xt3n — the share of a page's Latin runs that read as words. Three letters or more with
    a vowel, which is crude on purpose: prose and the residue of a broken encoding differ by an
    order of magnitude rather than at the margin."""

    def test_real_citations_score_in_the_band_thailand_id_measured(self):
        share, runs = word_likeness(BIBLIOGRAPHY_PAGE)
        assert runs >= 8
        assert share >= 0.9

    def test_mojibake_scores_an_order_of_magnitude_lower(self):
        share, runs = word_likeness(MOJIBAKE_PAGE)
        assert runs >= 8
        assert share < 0.5

    def test_a_page_with_no_latin_at_all_scores_zero_and_says_so(self):
        assert word_likeness(GOOD_PAGE) == (0.0, 0)

    def test_a_run_of_two_letters_counts_as_a_run_but_never_as_a_word(self):
        assert word_likeness("by an") == (0.0, 2)

    def test_a_vowelless_run_is_not_a_word_however_long(self):
        assert word_likeness("TCPDF") == (0.0, 1)


class TestTheMojibakeGateSparesAMixedScriptPage:
    """@szp4xt3n — a gate that refuses good documents gets turned off, which is worse than no
    gate. Five documents were refused in `thailand-id` and four of them were sound."""

    def test_a_bibliography_page_is_no_longer_refused(self):
        out = extract_thai("th.pdf", reader=lambda path: [GOOD_PAGE, BIBLIOGRAPHY_PAGE])
        assert "Bygrave" in out
        assert "กำหนด" in out

    def test_genuine_mojibake_is_still_refused(self):
        with pytest.raises(ThaiMojibakeError):
            extract_thai("bad.pdf", reader=lambda path: [MOJIBAKE_PAGE])

    def test_the_refusal_names_the_word_score_it_judged_on(self):
        with pytest.raises(ThaiMojibakeError) as e:
            extract_thai("bad.pdf", reader=lambda path: [MOJIBAKE_PAGE])
        assert "read as words" in str(e.value)

    def test_too_few_latin_runs_to_judge_stays_fail_closed(self):
        # Below the floor the score is noise, so the page is refused as it was before.
        page = "มาตรา ๙ ให้คณะ BCDFGHJKLMNP QRSTVWXZBCDF\n"
        with pytest.raises(ThaiMojibakeError) as e:
            extract_thai("bad.pdf", reader=lambda path: [page])
        assert "too few" in str(e.value)


class TestTheToneMarkGate:
    """@h4srdl2g — the DOPA manual keeps its sara am and loses every tone mark, so it passes both
    existing gates: `สราง` for `สร้าง`, `ใหม` for `ใหม่`, `พิสูจน` for `พิสูจน์`."""

    def test_refuses_a_thai_document_with_no_tone_mark_at_all(self):
        stripped = (GOOD_PAGE * 6).translate({ord(ch): None for ch in "่้๊๋"})
        with pytest.raises(ThaiToneMarkError) as e:
            extract_thai("dopa.pdf", reader=lambda path: [stripped])
        assert "U+0E48" in str(e.value)

    def test_it_names_what_failed_rather_than_that_something_did(self):
        stripped = (GOOD_PAGE * 6).translate({ord(ch): None for ch in "่้๊๋"})
        with pytest.raises(ThaiToneMarkError) as e:
            extract_thai("dopa.pdf", reader=lambda path: [stripped])
        assert "tone mark" in str(e.value)
        assert "OCR" in str(e.value)

    def test_the_document_that_passes_the_other_two_gates_is_caught_by_this_one(self):
        stripped = (GOOD_PAGE * 6).translate({ord(ch): None for ch in "่้๊๋"})
        assert "ำ" in stripped  # the sara-am gate is satisfied
        assert thai_ratio(stripped) > 0.9  # and so is the mojibake gate

    def test_a_sound_document_passes(self):
        out = extract_thai("gazette.pdf", reader=lambda path: [GOOD_PAGE * 6])
        assert "คุ้มครอง" in out

    def test_a_short_thai_document_is_not_refused_for_want_of_a_tone_mark(self):
        # Below the floor, none is a document that happens not to need one.
        out = extract_thai("short.pdf", reader=lambda path: ["มาตรา ๙ ให้คณะกรรมการ\n"])
        assert "มาตรา" in out

    def test_it_joins_the_family_a_caller_already_catches(self):
        assert ThaiToneMarkError.code.startswith("e.input.format.thai-text.")
        stripped = (GOOD_PAGE * 6).translate({ord(ch): None for ch in "่้๊๋"})
        with pytest.raises(ThaiTextError):
            extract_thai("dopa.pdf", reader=lambda path: [stripped])
