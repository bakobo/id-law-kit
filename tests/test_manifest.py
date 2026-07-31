"""One manifest schema for every corpus.

`utah-id-law` grew a bespoke manifest per corpus (`MANIFEST-utah-code.tsv` has six columns,
`MANIFEST-admin-rules.tsv` has ten, and they share only `retrieved`). With five repos that becomes
five dialects and no shared tooling. See this.i @oxu7ik.
"""

import pytest

from lawcorpus.errors import LawcorpusError
from lawcorpus.manifest import (
    COLUMNS,
    Manifest,
    ManifestError,
    ManifestItem,
)
from lawcorpus.validity import AuthorityTier, Validity


def an_item(**over):
    base = dict(
        item_id="32016R0679",
        citation="Regulation (EU) 2016/679",
        title="General Data Protection Regulation",
        authority_tier="legislative",
        validity="in-force",
        validity_note="",
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
