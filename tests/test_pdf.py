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

from lawcorpus.pdf import PdfError, clean_pages, strip_repeated_furniture

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
