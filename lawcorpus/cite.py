"""The citation primitive: quote a corpus item, or search across one.

Every claim about the law in these repos must be produced by this tool rather than from a model's
memory. `utah-id-law` established why: a model asked "what does the law require for X" will produce
a plausible section number with a plausible quotation, and both may be inventions. A corpus makes
that mechanically checkable.

This adds one thing to the Utah original. **A quote never prints without its validity banner.**
Quote-or-drop proves a passage was published; it does not prove the passage is law. Section 57 of
the Aadhaar Act is still in the PDF UIDAI publishes, and it has not been law since 2018.

Usage:
    lawcite --corpus corpus/ 32016R0679          # quote one item
    lawcite --corpus corpus/ 'Regulation (EU) 2016/679'
    lawcite --corpus corpus/ --grep 'lawful basis'
    lawcite --corpus corpus/ --grep 'identity' --in-force-only
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import LawcorpusError
from .manifest import Manifest, ManifestError
from .store import CorpusStore, StoreError
from .validity import Validity


class CorpusError(LawcorpusError):
    """A citation that cannot be resolved, or a corpus that does not hold together."""

    code = "BK_CITE_UNRESOLVED"


@dataclass(frozen=True)
class Hit:
    """One matching line, carried together with the item's authority and validity."""

    item: object
    line_no: int
    line: str


class Corpus:
    """A manifest plus its store, resolved together."""

    def __init__(self, root, manifest_name: str = "MANIFEST.tsv"):
        self.root = Path(root)
        try:
            self.manifest = Manifest.read(self.root / manifest_name)
        except ManifestError as e:
            raise CorpusError(e.message) from e
        self.store = CorpusStore(self.root)

    def resolve(self, ref: str):
        """Find an item by `item_id`, else by `citation` (case-insensitively)."""
        ref = ("" if ref is None else str(ref)).strip()
        for item in self.manifest:
            if item.item_id == ref:
                return item
        lowered = ref.lower()
        for item in self.manifest:
            if item.citation.lower() == lowered:
                return item
        known = ", ".join(sorted(i.item_id for i in self.manifest)[:8]) or "(the corpus is empty)"
        raise CorpusError(
            f"Nothing in this corpus matches '{ref[:60]}'. Give an item_id or an exact citation. "
            f"Known item_ids include: {known}."
        )

    def text(self, ref: str) -> str:
        """The stored text, after checking it still hashes to what the manifest recorded."""
        item = self.resolve(ref) if isinstance(ref, str) else ref
        try:
            body = self.store.read(item.item_id)
        except StoreError as e:
            raise CorpusError(e.message) from e

        if hashlib.sha256(body.encode("utf-8")).hexdigest() != item.sha256:
            raise CorpusError(
                f"The stored text for '{item.item_id}' no longer matches the sha256 in the "
                f"manifest. Either the file was edited by hand or the manifest is stale — refetch "
                f"rather than quoting it, because provenance is the only thing making this "
                f"corpus worth more than a web search."
            )
        return body

    def quote(self, ref: str) -> str:
        """The text, with the banner and provenance header that must accompany any citation."""
        item = self.resolve(ref) if isinstance(ref, str) else ref
        body = self.text(item)
        header = [
            item.banner(),
            f"{item.citation} — {item.title}",
            f"  authority: {item.authority_tier.value}"
            + (f"   version: {item.version_id}" if item.version_id else ""),
            f"  retrieved {item.retrieved} from {item.source_url}",
            "",
        ]
        return "\n".join(header) + body

    def grep(self, pattern: str, in_force_only: bool = False) -> list:
        """Search every item's text; hits carry the item, so validity travels with the count.

        `utah-id-law` learned that counts are pointers to read, never findings. A count that mixes
        in-force and struck-down text is worse than no count at all.
        """
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            raise CorpusError(
                f"'{str(pattern)[:40]}' is not a valid regular expression: {e}."
            ) from e
        hits = []
        for item in self.manifest.by_authority():
            if in_force_only and item.validity is not Validity.IN_FORCE:
                continue
            if not self.store.exists(item.item_id):
                continue
            for n, line in enumerate(self.store.read(item.item_id).splitlines(), start=1):
                if rx.search(line):
                    hits.append(Hit(item=item, line_no=n, line=line.strip()))
        return hits


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="lawcite", description=__doc__.split("\n")[0])
    p.add_argument("ref", nargs="?", help="item_id or citation to quote")
    p.add_argument("--corpus", default="corpus", help="corpus directory (default: corpus)")
    p.add_argument("--manifest", default="MANIFEST.tsv")
    p.add_argument("--grep", metavar="REGEX", help="search all items instead of quoting one")
    p.add_argument(
        "--in-force-only",
        action="store_true",
        help="skip amended, struck-down, read-down, and repealed text when searching",
    )
    args = p.parse_args(argv)

    if not args.ref and not args.grep:
        p.error("give an item_id/citation to quote, or --grep to search")

    try:
        corpus = Corpus(args.corpus, args.manifest)
        if args.grep:
            hits = corpus.grep(args.grep, in_force_only=args.in_force_only)
            for hit in hits:
                flag = "" if hit.item.validity is Validity.IN_FORCE else f" {hit.item.banner()}"
                print(f"{hit.item.item_id}:{hit.line_no}:{flag} {hit.line}")
            print(f"\n{len(hits)} line(s) in {len({h.item.item_id for h in hits})} item(s).")
            print(
                "Counts are pointers to read, not findings. Open the hits before concluding "
                "anything from this number."
            )
            return 0 if hits else 1
        print(corpus.quote(args.ref))
        return 0
    except LawcorpusError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
