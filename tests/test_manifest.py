"""One manifest schema for every corpus.

`utah-id-law` grew a bespoke manifest per corpus (`MANIFEST-utah-code.tsv` has six columns,
`MANIFEST-admin-rules.tsv` has ten, and they share only `retrieved`). With five repos that becomes
five dialects and no shared tooling. See this.i @oxu7ik.
"""

import pytest

from lawcorpus.errors import LawcorpusError
from lawcorpus.manifest import (
    COLUMNS,
    LEGACY_COLUMNS,
    Manifest,
    ManifestError,
    ManifestItem,
    StaleSchemaError,
)
from lawcorpus.validity import AuthorityTier, TranslationStatus, Validity


def an_item(**over):
    base = dict(
        item_id="32016R0679",
        citation="Regulation (EU) 2016/679",
        title="General Data Protection Regulation",
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
        bytes=1833131,
        sha256="a" * 64,
    )
    base.update(over)
    return ManifestItem(**base)


class TestManifestItem:
    def test_parses_its_vocabularies(self):
        item = an_item()
        assert item.validity is Validity.IN_FORCE
        assert item.authority_tier is AuthorityTier.LEGISLATIVE

    def test_rejects_a_missing_validity(self):
        with pytest.raises(ManifestError) as e:
            an_item(validity="")
        assert "validity" in str(e.value)

    def test_rejects_a_missing_authority_tier(self):
        with pytest.raises(ManifestError):
            an_item(authority_tier=None)

    def test_rejects_an_empty_item_id(self):
        with pytest.raises(ManifestError) as e:
            an_item(item_id="  ")
        assert "item_id" in str(e.value)

    def test_rejects_a_malformed_sha256(self):
        with pytest.raises(ManifestError) as e:
            an_item(sha256="deadbeef")
        assert "sha256" in str(e.value)
        assert "64" in str(e.value)

    def test_rejects_a_non_hex_sha256(self):
        with pytest.raises(ManifestError):
            an_item(sha256="z" * 64)

    def test_normalises_sha256_case(self):
        assert an_item(sha256="A" * 64).sha256 == "a" * 64

    def test_rejects_a_malformed_retrieved_date(self):
        with pytest.raises(ManifestError) as e:
            an_item(retrieved="31 July 2026")
        assert "retrieved" in str(e.value)

    def test_rejects_negative_bytes(self):
        with pytest.raises(ManifestError):
            an_item(bytes=-1)

    def test_rejects_non_integer_bytes(self):
        with pytest.raises(ManifestError):
            an_item(bytes="lots")

    def test_accepts_bytes_as_a_numeric_string(self):
        # TSV round-trips give strings; the item must coerce rather than reject.
        assert an_item(bytes="1833131").bytes == 1833131

    def test_requires_a_validity_note_when_not_in_force(self):
        # The whole point is knowing *what* changed it. "struck-down" with no pointer is a
        # dead end for the next reader.
        with pytest.raises(ManifestError) as e:
            an_item(validity="struck-down", validity_note="")
        assert "validity_note" in str(e.value)

    def test_allows_an_empty_validity_note_when_in_force(self):
        assert an_item(validity="in-force", validity_note="").validity_note == ""

    def test_banner_carries_the_note(self):
        item = an_item(
            validity="struck-down",
            validity_note="Puttaswamy v. Union of India (2018) 1 SCC 1",
        )
        assert "STRUCK DOWN" in item.banner()
        assert "Puttaswamy" in item.banner()

    def test_rejects_an_unknown_language_code_shape(self):
        with pytest.raises(ManifestError) as e:
            an_item(lang="english")
        assert "lang" in str(e.value)

    def test_rejects_a_missing_translation_status(self):
        # Required with no default, at the same chokepoint as validity. See this.i @elsvh64d.
        with pytest.raises(ManifestError) as e:
            an_item(translation_status="")
        assert "translation_status" in str(e.value)

    def test_rejects_an_unknown_translation_status(self):
        with pytest.raises(ManifestError) as e:
            an_item(translation_status="google-translate")
        assert "google-translate" in str(e.value)

    def test_parses_the_translation_vocabulary(self):
        assert an_item().translation_status is TranslationStatus.AUTHORITATIVE

    def test_a_translation_must_name_the_original_it_renders(self):
        with pytest.raises(ManifestError) as e:
            an_item(
                item_id="425AC0000000027-en",
                authority_tier="commentary",
                translation_status="official-non-authoritative",
                translation_of="",
            )
        assert "translation_of" in str(e.value)

    def test_a_translation_is_filed_as_commentary(self):
        # A rendering that is not authentic text cannot outrank the instrument it renders.
        with pytest.raises(ManifestError) as e:
            an_item(
                item_id="425AC0000000027-en",
                authority_tier="legislative",
                translation_status="official-non-authoritative",
                translation_of="425AC0000000027",
            )
        assert "commentary" in str(e.value)

    def test_accepts_a_well_formed_translation(self):
        item = an_item(
            item_id="425AC0000000027-en",
            authority_tier="commentary",
            translation_status="official-non-authoritative",
            translation_of="425AC0000000027",
        )
        assert item.translation_of == "425AC0000000027"
        assert item.authority_tier is AuthorityTier.COMMENTARY

    def test_an_authoritative_item_may_still_name_a_counterpart(self):
        # The EU's 24 language versions are each authentic; so are bilingual statutes.
        item = an_item(translation_status="authoritative", translation_of="32016R0679-fr")
        assert item.translation_of == "32016R0679-fr"

    def test_banners_carry_both_the_validity_and_the_translation(self):
        item = an_item(
            item_id="425AC0000000027-en",
            authority_tier="commentary",
            validity="amended",
            validity_note="Act No. 27 of 2023",
            translation_status="official-non-authoritative",
            translation_of="425AC0000000027",
        )
        assert len(item.banners()) == 2
        assert "AMENDED" in item.banners()[0]
        assert "TRANSLATION" in item.banners()[1]
        assert "425AC0000000027" in item.banners()[1]

    def test_an_authoritative_item_carries_only_the_validity_banner(self):
        assert an_item().banners() == ["[in force]"]

    def test_machine_translation_is_not_quotable_however_valid_the_original(self):
        item = an_item(
            item_id="uu27-2022-en",
            authority_tier="commentary",
            validity="in-force",
            translation_status="machine",
            translation_of="uu27-2022",
        )
        assert item.quotable_as_current_law() is False

    def test_a_struck_down_item_is_not_quotable_however_authentic(self):
        item = an_item(validity="struck-down", validity_note="Puttaswamy (2018) 1 SCC 1")
        assert item.quotable_as_current_law() is False

    def test_an_in_force_authoritative_item_is_quotable(self):
        assert an_item().quotable_as_current_law() is True

    def test_errors_are_lawcorpus_errors_with_a_code(self):
        with pytest.raises(LawcorpusError) as e:
            an_item(validity="")
        assert e.value.code
        assert e.value.transient is False


class TestRowRoundTrip:
    def test_to_row_and_back(self):
        item = an_item()
        assert ManifestItem.from_row(item.to_row()) == item

    def test_row_keys_are_exactly_the_schema(self):
        assert list(an_item().to_row().keys()) == list(COLUMNS)

    def test_from_row_rejects_an_unknown_column(self):
        row = an_item().to_row()
        row["favourite_colour"] = "blue"
        with pytest.raises(ManifestError) as e:
            ManifestItem.from_row(row)
        assert "favourite_colour" in str(e.value)

    def test_from_row_rejects_a_missing_column(self):
        row = an_item().to_row()
        del row["sha256"]
        with pytest.raises(ManifestError) as e:
            ManifestItem.from_row(row)
        assert "sha256" in str(e.value)


class TestManifestFile:
    def test_writes_and_reads_a_tsv(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        m = Manifest([an_item(), an_item(item_id="32022R0868", citation="Reg (EU) 2022/868")])
        m.write(path)
        assert Manifest.read(path) == m

    def test_written_file_has_a_header_row(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        Manifest([an_item()]).write(path)
        header = path.read_text().splitlines()[0]
        assert header.split("\t") == list(COLUMNS)

    def test_is_tab_separated_so_ripgrep_works(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        Manifest([an_item()]).write(path)
        assert "\t" in path.read_text().splitlines()[1]

    def test_rows_are_sorted_by_item_id_for_stable_diffs(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        Manifest([an_item(item_id="zzz"), an_item(item_id="aaa")]).write(path)
        ids = [line.split("\t")[0] for line in path.read_text().splitlines()[1:]]
        assert ids == ["aaa", "zzz"]

    def test_rejects_duplicate_item_ids(self, tmp_path):
        with pytest.raises(ManifestError) as e:
            Manifest([an_item(), an_item()]).write(tmp_path / "M.tsv")
        assert "32016R0679" in str(e.value)

    def test_rejects_a_translation_whose_original_is_not_in_the_corpus(self, tmp_path):
        # An unresolvable pointer is a defect that otherwise surfaces years later, in a citation.
        m = Manifest(
            [
                an_item(
                    item_id="425AC0000000027-en",
                    authority_tier="commentary",
                    translation_status="unofficial",
                    translation_of="425AC0000000027",
                )
            ]
        )
        with pytest.raises(ManifestError) as e:
            m.write(tmp_path / "M.tsv")
        assert "425AC0000000027" in str(e.value)

    def test_accepts_a_translation_alongside_its_original(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        m = Manifest(
            [
                an_item(item_id="425AC0000000027"),
                an_item(
                    item_id="425AC0000000027-en",
                    authority_tier="commentary",
                    translation_status="unofficial",
                    translation_of="425AC0000000027",
                ),
            ]
        )
        m.write(path)
        assert Manifest.read(path) == m

    def test_rejects_an_item_that_translates_itself(self, tmp_path):
        m = Manifest(
            [
                an_item(
                    item_id="loop",
                    authority_tier="commentary",
                    translation_status="unofficial",
                    translation_of="loop",
                )
            ]
        )
        with pytest.raises(ManifestError) as e:
            m.write(tmp_path / "M.tsv")
        assert "loop" in str(e.value)

    def test_read_of_a_missing_file_says_so(self, tmp_path):
        with pytest.raises(ManifestError) as e:
            Manifest.read(tmp_path / "nope.tsv")
        assert "nope.tsv" in str(e.value)

    def test_read_reports_the_line_number_of_a_bad_row(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        Manifest([an_item()]).write(path)
        lines = path.read_text().splitlines()
        lines[1] = lines[1].replace("in-force", "probably-fine")
        path.write_text("\n".join(lines) + "\n")
        with pytest.raises(ManifestError) as e:
            Manifest.read(path)
        assert "line 2" in str(e.value)

    def test_lookup_by_item_id(self):
        m = Manifest([an_item(), an_item(item_id="other")])
        assert m["other"].item_id == "other"

    def test_lookup_miss_lists_what_is_there(self):
        m = Manifest([an_item()])
        with pytest.raises(ManifestError) as e:
            m["absent"]
        assert "absent" in str(e.value)

    def test_iterates_in_authority_order(self):
        m = Manifest(
            [
                an_item(item_id="c", authority_tier="commentary"),
                an_item(item_id="a", authority_tier="legislative"),
                an_item(item_id="b", authority_tier="judicial"),
            ]
        )
        assert [i.item_id for i in m.by_authority()] == ["a", "b", "c"]

    def test_len_and_iter(self):
        m = Manifest([an_item(), an_item(item_id="x")])
        assert len(m) == 2
        assert {i.item_id for i in m} == {"32016R0679", "x"}


class TestTheQuotationQualifier:
    """@ublm5oib — japan-id writes 「（抄）」 into `citation` and singapore-id writes SSO clause (8)
    into it, because `citation` was the only field that travels with a quotation."""

    def test_it_defaults_to_nothing_and_prints_nothing(self):
        item = an_item()
        assert item.quotation_qualifier == ""
        assert item.banners() == [item.banner()]

    def test_a_qualifier_prints_above_the_quote_with_the_other_banners(self):
        item = an_item(quotation_qualifier="（抄）— e-Gov serves this instrument in part.")
        assert item.banners()[-1] == "[（抄）— e-Gov serves this instrument in part.]"
        assert len(item.banners()) == 2

    def test_singapores_disclaimer_and_japans_excerpt_mark_both_fit(self):
        sso = an_item(
            quotation_qualifier=(
                "SSO clause (8): this is an unofficial version and Interpretation Act 1965 s48 "
                "does not apply to it."
            )
        )
        assert "Interpretation Act 1965 s48" in "\n".join(sso.banners())

    def test_it_is_stripped_like_every_other_free_text_field(self):
        assert an_item(quotation_qualifier="  （抄）  ").quotation_qualifier == "（抄）"

    def test_none_reads_as_no_qualifier(self):
        assert an_item(quotation_qualifier=None).quotation_qualifier == ""

    def test_it_survives_a_write_and_a_read(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        Manifest([an_item(quotation_qualifier="（抄）")]).write(path)
        assert Manifest.read(path).items[0].quotation_qualifier == "（抄）"

    def test_the_column_is_in_the_schema(self):
        assert "quotation_qualifier" in COLUMNS


class TestAnAdditiveColumnNeedsNoMigration:
    """@ublm5oib — a required column with no default is what broke seven manifests across four
    repos (@oa2bvav5). This one is optional, so absence means 'the source did not qualify it'."""

    def test_a_manifest_written_before_the_column_still_reads(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        previous = [c for c in COLUMNS if c != "quotation_qualifier"]
        row = an_item().to_row()
        path.write_text(
            "\t".join(previous) + "\n" + "\t".join(row[c] for c in previous) + "\n",
            encoding="utf-8",
        )
        assert Manifest.read(path).items[0].quotation_qualifier == ""

    def test_and_gains_the_column_when_it_is_next_written(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        Manifest([an_item()]).write(path)
        assert path.read_text(encoding="utf-8").splitlines()[0].endswith("\tsha256")
        assert "quotation_qualifier" in path.read_text(encoding="utf-8").splitlines()[0]

    def test_a_row_missing_a_required_column_is_still_refused(self):
        row = an_item().to_row()
        del row["citation"]
        with pytest.raises(ManifestError) as e:
            ManifestItem.from_row(row)
        assert "citation" in str(e.value)

    def test_the_legacy_header_is_still_recognised_and_still_names_the_migration(self, tmp_path):
        # LEGACY_COLUMNS is frozen as a literal; derived from COLUMNS it would have grown this
        # column and stopped matching the seven files @oa2bvav5 shipped the migration for.
        assert "quotation_qualifier" not in LEGACY_COLUMNS
        assert "translation_status" not in LEGACY_COLUMNS
        path = tmp_path / "MANIFEST.tsv"
        path.write_text("\t".join(LEGACY_COLUMNS) + "\n", encoding="utf-8")
        with pytest.raises(StaleSchemaError) as e:
            Manifest.read(path)
        assert "lawcorpus.migrate" in str(e.value)
