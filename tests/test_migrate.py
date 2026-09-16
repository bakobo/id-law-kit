"""The one-shot migration a corpus repo runs when a required field is added to the schema.

`translation_status` shipped required and with no migration (this.i @elsvh64d), so seven manifests
across four repos stopped reading. The fix is deliberately *not* a reader that infers the value —
that is the default @elsvh64d rejected, wearing a schema version. It is a script whose
`--translation-status` flag has no default, so the value is typed by whoever knows the corpus and
lands as a committed act. See @oa2bvav5.
"""

import pytest

from lawcorpus.manifest import COLUMNS, LEGACY_COLUMNS, Manifest, ManifestError, StaleSchemaError
from lawcorpus.migrate import MigrationError, main, migrate
from lawcorpus.validity import TranslationStatusError

LEGACY_ROW = [
    "32016R0679",
    "Regulation (EU) 2016/679",
    "General Data Protection Regulation",
    "legislative",
    "in-force",
    "",
    "02016R0679-20160504",
    "eng",
    "http://publications.europa.eu/resource/celex/32016R0679",
    "2026-07-31",
    "application/xml",
    "1833131",
    "a" * 64,
]
SECOND_LEGACY_ROW = [
    "openid4vp-1_0",
    "OpenID for Verifiable Presentations 1.0",
    "OpenID4VP",
    "standard",
    "in-force",
    "",
    "1.0",
    "eng",
    "https://openid.net/specs/openid-4-verifiable-presentations-1_0.html",
    "2026-08-02",
    "text/html",
    "412000",
    "b" * 64,
]


def write_legacy(path, rows=(LEGACY_ROW,)):
    lines = ["\t".join(LEGACY_COLUMNS)] + ["\t".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestTheLegacySchemaIsRecognised:
    """A superseded header is named once, not complained about on every row."""

    def test_the_legacy_columns_are_the_current_ones_less_the_two_that_were_added(self):
        assert set(COLUMNS) - set(LEGACY_COLUMNS) == {"translation_status", "translation_of"}
        assert [c for c in COLUMNS if c in LEGACY_COLUMNS] == list(LEGACY_COLUMNS)

    def test_reading_one_raises_once_rather_than_per_row(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv", [LEGACY_ROW, SECOND_LEGACY_ROW])
        with pytest.raises(StaleSchemaError) as e:
            Manifest.read(path)
        assert "line 2" not in str(e.value)
        assert "line 3" not in str(e.value)

    def test_the_refusal_names_the_command_that_fixes_it(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(StaleSchemaError) as e:
            Manifest.read(path)
        assert "lawcorpus.migrate" in str(e.value)
        assert "--translation-status" in str(e.value)
        assert str(path) in str(e.value)

    def test_it_is_still_a_manifest_error_so_existing_callers_keep_catching_it(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(ManifestError):
            Manifest.read(path)

    def test_a_header_that_is_neither_schema_still_fails_per_row(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        path.write_text("item_id\tcitation\n32016R0679\tReg\n", encoding="utf-8")
        with pytest.raises(ManifestError) as e:
            Manifest.read(path)
        assert not isinstance(e.value, StaleSchemaError)
        assert "line 2" in str(e.value)


class TestTheMigrationRefusesToGuess:
    def test_it_requires_a_translation_status(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(TranslationStatusError):
            migrate(path, translation_status="")

    def test_it_refuses_a_token_outside_the_vocabulary(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(TranslationStatusError):
            migrate(path, translation_status="probably-fine")

    @pytest.mark.parametrize("token", ["official-non-authoritative", "unofficial", "machine"])
    def test_it_refuses_to_assign_a_status_that_owes_a_translation_of(self, tmp_path, token):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(MigrationError) as e:
            migrate(path, translation_status=token)
        assert "translation_of" in str(e.value)

    def test_it_refuses_a_manifest_already_on_the_current_schema(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        migrate(path, translation_status="authoritative")
        with pytest.raises(MigrationError) as e:
            migrate(path, translation_status="authoritative")
        assert "already" in str(e.value)

    def test_it_refuses_a_header_it_does_not_recognise(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        path.write_text("rule\tname\tagency\n", encoding="utf-8")
        with pytest.raises(MigrationError) as e:
            migrate(path, translation_status="authoritative")
        assert "rule" in str(e.value)

    def test_it_refuses_a_manifest_that_is_not_there(self, tmp_path):
        with pytest.raises(MigrationError) as e:
            migrate(tmp_path / "nope.tsv", translation_status="authoritative")
        assert "nope.tsv" in str(e.value)

    def test_it_refuses_an_empty_file_rather_than_reporting_nothing_to_do(self, tmp_path):
        path = tmp_path / "MANIFEST.tsv"
        path.write_text("", encoding="utf-8")
        with pytest.raises(MigrationError):
            migrate(path, translation_status="authoritative")


class TestTheMigrationItself:
    def test_it_adds_the_two_columns_with_the_stated_value(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        report = migrate(path, translation_status="authoritative")
        assert report.rows == 1
        assert path.read_text(encoding="utf-8").splitlines()[0] == "\t".join(COLUMNS)
        item = Manifest.read(path)["32016R0679"]
        assert item.translation_status.value == "authoritative"
        assert item.translation_of == ""

    def test_it_leaves_every_other_field_alone(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        migrate(path, translation_status="authoritative")
        item = Manifest.read(path)["32016R0679"]
        assert item.sha256 == "a" * 64
        assert item.bytes == 1833131
        assert item.retrieved == "2026-07-31"
        assert item.source_url.endswith("32016R0679")

    def test_a_dry_run_reports_without_writing(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        before = path.read_text(encoding="utf-8")
        report = migrate(path, translation_status="authoritative", dry_run=True)
        assert report.rows == 1
        assert path.read_text(encoding="utf-8") == before

    def test_a_row_that_fails_validation_stops_the_whole_file(self, tmp_path):
        bad = list(LEGACY_ROW)
        bad[12] = "not-a-digest"
        path = write_legacy(tmp_path / "MANIFEST.tsv", [LEGACY_ROW, bad])
        with pytest.raises(ManifestError):
            migrate(path, translation_status="authoritative")
        assert path.read_text(encoding="utf-8").splitlines()[0] == "\t".join(LEGACY_COLUMNS)


class TestRetier:
    """@3zljqayt's correction rides this migration rather than becoming a second hand-edit."""

    def test_it_rewrites_the_tier_it_is_told_to(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv", [SECOND_LEGACY_ROW])
        report = migrate(
            path, translation_status="authoritative", retier={"standard": "commentary"}
        )
        assert report.retiered == {"standard": 1}
        assert Manifest.read(path)["openid4vp-1_0"].authority_tier.value == "commentary"

    def test_without_it_an_unknown_tier_is_refused_as_before(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv", [SECOND_LEGACY_ROW])
        with pytest.raises(ManifestError) as e:
            migrate(path, translation_status="authoritative")
        assert "standard" in str(e.value)

    def test_a_retier_that_matches_nothing_is_reported_across_the_whole_run(self, tmp_path, capsys):
        """One --retier covers a set of manifests, so "matched nothing" is a run-level fact."""
        one = write_legacy(tmp_path / "one.tsv")
        two = write_legacy(tmp_path / "two.tsv", [SECOND_LEGACY_ROW])
        code = main(
            [
                str(one),
                str(two),
                "--translation-status",
                "authoritative",
                "--retier",
                "standard=commentary",
                "--retier",
                "standrad=commentary",
            ]
        )
        out = capsys.readouterr().out
        assert code == 1
        assert "standrad" in out
        assert "standard" not in out.split("FAIL")[1]
        assert Manifest.read(two)["openid4vp-1_0"].authority_tier.value == "commentary"

    def test_the_target_tier_must_be_in_the_vocabulary(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv", [SECOND_LEGACY_ROW])
        with pytest.raises(ManifestError):
            migrate(path, translation_status="authoritative", retier={"standard": "quite-good"})


class TestTheCommandLine:
    def test_it_migrates_every_path_it_is_given(self, tmp_path, capsys):
        one = write_legacy(tmp_path / "one.tsv")
        two = write_legacy(tmp_path / "two.tsv", [SECOND_LEGACY_ROW])
        code = main(
            [
                str(one),
                str(two),
                "--translation-status",
                "authoritative",
                "--retier",
                "standard=commentary",
            ]
        )
        assert code == 0
        assert capsys.readouterr().out.count("1 row(s)") == 2
        assert Manifest.read(one)
        assert Manifest.read(two)["openid4vp-1_0"].authority_tier.value == "commentary"

    def test_one_bad_file_does_not_stop_the_others_and_the_exit_code_says_so(
        self, tmp_path, capsys
    ):
        good = write_legacy(tmp_path / "good.tsv")
        missing = tmp_path / "gone.tsv"
        code = main([str(missing), str(good), "--translation-status", "authoritative"])
        assert code == 1
        out = capsys.readouterr().out
        assert "gone.tsv" in out
        assert Manifest.read(good)

    def test_a_dry_run_changes_nothing(self, tmp_path, capsys):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        before = path.read_text(encoding="utf-8")
        assert main([str(path), "--translation-status", "authoritative", "--dry-run"]) == 0
        assert path.read_text(encoding="utf-8") == before
        assert "dry run" in capsys.readouterr().out

    def test_a_malformed_retier_argument_is_refused_by_the_parser(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(SystemExit):
            main([str(path), "--translation-status", "authoritative", "--retier", "commentary"])

    def test_the_status_is_required_because_there_is_no_default(self, tmp_path):
        path = write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(SystemExit):
            main([str(path)])


class TestTheStaleSchemaReachesTheCaller:
    """`lawcite` must be able to offer the migration, not merely fail to read the corpus."""

    def test_opening_a_corpus_keeps_the_stale_schema_identity(self, tmp_path):
        from lawcorpus.cite import Corpus

        write_legacy(tmp_path / "MANIFEST.tsv")
        with pytest.raises(StaleSchemaError) as e:
            Corpus(tmp_path)
        assert e.value.code == "e.state.stale.manifest-schema.f"

    def test_any_other_manifest_defect_is_still_a_corpus_error(self, tmp_path):
        from lawcorpus.cite import Corpus, CorpusError

        (tmp_path / "MANIFEST.tsv").write_text("item_id\tcitation\nx\ty\n", encoding="utf-8")
        with pytest.raises(CorpusError):
            Corpus(tmp_path)
