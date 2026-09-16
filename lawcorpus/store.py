"""The gzip corpus store.

`utah-id-law` stores corpus text gzipped and searches it with `rg -z`, which reads gzip directly.
That stays. The change is that writing, sizing, and hashing happen in one call, so a manifest's
`sha256` cannot drift from the bytes actually on disk.

Gzip is written with `mtime=0`. Without that, two byte-identical fetches produce different
compressed bytes, every refetch shows up as a binary diff, and the "diff the manifest to see
exactly what changed" property that the provenance story rests on quietly stops working.
"""

from __future__ import annotations

import gzip
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import LawcorpusError

# What may follow an item_id in a stored filename: one extension, then `.gz`. Anything with a
# further dot in it belongs to a *longer item_id* — `URCP-26.1` is its own rule. See @ovqrxx4g.
_ONE_EXTENSION = re.compile(r"\.[^.]+\.gz")


class StoreError(LawcorpusError):
    """A corpus file that is missing, unreadable, or refused on write."""

    code = "BK_CORPUS_STORE"


@dataclass(frozen=True)
class StoredText:
    """What was written: the digest and size of the *uncompressed* text."""

    item_id: str
    path: Path
    sha256: str
    bytes: int


def _safe_id(item_id: str) -> str:
    text = "" if item_id is None else str(item_id).strip()
    if not text:
        raise StoreError("The item_id is empty. Every corpus file needs an id to be stored under.")
    if "/" in text or "\\" in text or text.startswith("."):
        raise StoreError(
            f"The item_id '{text[:40]}' contains a path separator or starts with a dot. An item_id "
            f"becomes a filename, so it must name one file inside the corpus directory."
        )
    return text


class CorpusStore:
    """Gzipped text files under one directory, keyed by `item_id`."""

    def __init__(self, root):
        self.root = Path(root)

    def path_for(self, item_id: str, suffix: str = ".txt") -> Path:
        return self.root / f"{_safe_id(item_id)}{suffix}.gz"

    def write(self, item_id: str, text: str, suffix: str = ".txt", expect=None) -> StoredText:
        """Write `text` for `item_id`, refusing an empty body and an incomplete one.

        `expect` is a `completeness.Expectation` — what an independent source says this instrument
        contains. Supplied, it is checked *before* anything reaches disk, so a refusal leaves no
        half-instrument behind. Omitted, only the emptiness guard runs: most corpora have no
        declared structure to check, and a check nobody can satisfy would be turned off.
        """
        item_id = _safe_id(item_id)
        if not text:
            raise StoreError(
                f"Refusing to store an empty body for '{item_id}'. A zero-byte corpus entry is "
                f"always a failed retrieval that looked like a success — check the fetch first."
            )
        if expect is not None:
            expect.verify(text)
        raw = text.encode("utf-8")
        path = self.path_for(item_id, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.GzipFile(filename="", mode="wb", fileobj=path.open("wb"), mtime=0) as fh:
            fh.write(raw)
        return StoredText(
            item_id=item_id,
            path=path,
            sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw),
        )

    def resolve(self, item_id: str, suffix: str = None) -> Path:
        """The stored file for `item_id`, whatever suffix it was written under.

        A corpus can mix suffixes — eidas-eudi stores EUR-Lex text as `.txt` and ARF documents as
        `.md`. Callers that assume one suffix get an empty result rather than an error, and an
        empty result from a search reads as a finding.

        **What follows the item_id must be exactly one dotted extension**, so a dot cannot be
        swallowed. This used to glob `{item_id}.*.gz`, where `*` matches a dot and `1` sorts before
        `t`, so `URCP-26` resolved to `URCP-26.1.txt.gz` — a *different rule*, not a suffix.
        `utah-id-law`'s court-rules layer had 13 of 662 items resolving to a sibling. The dotted
        insertion is universal in legal numbering (第六条の二, ๓๒/๒, `Pasal 13A`), and @kolycpun
        already refused to collapse one onto its base a layer up. See @ovqrxx4g.

        Walking the directory rather than globbing also means an item_id carrying `*`, `?` or `[`
        is matched literally instead of being read as a pattern.
        """
        if suffix is not None:
            path = self.path_for(item_id, suffix)
            if not path.exists():
                raise StoreError(
                    f"No corpus file for '{item_id}' at {path}. Run this repo's fetcher to "
                    f"retrieve it."
                )
            return path
        stem = _safe_id(item_id)
        matches = sorted(
            path
            for path in (self.root.iterdir() if self.root.exists() else ())
            if path.name.startswith(stem) and _ONE_EXTENSION.fullmatch(path.name[len(stem):])
        )
        if not matches:
            raise StoreError(
                f"No corpus file for '{item_id}' under {self.root} (any suffix). Run this repo's "
                f"fetcher to retrieve it."
            )
        return matches[0]

    def read(self, item_id: str, suffix: str = None) -> str:
        return gzip.decompress(self.resolve(item_id, suffix).read_bytes()).decode("utf-8", "replace")

    def exists(self, item_id: str, suffix: str = None) -> bool:
        try:
            self.resolve(item_id, suffix)
            return True
        except StoreError:
            return False

    def verify(self, item_id: str, sha256: str, suffix: str = None) -> bool:
        """Does the stored text still hash to what the manifest recorded?

        Raises if the file is absent — a missing corpus file and a corrupted one are different
        problems, and returning False for both would hide the first.
        """
        raw = self.read(item_id, suffix).encode("utf-8")
        return hashlib.sha256(raw).hexdigest() == str(sha256).strip().lower()

    def item_ids(self, suffix: str = None) -> list:
        """Every stored item_id, across all suffixes unless one is named."""
        if not self.root.exists():
            return []
        pattern = f"*{suffix}.gz" if suffix else "*.*.gz"
        return sorted({p.name.rsplit(".", 2)[0] for p in self.root.glob(pattern)})
