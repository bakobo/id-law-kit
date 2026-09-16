"""Japanese PDFs, where the general cleaner welds a space into the middle of a phrase.

`pdf.py`'s rejoiner is English. `_UNTERMINATED` calls a line mid-sentence unless it ends in
`.:;?!`, so every Japanese line ending in 。 is judged unfinished and joined to the next — with a
space, which Japanese does not write between words. 「③発行者の電子署名から構成される」 becomes
「③発行者の 電子署名から構成される」 and cannot be found at all: the cleaner manufacturing the false
negative, not the PDF.

So `pdf.clean_pages` gates, following `thai.py`, and this module carries the working path. See
this.i @3i2xqflu.
"""

import pytest

from lawcorpus.japanese import (
    JapaneseScriptError,
    cjk_ratio,
    clean_japanese_pages,
    extract_japanese,
)
from lawcorpus.pdf import PdfError, clean_pages

# The Digital Agency slide, wrapped the way pdftotext emits it.
WRAPPED = "\n".join(
    [
        "③発行者の",
        "電子署名から構成される。",
        "なお、国際標準としては",
        "ISO18013-5のmdoc data modelを採用する。",
    ]
)


class TestTheEnglishPathRefusesRatherThanCorrupts:
    def test_it_welded_a_space_into_the_phrase_before_this_gate_existed(self):
        """The defect, stated as the reason the gate is here."""
        assert "電子署名" in WRAPPED
        assert "発行者の電子署名" not in WRAPPED  # wrapped across a line, as extracted

    def test_clean_pages_refuses_a_japanese_extraction(self):
        with pytest.raises(PdfError) as e:
            clean_pages([WRAPPED])
        assert "japanese" in str(e.value).lower()

    def test_the_refusal_names_the_module_that_handles_it(self):
        with pytest.raises(PdfError) as e:
            clean_pages([WRAPPED])
        assert "extract_japanese" in str(e.value)

    def test_an_english_document_is_unaffected(self):
        out = clean_pages(["A business uses the technology's output\nto replace human judgment."])
        assert "output to replace" in out

    def test_a_stray_kanji_in_an_english_document_does_not_trip_it(self):
        english = "The term 個人情報 appears once in this otherwise English page. " * 8
        assert clean_pages([english])

    def test_korean_is_not_gated_because_it_writes_word_spaces(self):
        korean = "제1조 이 법은 개인정보 보호에 관한 사항을 규정한다. " * 8
        assert clean_pages([korean])


class TestTheRatio:
    def test_a_page_with_no_letters_scores_zero(self):
        assert cjk_ratio("123 456 -- ...") == 0.0

    def test_japanese_prose_scores_high(self):
        assert cjk_ratio("個人情報の保護に関する法律") > 0.9

    def test_english_scores_zero(self):
        assert cjk_ratio("the law nowhere requires this") == 0.0


class TestTheJapaneseCleaner:
    def test_it_rejoins_with_no_separator(self):
        out = clean_japanese_pages([WRAPPED])
        assert "③発行者の電子署名から構成される。" in out

    def test_a_terminated_line_never_absorbs_the_one_below(self):
        out = clean_japanese_pages(["電子署名から構成される。", "なお、国際標準としては"])
        assert "構成される。なお" not in out

    def test_a_bullet_opens_a_new_block(self):
        out = clean_japanese_pages(["マイナンバーカードの", "※ 本資料は参考である"])
        assert "カードの※" not in out

    def test_a_circled_enumerator_opens_a_new_block(self):
        out = clean_japanese_pages(["カード代替電磁的記録は", "③発行者の電子署名"])
        assert "記録は③" not in out

    def test_a_line_opening_in_latin_is_not_absorbed(self):
        out = clean_japanese_pages(["採用するのは", "ISO18013-5である。"])
        assert "採用するのはISO" not in out

    def test_a_blank_line_ends_a_join(self):
        out = clean_japanese_pages(["個人情報の", "", "保護に関する法律"])
        assert "個人情報の保護" not in out

    def test_the_layout_fold_still_runs(self):
        assert "(" in clean_japanese_pages(["第一条（定義）"])

    def test_furniture_is_removed_across_pages(self):
        pages = [f"デジタル庁\n本文{n}である。\nPage {n} of 3" for n in (1, 2, 3)]
        out = clean_japanese_pages(pages)
        assert "デジタル庁" not in out

    def test_an_empty_page_set_is_a_failure_not_a_document(self):
        with pytest.raises(JapaneseScriptError):
            clean_japanese_pages([])

    def test_a_page_set_of_whitespace_is_refused(self):
        with pytest.raises(JapaneseScriptError) as e:
            clean_japanese_pages(["   \n  ", ""])
        assert "OCR" in str(e.value)

    def test_it_refuses_a_page_set_that_is_not_japanese(self):
        with pytest.raises(JapaneseScriptError) as e:
            clean_japanese_pages(["the law nowhere requires this, and it never has"])
        assert "%" in str(e.value)

    def test_runs_of_blank_lines_collapse(self):
        assert "\n\n\n" not in clean_japanese_pages(["第一条\n\n\n\n第二条"])


class TestExtractJapanese:
    def test_the_reader_is_injectable_so_the_traps_can_be_tested(self):
        out = extract_japanese("ignored.pdf", reader=lambda path: [WRAPPED])
        assert "③発行者の電子署名から構成される。" in out

    def test_it_goes_through_poppler_by_default(self, monkeypatch):
        seen = {}

        def fake_raw_pages(path, layout=True):
            seen["path"] = path
            return [WRAPPED]

        monkeypatch.setattr("lawcorpus.japanese.raw_pages", fake_raw_pages)
        out = extract_japanese("some.pdf")
        assert str(seen["path"]).endswith("some.pdf")
        assert "電子署名から構成される" in out
