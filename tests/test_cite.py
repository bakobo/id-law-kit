"""The citation primitive.

Quotes never print without a validity banner. That is the whole point: an agent obeying
quote-or-drop over a struck-down provision produces a confidently false claim, and a document
telling it to be careful is not enough. See this.i @xrfhyv.
"""

import pytest

from lawcorpus.cite import Corpus, CorpusError, main
from lawcorpus.manifest import Manifest, ManifestItem
from lawcorpus.store import CorpusStore

GDPR = "Article 5\nPersonal data shall be processed lawfully, fairly and transparently.\n"
STRUCK = "57. Nothing contained in this Act shall prevent the use of the Aadhaar number...\n"


def item(**over):
    base = dict(
        item_id="32016R0679",
        citation="Regulation (EU) 2016/679",
        title="GDPR",
        authority_tier="legislative",
        validity="in-force",
        validity_note="",
        translation_status="authoritative",
        translation_of="",
        version_id="02016R0679-20160504",
        lang="eng",
        source_url="http://publications.europa.eu/resource/celex/32016R0679",
        retrieved="2026-07-31",
        media_type="application/xml",
        bytes=len(GDPR.encode()),
        sha256="0" * 64,
    )
    base.update(over)
    return ManifestItem(**base)


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "corpus"
    store = CorpusStore(root)
    a = store.write("32016R0679", GDPR)
    b = store.write("aadhaar-s57", STRUCK)
    Manifest(
        [
            item(sha256=a.sha256, bytes=a.bytes),
            item(
                item_id="aadhaar-s57",
                citation="Aadhaar Act 2016 s.57",
                title="Aadhaar Act, section 57",
                validity="struck-down",
                validity_note="K.S. Puttaswamy v. Union of India (2018) 1 SCC 1",
                sha256=b.sha256,
                bytes=b.bytes,
            ),
        ]
    ).write(root / "MANIFEST.tsv")
    return Corpus(root)


class TestQuote:
    def test_returns_the_stored_text(self, corpus):
        assert GDPR in corpus.quote("32016R0679")

    def test_prefixes_an_in_force_banner(self, corpus):
        assert corpus.quote("32016R0679").startswith("[in force]")

    def test_a_struck_down_quote_shouts_before_the_text(self, corpus):
        out = corpus.quote("aadhaar-s57")
        assert out.index("STRUCK DOWN") < out.index("Nothing contained")

    def test_a_struck_down_quote_names_the_judgment(self, corpus):
        assert "Puttaswamy" in corpus.quote("aadhaar-s57")

    def test_includes_the_citation_and_retrieval_date(self, corpus):
        out = corpus.quote("32016R0679")
        assert "Regulation (EU) 2016/679" in out
        assert "2026-07-31" in out

    def test_includes_the_version_that_was_pinned(self, corpus):
        # A citation that does not say which consolidation it means is not checkable.
        assert "02016R0679-20160504" in corpus.quote("32016R0679")

    def test_unknown_item_names_what_is_available(self, corpus):
        with pytest.raises(CorpusError) as e:
            corpus.quote("nope")
        assert "nope" in str(e.value)

    def test_refuses_when_the_stored_text_no_longer_matches_the_manifest(self, tmp_path):
        root = tmp_path / "corpus"
        store = CorpusStore(root)
        store.write("x", GDPR)
        Manifest([item(item_id="x", sha256="f" * 64)]).write(root / "MANIFEST.tsv")
        with pytest.raises(CorpusError) as e:
            Corpus(root).quote("x")
        assert "sha256" in str(e.value) or "hash" in str(e.value).lower()


MYNUMBER_EN = "Article 2\nThe term 'Individual Number' as used in this Act means...\n"


@pytest.fixture
def translated_corpus(tmp_path):
    """A Japanese Act with its official-but-not-authentic English rendering beside it."""
    root = tmp_path / "corpus"
    store = CorpusStore(root)
    original = store.write("425AC0000000027", GDPR)
    english = store.write("425AC0000000027-en", MYNUMBER_EN)
    Manifest(
        [
            item(
                item_id="425AC0000000027",
                citation="Act No. 27 of 2013",
                title="My Number Act",
                lang="jpn",
                sha256=original.sha256,
                bytes=original.bytes,
            ),
            item(
                item_id="425AC0000000027-en",
                citation="Act No. 27 of 2013 (English)",
                title="My Number Act, e-Gov translation",
                authority_tier="commentary",
                translation_status="official-non-authoritative",
                translation_of="425AC0000000027",
                sha256=english.sha256,
                bytes=english.bytes,
            ),
        ]
    ).write(root / "MANIFEST.tsv")
    return Corpus(root)


class TestTranslationBanner:
    def test_a_translation_is_bannered_above_its_text(self, translated_corpus):
        out = translated_corpus.quote("425AC0000000027-en")
        assert out.index("TRANSLATION") < out.index("Individual Number")

    def test_the_banner_names_the_original_item(self, translated_corpus):
        assert "425AC0000000027" in translated_corpus.quote("425AC0000000027-en")

    def test_the_validity_banner_still_comes_first(self, translated_corpus):
        out = translated_corpus.quote("425AC0000000027-en")
        assert out.startswith("[in force]")
        assert out.index("[in force]") < out.index("TRANSLATION")

    def test_an_authoritative_item_gets_no_translation_banner(self, translated_corpus):
        assert "TRANSLATION" not in translated_corpus.quote("425AC0000000027")

    def test_machine_output_is_excluded_from_an_in_force_sweep(self, tmp_path):
        # in-force *and* unquotable: the filter is about what may be presented as current law,
        # and a machine rendering may never be.
        root = tmp_path / "corpus"
        store = CorpusStore(root)
        original = store.write("uu27-2022", GDPR)
        machine = store.write("uu27-2022-en", MYNUMBER_EN)
        Manifest(
            [
                item(item_id="uu27-2022", lang="ind", sha256=original.sha256, bytes=original.bytes),
                item(
                    item_id="uu27-2022-en",
                    authority_tier="commentary",
                    translation_status="machine",
                    translation_of="uu27-2022",
                    sha256=machine.sha256,
                    bytes=machine.bytes,
                ),
            ]
        ).write(root / "MANIFEST.tsv")
        corpus = Corpus(root)
        assert [h.item.item_id for h in corpus.grep("Individual Number")] == ["uu27-2022-en"]
        assert corpus.grep("Individual Number", in_force_only=True) == []

    def test_the_grep_line_flags_an_unquotable_translation(self, tmp_path, capsys):
        root = tmp_path / "corpus"
        store = CorpusStore(root)
        machine = store.write("uu27-2022-en", MYNUMBER_EN)
        Manifest(
            [
                item(
                    item_id="uu27-2022-en",
                    authority_tier="commentary",
                    translation_status="machine",
                    translation_of="uu27-2022-en-src",
                    sha256=machine.sha256,
                    bytes=machine.bytes,
                ),
                item(item_id="uu27-2022-en-src", sha256="0" * 64),
            ]
        ).write(root / "MANIFEST.tsv")
        assert main(["--corpus", str(root), "--grep", "Individual Number"]) == 0
        assert "MACHINE TRANSLATION" in capsys.readouterr().out


class TestResolveByCitation:
    def test_finds_an_item_by_its_citation_string(self, corpus):
        assert corpus.resolve("Regulation (EU) 2016/679").item_id == "32016R0679"

    def test_citation_lookup_is_case_insensitive(self, corpus):
        assert corpus.resolve("regulation (eu) 2016/679").item_id == "32016R0679"

    def test_item_id_wins_over_citation(self, corpus):
        assert corpus.resolve("32016R0679").item_id == "32016R0679"


class TestGrep:
    def test_finds_matching_items(self, corpus):
        hits = corpus.grep("lawfully")
        assert [h.item.item_id for h in hits] == ["32016R0679"]

    def test_reports_the_matching_line(self, corpus):
        assert "lawfully" in corpus.grep("lawfully")[0].line

    def test_is_a_regex(self, corpus):
        assert corpus.grep(r"law(fully|ful)")

    def test_case_insensitive_by_default(self, corpus):
        assert corpus.grep("LAWFULLY")

    def test_returns_nothing_for_no_match(self, corpus):
        assert corpus.grep("zzzz-not-present") == []

    def test_hits_carry_the_validity_so_a_sweep_cannot_silently_count_dead_law(self, corpus):
        hits = corpus.grep("Aadhaar")
        assert hits[0].item.validity.value == "struck-down"

    def test_an_invalid_regex_is_a_permanent_error(self, corpus):
        with pytest.raises(CorpusError) as e:
            corpus.grep("(unclosed")
        assert e.value.transient is False

    def test_grep_checks_the_digest_it_reports_under(self, tmp_path):
        """@ovqrxx4g — `text` failed closed on a wrong file and `grep` did not check at all.

        The asymmetry is the defect: `lawcite --grep 'domestic relations actions'` reported hits
        attributed to `URCP-26` from `URCP-26.1`'s text, while `text('URCP-26')` refused the same
        corpus a moment later. A search that reports an unchecked line is attributing a quotation
        to an instrument that may not carry it.
        """
        root = tmp_path / "corpus"
        store = CorpusStore(root)
        stored = store.write("32016R0679", GDPR)
        Manifest([item(sha256=stored.sha256, bytes=stored.bytes)]).write(root / "MANIFEST.tsv")
        corpus = Corpus(root)
        assert corpus.grep("lawfully")

        store.write("32016R0679", "Article 5\nSomething else entirely, lawfully.\n")
        with pytest.raises(CorpusError) as e:
            corpus.grep("lawfully")
        assert "32016R0679" in str(e.value)
        assert e.value.transient is False


class TestCli:
    def test_quote_prints_to_stdout(self, corpus, capsys, monkeypatch):
        monkeypatch.chdir(corpus.root.parent)
        assert main(["--corpus", str(corpus.root), "32016R0679"]) == 0
        assert "lawfully" in capsys.readouterr().out

    def test_grep_prints_hits(self, corpus, capsys):
        assert main(["--corpus", str(corpus.root), "--grep", "lawfully"]) == 0
        assert "32016R0679" in capsys.readouterr().out

    def test_missing_item_exits_nonzero_with_a_message(self, corpus, capsys):
        assert main(["--corpus", str(corpus.root), "absent"]) == 1
        assert "absent" in capsys.readouterr().err

    def test_grep_with_no_hits_exits_nonzero(self, corpus, capsys):
        # So a shell pipeline can tell "searched and found nothing" from "searched and found".
        assert main(["--corpus", str(corpus.root), "--grep", "zzzz"]) == 1


class TestCorpusIntegrity:
    def test_a_missing_manifest_is_reported_as_a_corpus_error(self, tmp_path):
        with pytest.raises(CorpusError) as e:
            Corpus(tmp_path / "empty")
        assert "MANIFEST.tsv" in str(e.value)

    def test_a_manifest_row_without_its_corpus_file_fails_on_quote(self, tmp_path):
        root = tmp_path / "corpus"
        root.mkdir()
        Manifest([item(item_id="ghost")]).write(root / "MANIFEST.tsv")
        with pytest.raises(CorpusError) as e:
            Corpus(root).quote("ghost")
        assert "ghost" in str(e.value)

    def test_grep_skips_a_manifest_row_with_no_stored_file(self, tmp_path):
        # A half-finished fetch must not crash a sweep; it must just not contribute hits.
        root = tmp_path / "corpus"
        store = CorpusStore(root)
        written = store.write("real", GDPR)
        Manifest(
            [item(item_id="real", sha256=written.sha256, bytes=written.bytes),
             item(item_id="ghost")]
        ).write(root / "MANIFEST.tsv")
        assert [h.item.item_id for h in Corpus(root).grep("lawfully")] == ["real"]


class TestInForceOnly:
    def test_excludes_struck_down_text(self, corpus):
        assert corpus.grep("Aadhaar", in_force_only=True) == []

    def test_still_includes_in_force_text(self, corpus):
        assert corpus.grep("lawfully", in_force_only=True)

    def test_cli_passes_the_flag_through(self, corpus, capsys):
        assert main(["--corpus", str(corpus.root), "--grep", "Aadhaar", "--in-force-only"]) == 1


class TestCliArguments:
    def test_neither_ref_nor_grep_is_a_usage_error(self, corpus, capsys):
        with pytest.raises(SystemExit) as e:
            main(["--corpus", str(corpus.root)])
        assert e.value.code == 2
        assert "grep" in capsys.readouterr().err


class TestTheQualifierTravelsIntoGrepOutput:
    """@fyh6u2nf — the qualifier was printed only for an item that is not quotable as current law,
    so `indonesia-id`'s five re-OCR'd items, all of them in force, greped silently.
    """

    def _corpus_with_a_qualifier(self, tmp_path, qualifier):
        root = tmp_path / "corpus"
        store = CorpusStore(root)
        written = store.write("uu27-2022", "Pasal 1 Setiap orang berhak atas pelindungan.\n")
        Manifest(
            [
                item(
                    item_id="uu27-2022",
                    lang="ind",
                    quotation_qualifier=qualifier,
                    sha256=written.sha256,
                    bytes=written.bytes,
                )
            ]
        ).write(root / "MANIFEST.tsv")
        return root

    def test_an_in_force_item_carries_its_qualifier_on_every_hit(self, tmp_path, capsys):
        root = self._corpus_with_a_qualifier(tmp_path, "teks hasil OCR ulang oleh Bakobo")
        assert main(["--corpus", str(root), "--grep", "pelindungan"]) == 0
        assert "teks hasil OCR ulang oleh Bakobo" in capsys.readouterr().out

    def test_an_in_force_item_with_nothing_to_qualify_stays_quiet(self, tmp_path, capsys):
        # Noise is what stops banners being read, so an in-force authentic item prints no mark.
        root = self._corpus_with_a_qualifier(tmp_path, "")
        assert main(["--corpus", str(root), "--grep", "pelindungan"]) == 0
        assert "[in force]" not in capsys.readouterr().out
