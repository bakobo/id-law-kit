"""The gzip corpus store.

`utah-id-law` stores corpus text gzipped (86 MB -> 15 MB) and keeps it searchable with `rg -z`.
That was the right call and is kept. What is added here is that writing and hashing happen in one
place, so the manifest's `sha256` cannot drift from the bytes on disk.
"""

import gzip
import hashlib

import pytest

from lawcorpus.store import CorpusStore, StoreError


@pytest.fixture
def store(tmp_path):
    return CorpusStore(tmp_path / "corpus")


TEXT = "Article 5\nPersonal data shall be processed lawfully, fairly and transparently.\n"


class TestWrite:
    def test_writes_a_gzipped_file(self, store):
        store.write("32016R0679", TEXT)
        path = store.path_for("32016R0679")
        assert path.name == "32016R0679.txt.gz"
        assert gzip.decompress(path.read_bytes()).decode() == TEXT

    def test_creates_the_corpus_directory(self, tmp_path):
        CorpusStore(tmp_path / "a" / "b").write("x", TEXT)
        assert (tmp_path / "a" / "b" / "x.txt.gz").exists()

    def test_returns_the_hash_and_size_of_the_uncompressed_text(self, store):
        result = store.write("32016R0679", TEXT)
        assert result.sha256 == hashlib.sha256(TEXT.encode()).hexdigest()
        assert result.bytes == len(TEXT.encode())

    def test_honours_a_custom_suffix(self, store):
        store.write("32016R0679", "<akn/>", suffix=".xml")
        assert store.path_for("32016R0679", suffix=".xml").name == "32016R0679.xml.gz"

    def test_gzip_is_deterministic_so_refetches_diff_cleanly(self, store):
        # mtime in the gzip header would make every refetch a binary diff even when the text
        # is byte-identical. That would destroy the "diff the manifest to see what changed"
        # property the whole provenance story rests on.
        store.write("a", TEXT)
        first = store.path_for("a").read_bytes()
        store.write("a", TEXT)
        assert store.path_for("a").read_bytes() == first

    def test_rejects_an_id_with_a_path_separator(self, store):
        with pytest.raises(StoreError) as e:
            store.write("../etc/passwd", TEXT)
        assert "item_id" in str(e.value)

    def test_rejects_an_empty_id(self, store):
        with pytest.raises(StoreError):
            store.write("   ", TEXT)

    def test_rejects_empty_text(self, store):
        # A zero-byte corpus entry is always a failed fetch that looked like a success.
        with pytest.raises(StoreError) as e:
            store.write("a", "")
        assert "empty" in str(e.value).lower()


class TestRead:
    def test_round_trips(self, store):
        store.write("a", TEXT)
        assert store.read("a") == TEXT

    def test_missing_item_names_the_path_and_is_permanent(self, store):
        with pytest.raises(StoreError) as e:
            store.read("absent")
        assert "absent" in str(e.value)
        assert e.value.transient is False

    def test_exists(self, store):
        assert store.exists("a") is False
        store.write("a", TEXT)
        assert store.exists("a") is True


class TestVerify:
    def test_passes_when_the_text_matches_the_recorded_hash(self, store):
        written = store.write("a", TEXT)
        assert store.verify("a", written.sha256) is True

    def test_fails_when_the_text_has_changed_underneath(self, store):
        store.write("a", TEXT)
        assert store.verify("a", "b" * 64) is False

    def test_verify_of_a_missing_item_raises_rather_than_returning_false(self, store):
        # A missing file and a corrupted file are different problems and must not be conflated.
        with pytest.raises(StoreError):
            store.verify("absent", "b" * 64)


class TestItemIds:
    def test_lists_what_is_stored(self, store):
        store.write("b", TEXT)
        store.write("a", TEXT)
        assert store.item_ids() == ["a", "b"]

    def test_lists_nothing_when_the_directory_does_not_exist(self, tmp_path):
        assert CorpusStore(tmp_path / "never-created").item_ids() == []


class TestSuffixResolution:
    """A corpus may hold more than one suffix.

    eidas-eudi stores EUR-Lex instruments as .txt and ARF documents as .md in sibling corpora.
    Anything that resolves an item_id must find it without being told the suffix — otherwise a
    search silently returns zero hits, which reads as a finding rather than as a bug.
    """

    def test_finds_a_file_whatever_its_suffix(self, store):
        store.write("a", TEXT, suffix=".md")
        assert store.resolve("a").name == "a.md.gz"

    def test_read_without_a_suffix_finds_the_md_file(self, store):
        store.write("a", TEXT, suffix=".md")
        assert store.read("a") == TEXT

    def test_exists_without_a_suffix_finds_the_md_file(self, store):
        store.write("a", TEXT, suffix=".md")
        assert store.exists("a") is True

    def test_item_ids_lists_every_suffix(self, store):
        store.write("a", TEXT, suffix=".md")
        store.write("b", TEXT)
        assert store.item_ids() == ["a", "b"]

    def test_an_explicit_suffix_still_wins(self, store):
        store.write("a", TEXT, suffix=".md")
        store.write("a", "different\n", suffix=".txt")
        assert store.read("a", suffix=".txt") == "different\n"

    def test_resolve_of_a_missing_item_raises(self, store):
        with pytest.raises(StoreError):
            store.resolve("absent")

    def test_an_explicit_suffix_that_is_absent_names_the_exact_path(self, store):
        store.write("a", TEXT, suffix=".md")
        with pytest.raises(StoreError) as e:
            store.read("a", suffix=".txt")
        assert "a.txt.gz" in str(e.value)
