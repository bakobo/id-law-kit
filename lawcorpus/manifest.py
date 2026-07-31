"""One manifest schema for every corpus in the programme.

`utah-id-law` grew a bespoke manifest per corpus — `MANIFEST-utah-code.tsv` carries six columns,
`MANIFEST-admin-rules.tsv` ten, and they share only `retrieved`. That is fine for one repo and
unworkable for five, because no shared citation or sweep tool can read them all.

The format stays tab-separated for the same reason `utah-id-law` chose it: it diffs cleanly in git
and `rg` reads it without a parser. What is new is that `validity` and `authority_tier` are
**required, with no default** — see `validity.py` for why.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import LawcorpusError
from .validity import (
    AuthorityTier,
    Validity,
    ValidityError,
    parse_authority_tier,
    parse_validity,
)

COLUMNS = (
    "item_id",
    "citation",
    "title",
    "authority_tier",
    "validity",
    "validity_note",
    "version_id",
    "lang",
    "source_url",
    "retrieved",
    "media_type",
    "bytes",
    "sha256",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LANG = re.compile(r"^[a-z]{3}$")


class ManifestError(LawcorpusError):
    """A manifest row, file, or lookup that does not hold up."""

    code = "BK_MANIFEST_INVALID"


def _required_text(value, name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ManifestError(
            f"The {name} field is empty. Every manifest row must carry a {name}."
        )
    return text


@dataclass(frozen=True)
class ManifestItem:
    """One retrieved instrument, provision, or document."""

    item_id: str
    citation: str
    title: str
    authority_tier: AuthorityTier
    validity: Validity
    version_id: str
    lang: str
    source_url: str
    retrieved: str
    media_type: str
    bytes: int
    sha256: str
    validity_note: str = ""

    def __post_init__(self):
        object.__setattr__(self, "item_id", _required_text(self.item_id, "item_id"))
        object.__setattr__(self, "citation", _required_text(self.citation, "citation"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        object.__setattr__(self, "source_url", _required_text(self.source_url, "source_url"))
        object.__setattr__(self, "version_id", "" if self.version_id is None else str(self.version_id).strip())
        object.__setattr__(self, "media_type", "" if self.media_type is None else str(self.media_type).strip())
        object.__setattr__(
            self, "validity_note", "" if self.validity_note is None else str(self.validity_note).strip()
        )

        try:
            object.__setattr__(self, "validity", _coerce(self.validity, parse_validity))
            object.__setattr__(
                self, "authority_tier", _coerce(self.authority_tier, parse_authority_tier)
            )
        except ValidityError as e:
            raise ManifestError(e.message) from e

        if self.validity is not Validity.IN_FORCE and not self.validity_note:
            raise ManifestError(
                f"Item '{self.item_id}' is marked '{self.validity.value}' but its validity_note is "
                f"empty. Name the instrument that changed it — the amending act, the judgment, or "
                f"the repeal — so the next reader can check it rather than take our word for it."
            )

        lang = _required_text(self.lang, "lang").lower()
        if not _LANG.match(lang):
            raise ManifestError(
                f"The lang field is '{lang[:20]}', which is not an ISO 639-3 code. Use a "
                f"three-letter code such as 'eng'."
            )
        object.__setattr__(self, "lang", lang)

        retrieved = _required_text(self.retrieved, "retrieved")
        if not _ISO_DATE.match(retrieved):
            raise ManifestError(
                f"The retrieved field is '{retrieved[:20]}', which is not an ISO date. Use "
                f"YYYY-MM-DD, so retrieval dates sort and diff."
            )
        object.__setattr__(self, "retrieved", retrieved)

        try:
            size = int(str(self.bytes).strip())
        except (TypeError, ValueError) as e:
            raise ManifestError(
                f"The bytes field is '{str(self.bytes)[:20]}', which is not a whole number."
            ) from e
        if size < 0:
            raise ManifestError(f"The bytes field is {size}, but a size cannot be negative.")
        object.__setattr__(self, "bytes", size)

        digest = _required_text(self.sha256, "sha256").lower()
        if not _SHA256.match(digest):
            raise ManifestError(
                f"The sha256 field is '{digest[:20]}', which is not a SHA-256 digest. Expected 64 "
                f"lowercase hex characters; got {len(digest)}."
            )
        object.__setattr__(self, "sha256", digest)

    def banner(self) -> str:
        """The validity line that must precede any quote of this item."""
        return self.validity.banner(self.validity_note)

    def to_row(self) -> dict:
        return {
            "item_id": self.item_id,
            "citation": self.citation,
            "title": self.title,
            "authority_tier": self.authority_tier.value,
            "validity": self.validity.value,
            "validity_note": self.validity_note,
            "version_id": self.version_id,
            "lang": self.lang,
            "source_url": self.source_url,
            "retrieved": self.retrieved,
            "media_type": self.media_type,
            "bytes": str(self.bytes),
            "sha256": self.sha256,
        }

    @classmethod
    def from_row(cls, row: dict) -> "ManifestItem":
        keys = set(row)
        unknown = keys - set(COLUMNS)
        if unknown:
            raise ManifestError(
                f"The row carries column(s) not in the schema: {', '.join(sorted(unknown))}. The "
                f"schema is: {', '.join(COLUMNS)}."
            )
        missing = set(COLUMNS) - keys
        if missing:
            raise ManifestError(
                f"The row is missing column(s): {', '.join(sorted(missing))}. Every manifest row "
                f"must carry all {len(COLUMNS)} columns."
            )
        return cls(**row)


def _coerce(value, parser):
    if isinstance(value, (Validity, AuthorityTier)):
        return value
    return parser(value)


@dataclass
class Manifest:
    """The set of items in one corpus."""

    items: list = field(default_factory=list)

    def __post_init__(self):
        self.items = list(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Manifest):
            return NotImplemented
        return sorted(self.items, key=lambda i: i.item_id) == sorted(
            other.items, key=lambda i: i.item_id
        )

    def __getitem__(self, item_id: str) -> ManifestItem:
        for item in self.items:
            if item.item_id == item_id:
                return item
        known = ", ".join(sorted(i.item_id for i in self.items)[:8]) or "(the manifest is empty)"
        raise ManifestError(
            f"No item '{item_id}' in this manifest. Known item_ids include: {known}."
        )

    def by_authority(self):
        """Items sorted most-binding first, then by id, so conflicts read in the right order."""
        return sorted(self.items, key=lambda i: (i.authority_tier.rank, i.item_id))

    def _check_unique(self):
        seen = set()
        for item in self.items:
            if item.item_id in seen:
                raise ManifestError(
                    f"item_id '{item.item_id}' appears more than once. Each corpus item needs a "
                    f"unique id, because it is the key cite.py resolves a citation through."
                )
            seen.add(item.item_id)

    def write(self, path) -> None:
        self._check_unique()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(COLUMNS), delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for item in sorted(self.items, key=lambda i: i.item_id):
                writer.writerow(item.to_row())

    @classmethod
    def read(cls, path) -> "Manifest":
        path = Path(path)
        if not path.exists():
            raise ManifestError(
                f"No manifest at {path}. Run the corpus fetcher for this repo to create it."
            )
        items = []
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for offset, row in enumerate(reader, start=2):
                try:
                    items.append(ManifestItem.from_row(row))
                except ManifestError as e:
                    raise ManifestError(f"{path} line {offset}: {e.message}") from e
        return cls(items)
