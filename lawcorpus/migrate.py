"""Bring a manifest onto the current schema, with the new field's value stated rather than guessed.

`translation_status` and `translation_of` were added as required fields with no default (this.i
@elsvh64d) and shipped with no migration, so `Manifest.read` began refusing seven manifests across
four corpus repos — every published corpus except `japan-id`.

The tempting repair is a reader that treats a manifest with no translation columns as
`authoritative`. That is precisely the default @elsvh64d rejected, wearing a schema version: it
infers the value from the *absence* of the value, it happens to be right for all seven of these
files, and it would be silently wrong for the first corpus that predates the column and holds a
translation. So the migration is a one-shot script the corpus repo runs, and

    --translation-status has no default.

Somebody who knows the corpus types the value, reads the diff, and commits it. The assignment then
has an author and a date, which is what makes it checkable later. See @oa2bvav5.

Only `authoritative` may be assigned in bulk. A non-authoritative item owes a `translation_of`
naming the original it renders (@xsjnzwvu), and an old manifest does not record one — a corpus of
translations must be re-harvested, not rewritten.

    python -m lawcorpus.migrate ../ccpa/corpus/MANIFEST.tsv --translation-status authoritative
    python -m lawcorpus.migrate corpus-specs/MANIFEST.tsv --translation-status authoritative \\
        --retier standard=commentary
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import LawcorpusError
from .manifest import COLUMNS, LEGACY_COLUMNS, Manifest, ManifestItem
from .validity import TranslationStatus, parse_translation_status


class MigrationError(LawcorpusError):
    """A migration that cannot be performed as it was asked for.

    `input.format` and not `state.stale`: the manifest is whatever it is, and what is wrong is the
    instruction — a path that is not a manifest of the schema being migrated from, a status that
    cannot be assigned in bulk, a retier that matches nothing.
    """

    code = "e.input.format.migration.f"


@dataclass(frozen=True)
class Migration:
    """What one migrated file gained."""

    path: Path
    rows: int
    translation_status: str
    retiered: dict


def _header(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return csv.DictReader(fh, delimiter="\t").fieldnames or []


def migrate(path, *, translation_status: str, retier: dict = None, dry_run: bool = False):
    """Rewrite one legacy manifest on the current schema, or refuse and say why.

    Every row is reconstructed through `ManifestItem`, so the migration is also a full revalidation
    of the file: a digest or a date that was wrong before is refused now, and nothing is written.
    """
    path = Path(path)
    retier = dict(retier or {})
    status = parse_translation_status(translation_status)
    if status is not TranslationStatus.AUTHORITATIVE:
        raise MigrationError(
            f"Refusing to assign '{status.value}' to every row. A rendering that is not authentic "
            f"text must name the item it translates, and a manifest written before these columns "
            f"existed records no translation_of to carry over — so this would write a link that "
            f"resolves to nothing. Harvest the originals and re-run the corpus fetcher instead."
        )
    if not path.exists():
        raise MigrationError(f"No manifest at {path}, so there is nothing to migrate.")

    header = _header(path)
    if header == list(COLUMNS):
        raise MigrationError(
            f"{path} is already on the current schema. Migrating it again would rewrite a "
            f"translation_status somebody has curated since."
        )
    if header != list(LEGACY_COLUMNS):
        raise MigrationError(
            f"{path} carries columns this migration does not know how to read: "
            f"{', '.join(header) or '(no header at all)'}. It migrates the schema that predates "
            f"translation_status, whose columns are: {', '.join(LEGACY_COLUMNS)}."
        )

    retiered = {old: 0 for old in retier}
    items = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            tier = row["authority_tier"]
            if tier in retier:
                retiered[tier] += 1
                row["authority_tier"] = retier[tier]
            items.append(
                ManifestItem.from_row(
                    {**row, "translation_status": status.value, "translation_of": ""}
                )
            )

    if not dry_run:
        Manifest(items).write(path)
    return Migration(
        path=path, rows=len(items), translation_status=status.value, retiered=retiered
    )


def _retier_pair(raw: str) -> tuple:
    old, sep, new = raw.partition("=")
    if not sep or not old.strip() or not new.strip():
        raise argparse.ArgumentTypeError(
            f"'{raw}' is not a retier. Write it as old=new, for example standard=commentary."
        )
    return old.strip(), new.strip()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m lawcorpus.migrate",
        description=__doc__.split("\n")[0],
    )
    p.add_argument("manifest", nargs="+", help="the manifest file(s) to migrate, in place")
    p.add_argument(
        "--translation-status",
        required=True,
        help=(
            "the translation_status to assign to every row. Required, and deliberately without a "
            "default: only somebody who knows the corpus can say whether its text is authentic."
        ),
    )
    p.add_argument(
        "--retier",
        action="append",
        default=[],
        type=_retier_pair,
        metavar="OLD=NEW",
        help="rewrite an authority_tier, e.g. standard=commentary",
    )
    p.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    args = p.parse_args(argv)

    retier = dict(args.retier)
    failures, hits = 0, {old: 0 for old in retier}
    for name in args.manifest:
        try:
            report = migrate(
                name,
                translation_status=args.translation_status,
                retier=retier,
                dry_run=args.dry_run,
            )
        except LawcorpusError as e:
            failures += 1
            print(f"FAIL {name}\n  {e}")
            continue
        for old, n in report.retiered.items():
            hits[old] += n
        moved = ", ".join(f"{old}→{retier[old]} ×{n}" for old, n in report.retiered.items() if n)
        tail = f"; retiered {moved}" if moved else ""
        print(
            f"{'dry run' if args.dry_run else 'migrated'} {report.path}: {report.rows} row(s) "
            f"at translation_status={report.translation_status}{tail}"
        )

    # Checked across the whole run rather than per file, because one --retier is given for a set
    # of manifests and only one of them usually carries the tier being corrected.
    unused = sorted(old for old, n in hits.items() if n == 0)
    if unused:
        failures += 1
        print(
            f"FAIL --retier {', '.join(unused)}: no row in any manifest given here carries that "
            f"authority_tier, so the retier did nothing. A retier that matches nothing is a typo "
            f"far more often than it is a no-op, and ignoring it silently is how the tier it was "
            f"meant to correct survives the migration. The translation_status migration above did "
            f"land; re-run with the right tier, or with the manifest that carries it."
        )
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
