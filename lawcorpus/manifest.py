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
    TranslationStatus,
    TranslationStatusError,
    Validity,
    ValidityError,
    parse_authority_tier,
    parse_translation_status,
    parse_validity,
    quotable_as_current_law,
    quotable_as_evidence,
)

COLUMNS = (
    "item_id",
    "citation",
    "title",
    "authority_tier",
    "validity",
    "validity_note",
    "translation_status",
    "translation_of",
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
    translation_status: TranslationStatus
    version_id: str
    lang: str
    source_url: str
    retrieved: str
    media_type: str
    bytes: int
    sha256: str
    validity_note: str = ""
    translation_of: str = ""

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
        object.__setattr__(
            self, "translation_of", "" if self.translation_of is None else str(self.translation_of).strip()
        )

        try:
            object.__setattr__(self, "validity", _coerce(self.validity, parse_validity))
            object.__setattr__(
                self, "authority_tier", _coerce(self.authority_tier, parse_authority_tier)
            )
            object.__setattr__(
                self,
                "translation_status",
                _coerce(self.translation_status, parse_translation_status),
            )
        except (ValidityError, TranslationStatusError) as e:
            raise ManifestError(e.message) from e

        if self.translation_status is not TranslationStatus.AUTHORITATIVE:
            if not self.translation_of:
                raise ManifestError(
                    f"Item '{self.item_id}' is a '{self.translation_status.value}' rendering but "
                    f"its translation_of is empty. Name the item_id of the text it translates, so "
                    f"a reader who may not quote this one can reach the text that binds."
                )
            if self.authority_tier is not AuthorityTier.COMMENTARY:
                raise ManifestError(
                    f"Item '{self.item_id}' is a '{self.translation_status.value}' rendering filed "
                    f"at authority_tier '{self.authority_tier.value}'. A translation that is not "
                    f"authentic text cannot outrank the instrument it renders, so it belongs at "
                    f"commentary."
                )

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

    def banners(self) -> list:
        """Every line that must precede a quote of this item, validity first.

        A translation carries two: what happened to the instrument, and whether this is the text
        that binds. An authentic item carries one, because a translation banner on it would be
        noise.
        """
        lines = [self.banner()]
        translation = self.translation_status.banner(self.translation_of)
        if translation:
            lines.append(translation)
        return lines

    def quotable_as_current_law(self) -> bool:
        """May this item be presented as a statement of what the law is today?

        Both fields must allow it. An in-force machine translation fails here, which is the point
        of @c5jtwe4i: the instrument is current and our rendering of it is not evidence.
        """
        return quotable_as_current_law(self.validity) and quotable_as_evidence(
            self.translation_status
        )

    def to_row(self) -> dict:
        return {
            "item_id": self.item_id,
            "citation": self.citation,
            "title": self.title,
            "authority_tier": self.authority_tier.value,
            "validity": self.validity.value,
            "validity_note": self.validity_note,
            "translation_status": self.translation_status.value,
            "translation_of": self.translation_of,
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
    if isinstance(value, (Validity, AuthorityTier, TranslationStatus)):
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

    def _check_translation_links(self):
        """Every `translation_of` must reach an item in this manifest.

        Checked when the manifest is written rather than when an item is constructed, because an
        item does not know its siblings. A dangling pointer would otherwise surface years later,
        inside a citation, which is the worst place to find it.
        """
        known = {item.item_id for item in self.items}
        for item in self.items:
            if not item.translation_of:
                continue
            if item.translation_of == item.item_id:
                raise ManifestError(
                    f"Item '{item.item_id}' names itself as the text it translates. A translation "
                    f"and its original are two corpus items, with two source URLs and two digests."
                )
            if item.translation_of not in known:
                raise ManifestError(
                    f"Item '{item.item_id}' translates '{item.translation_of}', which is not in "
                    f"this manifest. Harvest the original too — a translation nobody can check "
                    f"against its source is the failure translation_status exists to surface."
                )

    def write(self, path) -> None:
        self._check_unique()
        self._check_translation_links()
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
