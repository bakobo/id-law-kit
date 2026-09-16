"""PDF text extraction.

The last resort of the three renderers in this package, and the only one whose output cannot be
trusted structurally. Formex and CAML are markup: what you get out is what the publisher put in.
A PDF is a page description, so extraction invents a reading order and interleaves furniture —
running headers, footers, page numbers — into the middle of sentences.

That matters more here than it would elsewhere. A running footer landing between "the business
shall" and "not retain" produces text that greps wrong and reads wrong, and nothing about it looks
broken.
"""

import pytest

from lawcorpus.pdf import (
    STRUCTURAL_OPENERS,
    PdfError,
    UnknownTraditionError,
    clean_pages,
    strip_repeated_furniture,
    structural_pattern,
)

PAGES = [
    "TEXT OF REGULATIONS\n\n§ 7001. Definitions.\n\n(a) 'Agency' means the California\n"
    "Privacy Protection Agency.\n\nCA PRIVACY PROTECTION AGENCY\nPage 1 of 3",
    "TEXT OF REGULATIONS\n\n(b) 'Attorney General' means the California\n"
    "Attorney General.\n\nCA PRIVACY PROTECTION AGENCY\nPage 2 of 3",
    "TEXT OF REGULATIONS\n\n§ 7002. Restrictions on collection.\n\n"
    "A business shall collect only what is necessary.\n\nCA PRIVACY PROTECTION AGENCY\nPage 3 of 3",
]


class TestStripRepeatedFurniture:
    def test_removes_a_header_that_appears_on_every_page(self):
        out = strip_repeated_furniture(PAGES)
        assert all("TEXT OF REGULATIONS" not in p for p in out)

    def test_removes_a_footer_that_appears_on_every_page(self):
        out = strip_repeated_furniture(PAGES)
        assert all("CA PRIVACY PROTECTION AGENCY" not in p for p in out)

    def test_removes_page_numbers_even_though_each_is_unique(self):
        # "Page 1 of 3" never repeats verbatim, so frequency alone will not catch it.
        out = strip_repeated_furniture(PAGES)
        assert all("Page 1 of 3" not in p for p in out)
        assert all("Page 2 of 3" not in p for p in out)

    def test_keeps_the_operative_text(self):
        out = "\n".join(strip_repeated_furniture(PAGES))
        assert "'Agency' means the California" in out
        assert "A business shall collect only what is necessary." in out

    def test_keeps_a_line_that_merely_looks_like_a_header_but_appears_once(self):
        pages = ["HEADER\nreal text one\nFOOTER", "HEADER\nSPECIAL NOTICE\nFOOTER"]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "SPECIAL NOTICE" in out

    def test_a_single_page_document_keeps_everything(self):
        # With one page there is no repetition to measure, so nothing may be inferred as furniture.
        page = "TITLE\n\nSome text.\n\nFOOTER"
        assert strip_repeated_furniture([page]) == [page]

    def test_only_looks_at_the_edges_of_a_page(self):
        # A phrase repeated in the body of every page is a defined term, not furniture.
        pages = [
            "H\n" + "\n".join([f"line {i}" for i in range(10)] + ["personal information"]
                               + [f"line {i}" for i in range(10)]) + "\nF",
            "H\n" + "\n".join([f"row {i}" for i in range(10)] + ["personal information"]
                               + [f"row {i}" for i in range(10)]) + "\nF",
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "personal information" in out

    def test_handles_empty_pages(self):
        assert strip_repeated_furniture(["", "text"]) is not None


class TestCleanPages:
    def test_joins_pages_into_one_document(self):
        out = clean_pages(PAGES)
        assert "§ 7001." in out and "§ 7002." in out

    def test_does_not_leave_form_feeds(self):
        assert "\f" not in clean_pages(PAGES)

    def test_rejoins_a_sentence_split_across_a_line_break(self):
        # pdftotext hard-wraps at the PDF's line boundaries. Left alone, a search for
        # "the California Privacy Protection Agency" spans a newline and fails.
        assert "means the California Privacy Protection Agency." in clean_pages(PAGES)

    def test_keeps_section_headings_on_their_own_line(self):
        assert "\n§ 7002. Restrictions on collection." in clean_pages(PAGES)

    def test_normalises_layout_only_characters(self):
        assert "Section 7001" in clean_pages(["Section 7001 applies."])

    def test_collapses_runs_of_blank_lines(self):
        assert "\n\n\n" not in clean_pages(["a\n\n\n\n\n\nb"])

    def test_rejects_no_pages(self):
        with pytest.raises(PdfError) as e:
            clean_pages([])
        assert e.value.transient is False

    def test_rejects_pages_that_are_all_whitespace(self):
        # A PDF with no text layer extracts to nothing. That is a scanned document needing OCR,
        # not an empty regulation, and storing it would put a blank entry in the corpus.
        with pytest.raises(PdfError) as e:
            clean_pages(["", "   \n\n  "])
        assert "text layer" in str(e.value).lower()


def minimal_pdf(pages_of_lines) -> bytes:
    """A valid multi-page PDF built by hand.

    Hermetic on purpose: the test suite should need poppler and nothing else. Pulling in
    ghostscript or a PDF-writing library just to produce a fixture would add a second binary
    dependency to CI for no gain.
    """
    objects, contents = [], []
    for lines in pages_of_lines:
        body = ["BT /F1 12 Tf 72 720 Td 14 TL"]
        for line in lines:
            escaped = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            body.append(f"({escaped}) Tj T*")
        body.append("ET")
        contents.append("\n".join(body).encode("latin-1"))

    n_pages = len(contents)
    page_ids = [3 + i for i in range(n_pages)]
    content_ids = [3 + n_pages + i for i in range(n_pages)]
    font_id = 3 + 2 * n_pages

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{i} 0 R" for i in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    for page_id, content_id in zip(page_ids, content_ids):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
    for stream in contents:
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


pdftotext_required = pytest.mark.skipif(
    __import__("shutil").which("pdftotext") is None, reason="poppler-utils not installed"
)


@pdftotext_required
class TestExtract:
    def test_extracts_text_from_a_real_pdf(self, tmp_path):
        from lawcorpus.pdf import extract

        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(minimal_pdf([["SECTION ONE", "The business shall comply."]]))
        assert "The business shall comply." in extract(pdf)

    def test_strips_running_furniture_across_real_pages(self, tmp_path):
        from lawcorpus.pdf import extract

        pdf = tmp_path / "b.pdf"
        pdf.write_bytes(
            minimal_pdf(
                [
                    ["TEXT OF REGULATIONS", "First operative sentence.", "Page 1 of 3"],
                    ["TEXT OF REGULATIONS", "Second operative sentence.", "Page 2 of 3"],
                    ["TEXT OF REGULATIONS", "Third operative sentence.", "Page 3 of 3"],
                ]
            )
        )
        out = extract(pdf)
        assert "First operative sentence." in out
        assert "Third operative sentence." in out
        assert "TEXT OF REGULATIONS" not in out
        assert "Page 2 of 3" not in out

    def test_a_missing_file_is_named(self, tmp_path):
        from lawcorpus.pdf import PdfError, extract

        with pytest.raises(PdfError) as e:
            extract(tmp_path / "nope.pdf")
        assert "nope.pdf" in str(e.value)

    def test_a_pdf_with_no_text_layer_is_refused(self, tmp_path):
        from lawcorpus.pdf import PdfError, extract

        pdf = tmp_path / "blank.pdf"
        pdf.write_bytes(minimal_pdf([[], []]))
        with pytest.raises(PdfError) as e:
            extract(pdf)
        assert "text layer" in str(e.value).lower()

    def test_a_corrupt_pdf_reports_the_extractor_failure(self, tmp_path):
        from lawcorpus.pdf import PdfError, extract

        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"%PDF-1.4\nthis is not a pdf\n")
        with pytest.raises(PdfError) as e:
            extract(pdf)
        assert "pdftotext" in str(e.value)


class TestExtractWithoutPoppler:
    def test_a_missing_pdftotext_says_how_to_install_it(self, tmp_path, monkeypatch):
        import lawcorpus.pdf as mod

        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        monkeypatch.setattr(mod.shutil, "which", lambda name: None)
        with pytest.raises(mod.PdfError) as e:
            mod.extract(pdf)
        assert "poppler" in str(e.value)


class TestALetteredSectionNumberOpensABlock:
    """@zr3b5ll2 — `23A.` was not a structural opener, so the marginal note above it was welded
    onto the heading and the section stopped being line-anchored. Measured on NRA 1965: 33 of 34
    sections scan and the one that fails is the lettered one.
    """

    def test_a_plain_numeric_heading_was_already_safe(self):
        out = clean_pages(["Marginal note\n17.—(1) A person must register."])
        assert "\n17.—(1) A person must register." in out

    def test_a_lettered_heading_is_no_longer_welded_to_the_line_above(self):
        out = clean_pages(["Marginal note\n23A.—(1) The Registrar may issue."])
        assert "\n23A.—(1) The Registrar may issue." in out

    def test_the_whole_of_part_2a_survives(self):
        # ss.16A-16S of the Electronic Transactions Act 2010 — singapore-id's central finding.
        page = "\n".join(f"Marginal note\n16{letter}.—(1) Provision text." for letter in "AOS")
        out = clean_pages([page])
        for letter in "AOS":
            assert f"\n16{letter}.—(1) Provision text." in out

    def test_a_wrapped_sentence_is_still_rejoined(self):
        # The change must not turn every capitalised continuation into a new block.
        out = clean_pages(["means the California\nPrivacy Protection Agency."])
        assert "means the California Privacy Protection Agency." in out


SSO_PAGES = [
    "2020 Ed.   National Registration Act 1965   4\n"
    "(a) the name and sex of every person registered\nand the address of that person.",
    "5   National Registration Act 1965   2020 Ed.\n"
    "(b) either generally or specially and subject\nto any conditions imposed.",
    "2020 Ed.   National Registration Act 1965   6\n"
    "(c) the Registrar may require a person to\nfurnish such particulars.",
    "7   National Registration Act 1965   2020 Ed.\n"
    "(d) no person shall be required to furnish\nany particulars twice.",
]


class TestFurnitureWithAnEmbeddedPageNumber:
    """@ly7tho4y — SSO writes the page number inside the running head, so no two pages carry the
    same string and the repeated-text rule finds nothing. Measured on the PDPA: 124 of 124 footers
    stripped, and the header surviving on 120 of 123 pages.
    """

    def test_the_running_head_goes_even_though_no_two_pages_match(self):
        out = "\n".join(strip_repeated_furniture(SSO_PAGES))
        assert "National Registration Act 1965" not in out

    def test_both_the_recto_and_the_verso_form_go(self):
        # Printed legal publishing mirrors the head, so each form is on about half the pages and
        # no threshold above one half can see either.
        out = strip_repeated_furniture(SSO_PAGES)
        assert not any("2020 Ed." in page for page in out)

    def test_the_operative_text_survives(self):
        out = "\n".join(strip_repeated_furniture(SSO_PAGES))
        assert "the name and sex of every person registered" in out
        assert "no person shall be required to furnish" in out

    def test_a_line_whose_number_does_not_count_up_with_the_pages_is_kept(self):
        # "Constant except for a number" also describes a numbered table, and eating content to
        # remove furniture is worse than the furniture.
        pages = [f"Form {n} of the Schedule\nbody {n} here" for n in (3, 1, 4, 2)]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("Form") == 4

    def test_a_shape_with_no_letters_is_left_to_the_page_number_rule(self):
        pages = [f"{n}\nparagraph {letter} of the Act" for n, letter in enumerate("abcd", start=1)]
        out = strip_repeated_furniture(pages)
        assert all(page.startswith("paragraph ") for page in out)

    def test_a_repeated_line_with_no_number_in_it_needs_the_text_rule_and_its_threshold(self):
        # Two of five pages is below FURNITURE_THRESHOLD and below the shape rule's floor of two.
        pages = ["NOTICE\nbody one", "NOTICE\nbody two", "a\nb", "c\nd", "e\nf"]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("NOTICE") == 2

    def test_a_shape_appearing_on_too_few_pages_is_kept(self):
        pages = [f"Table {n} follows\nbody {n}" for n in range(1, 3)] + [
            f"unrelated {n}\nbody {n}" for n in range(3, 9)
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("Table") == 2

    def test_a_head_carrying_thai_digits_is_recognised_too(self):
        # The digit runs are read through the one numeral table, not through ASCII alone.
        pages = [f"หน้า ๔{d}   ราชกิจจานุเบกษา\nเนื้อหา {d}" for d in "๑๒๓๔"]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "ราชกิจจานุเบกษา" not in out


class TestTheShapeRuleCountsThePagesAHeadCovers:
    """@lbqi475m — the denominator was every page, and only pages carrying a head can vote."""

    def test_a_mirrored_head_survives_front_matter_that_does_not_carry_it(self):
        # singapore-id, Interpretation Act 1965: 63 pages of which 18 are front matter with no
        # running head, mirrored templates on 22 and 23 of the remaining 45, against a bar of 25.
        front = [f"ARRANGEMENT OF SECTIONS\nsection {n} is listed here" for n in range(1, 19)]
        body = [
            (
                f"2020 Ed.   Interpretation Act 1965   {n}"
                if n % 2 == 0
                else f"{n}   Interpretation Act 1965   2020 Ed."
            )
            + f"\nprovision text {chr(96 + n - 18)} of the Act"
            for n in range(19, 64)
        ]
        out = "\n".join(strip_repeated_furniture(front + body))
        assert "Interpretation Act 1965" not in out
        assert "provision text a of the Act" in out
        assert "section 1 is listed here" in out

    def test_a_template_confined_to_a_corner_of_a_document_is_still_kept(self):
        # The span must itself reach the document, or a template on pages 1 and 2 of sixty scores
        # two of two and is deleted.
        pages = [f"Table {n} follows\nbody {n}" for n in range(1, 3)] + [
            f"unrelated {n}\nbody {n}" for n in range(3, 61)
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("Table") == 2

    def test_a_mirrored_head_is_stripped_on_a_two_page_document(self):
        # japan-id measured the old floor stripping a mirrored head on 0 of 2 pages and 2 of 3,
        # because each half holds only half the evidence and the floor is an absolute 2.
        pages = [
            "Gazette   Ministry of Justice   1\nfirst provision text",
            "2   Ministry of Justice   Gazette\nsecond provision text",
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "Ministry of Justice" not in out
        assert "first provision text" in out
        assert "second provision text" in out

    def test_a_mirrored_head_is_stripped_on_a_three_page_document(self):
        pages = [
            "Gazette   Ministry of Justice   1\nfirst provision text",
            "2   Ministry of Justice   Gazette\nsecond provision text",
            "Gazette   Ministry of Justice   3\nthird provision text",
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "Ministry of Justice" not in out
        assert "third provision text" in out

    def test_a_non_mirrored_head_still_fires_at_every_length_from_two_up(self):
        # indonesia-id measured the rule firing at every length from 2 to 11 pages, and that must
        # stay true: the floor is right for a head that appears on every page.
        for count in range(2, 12):
            pages = [f"Gazette Volume 4 page {n}\nbody text {n}" for n in range(1, count + 1)]
            out = "\n".join(strip_repeated_furniture(pages))
            assert "Gazette Volume" not in out, count


class TestTheShapeRuleNeverDeletesAProvisionHeading:
    """@lbqi475m — a Pasal heading counts up with the pages too, so the safety premise was false."""

    def test_an_article_heading_that_counts_up_with_the_pages_is_kept(self):
        # indonesia-id, on a synthetic statute at 6, 12 and 40 pages: 0 of 40 headings kept.
        pages = [
            f"Pasal {n}\n"
            + "\n".join(f"Uraian {chr(96 + n)}{k} tentang ketentuan ini." for k in range(1, 6))
            for n in range(1, 41)
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("Pasal ") == 40

    def test_a_chapter_heading_that_counts_up_with_the_pages_is_kept(self):
        pages = [
            f"BAB {n}\n" + "\n".join(f"Uraian {chr(96 + n)}{k} lebih lanjut." for k in range(1, 6))
            for n in range(1, 13)
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("BAB ") == 12

    def test_a_japanese_article_heading_that_counts_up_is_kept(self):
        pages = [f"第{n}条\n規定の内容{chr(96 + n)}について。" for n in range(1, 13)]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("条") == 12

    def test_a_repeated_all_caps_running_head_still_goes_by_the_text_rule(self):
        # The exclusion is applied to the shape rule only: identical text on most pages cannot be
        # distinct provisions, so repetition of the literal string is proof in a way a shape is not.
        pages = [
            f"REPUBLIK INDONESIA\n- {n} -\nPasal {n}\nIsi ketentuan {chr(96 + n)} di sini."
            for n in range(1, 13)
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "REPUBLIK INDONESIA" not in out
        assert out.count("Pasal ") == 12


def _noisy_indonesian_pages(count: int = 12) -> list:
    """Pages whose head is an emblem OCR'd into five lines of noise, as Perpres 95/2018's are."""
    noise = "˝\n' '\n. ..\n|\n~ ~"
    return [
        f"{noise}\nREPUBLIK INDONESIA\n- {n} -\nPasal {n}\n"
        + "\n".join(f"Uraian {chr(96 + n)}{k} tentang ketentuan ini." for k in range(1, 15))
        for n in range(1, count + 1)
    ]


class TestTheEdgeWindows:
    """@kbdz5bmq — two windows, because only the page-number rule is evidence-free."""

    def test_a_running_head_below_five_lines_of_scanner_noise_is_stripped(self):
        # indonesia-id, Perpres 95/2018: 0 of 112 REPUBLIK INDONESIA heads stripped, because the
        # emblem OCRs into three to six lines and the head lands at line index 5 to 7.
        out = "\n".join(strip_repeated_furniture(_noisy_indonesian_pages()))
        assert "REPUBLIK INDONESIA" not in out

    def test_a_page_marker_below_the_noise_goes_on_the_evidence_every_template_needs(self):
        # 123 of 134 standalone -N- markers were left, and each survivor is an unterminated line
        # the rejoiner then welds to the heading beneath it.
        out = "\n".join(strip_repeated_furniture(_noisy_indonesian_pages()))
        assert "- 7 -" not in out

    def test_the_provision_headings_under_all_of_that_survive(self):
        out = "\n".join(strip_repeated_furniture(_noisy_indonesian_pages()))
        assert out.count("Pasal ") == 12
        assert "Uraian a1 tentang ketentuan ini." in out

    def test_a_bare_number_deep_in_a_page_is_not_a_page_number(self):
        # Position is the only evidence _PAGE_NUMBER has, so it keeps the tight window. A constant
        # number at depth does not count up, so the shape rule does not reach it either.
        # The number differs per page and does not count up, so it is neither a repeated line nor
        # a template with a rising field: nothing but its position could condemn it, and it is out
        # of reach of the only rule that reads position.
        marks = [42, 17, 88, 5, 63, 9, 71, 24, 96, 33, 50, 12]
        pages = [
            f"opening {chr(96 + n)} one\nopening {chr(96 + n)} two\nopening {chr(96 + n)} three\n"
            f"opening {chr(96 + n)} four\n{marks[n - 1]}\n"
            + "\n".join(f"body {chr(96 + n)}{k} of the page." for k in range(1, 9))
            for n in range(1, 13)
        ]
        out = "\n".join(strip_repeated_furniture(pages))
        assert all(str(mark) in out for mark in marks)

    def test_the_window_counts_the_same_lines_when_a_page_opens_with_blanks(self):
        # _edge_lines counted non-blank lines while the strip loop counted raw ones.
        pages = [f"\n\n\nRUNNING HEAD\nbody {chr(96 + n)} of the page." for n in range(1, 6)]
        out = "\n".join(strip_repeated_furniture(pages))
        assert "RUNNING HEAD" not in out


class TestStructuralOpenersPerTradition:
    """@zzqzaku4 — the opener list was number-leading, and most of the world puts the label first."""

    @pytest.mark.parametrize(
        "line",
        [
            "Pasal 13",
            "Pasal 13A",
            "PASAL 13",
            "BAB I",
            "BAB XVII",
            "Bagian Kesatu",
            "BAGIAN KEDUA",
            "Paragraf 2",
            "PARAGRAF 2",
            "Menimbang:",
            "Mengingat:",
            "MEMUTUSKAN:",
            "Menetapkan:",
            "MENETAPKAN:",
            "PRESIDEN REPUBLIK INDONESIA",
            "UNDANG-UNDANG NOMOR 27 TAHUN 2022",
            "PERATURAN PEMERINTAH",
            "PENJELASAN",
            "LAMPIRAN I",
            "a. bahwa perlindungan data pribadi",
            "1. Ketentuan umum",
        ],
    )
    def test_an_indonesian_opener_is_structural(self, line):
        assert structural_pattern().match(line), line

    @pytest.mark.parametrize("line", ["มาตรา ๗", "หมวด ๑", "ส่วนที่ ๒", "ภาค ๓", "ลักษณะ ๑"])
    def test_a_thai_opener_is_structural(self, line):
        assert structural_pattern().match(line), line

    @pytest.mark.parametrize("line", ["第十八条", "第18条", "第一章", "第二節", "第三款"])
    def test_a_japanese_opener_is_structural(self, line):
        assert structural_pattern().match(line), line

    @pytest.mark.parametrize("line", ["23A.", "§ 7001.", "(a) means", "ARTICLE III", "Note:"])
    def test_a_common_law_opener_is_still_structural(self, line):
        assert structural_pattern().match(line), line

    def test_bab_one_is_the_case_the_all_caps_rule_cannot_reach(self):
        # indonesia-id's sharpest observation: the all-caps rule matches BAB XVII and fails BAB I,
        # which welds exactly the chapters an ordering check would have caught.
        assert not structural_pattern("common-law").match("BAB I")
        assert structural_pattern("common-law").match("BAB XVII")
        assert structural_pattern("indonesian").match("BAB I")

    def test_a_subset_of_traditions_can_be_asked_for(self):
        assert structural_pattern("common-law").match("23A.")
        assert not structural_pattern("common-law").match("Pasal 13")

    def test_an_unknown_tradition_is_refused_rather_than_ignored(self):
        with pytest.raises(UnknownTraditionError) as excinfo:
            structural_pattern("javanese")
        assert "javanese" in str(excinfo.value)
        assert "indonesian" in str(excinfo.value)

    def test_the_registry_names_the_four_traditions_the_programme_has_evidence_for(self):
        assert set(STRUCTURAL_OPENERS) == {"common-law", "indonesian", "thai", "japanese"}

    def test_an_indonesian_heading_is_not_welded_to_the_line_above(self):
        out = clean_pages(["ditetapkan lebih lanjut oleh Menteri\nPasal 14\nSetiap orang berhak."])
        assert "Menteri Pasal 14" not in out
        assert "\nPasal 14" in out

    def test_a_wrapped_indonesian_sentence_is_still_rejoined(self):
        out = clean_pages(["setiap orang berhak atas pelindungan\ndata pribadi tentang dirinya."])
        assert "pelindungan data pribadi tentang dirinya." in out

    def test_a_numeric_template_that_is_not_a_page_marker_is_left_alone(self):
        # A field and no letter, and not a page number either: a ratio, a date, a table cell. The
        # shape rule admits a letterless template only when the whole line is a page marker.
        pages = [f"{n}/4\nclause {chr(96 + n)} of the Schedule" for n in range(1, 13)]
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("/4") == 12

    def test_a_template_that_is_sparse_across_the_span_it_covers_is_kept(self):
        # Span and density are separate conditions: reaching from the first page to the last is
        # not enough if the template is on two of the twenty pages between them.
        pages = (
            ["Annex 1 to the Order\nbody one"]
            + [f"unrelated {chr(96 + n)}\nbody {chr(96 + n)}" for n in range(2, 20)]
            + ["Annex 2 to the Order\nbody twenty"]
        )
        out = "\n".join(strip_repeated_furniture(pages))
        assert out.count("to the Order") == 2
