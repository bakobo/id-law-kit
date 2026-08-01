# id-law-kit — method and tooling for the identity-law corpora

[![CI](https://github.com/bakobo/id-law-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/bakobo/id-law-kit/actions/workflows/ci.yml)

Shared machinery for a family of repos that harvest primary legal sources so they can be analysed
later — by a person or by an AI — **without repeating the online research, and without trusting
anyone's memory of what the law says.**

| Repo | Regime |
|---|---|
| [`utah-id-law`](https://github.com/bakobo/utah-id-law) | Utah identity-verification law |
| [`eu-data-law`](https://github.com/bakobo/eu-data-law) | GDPR + EU data-locality stack |
| [`eidas-eudi`](https://github.com/bakobo/eidas-eudi) | eIDAS 2, EUDI wallet, ARF |
| [`ccpa`](https://github.com/bakobo/ccpa) | California CCPA/CPRA |
| [`aadhaar`](https://github.com/bakobo/aadhaar) | Aadhaar Act, UIDAI regs, DPDP Act |

This repo holds no legal corpus of its own. It holds the method, the schema, and the code.

## The problem it solves

Language models fabricate legal citations fluently and confidently. The countermeasure, established
in `utah-id-law`, is **quote-or-drop**: a claim about the law is admissible only with a citation
*and* a verbatim quote retrievable from a local corpus file. If the quote cannot be reproduced, the
claim is deleted rather than softened.

That rule has a hole, and this repo exists partly to close it. Quote-or-drop guarantees the text was
*published*. It does not guarantee the text is *law*. Section 57 of India's Aadhaar Act was struck
down by the Supreme Court in 2018, but the Act PDF that UIDAI publishes today still contains it. A
diligent agent following quote-or-drop over that PDF produces a confidently false claim — the exact
failure the rule was written to prevent.

So every corpus item here carries two fields beyond provenance:

- **`validity`** — `in-force` · `amended` · `struck-down` · `read-down` · `not-yet-applicable` ·
  `repealed`, with a pointer to the instrument that changed it.
- **`authority_tier`** — `constitutional` · `legislative` · `delegated` · `judicial` ·
  `regulatory-guidance` · `commentary`.

Both are **required, with no default**. The fetcher refuses to write an item without them, and
`cite.py` prints a validity banner above every quote. Enforcement sits at those two chokepoints
rather than in a document someone has to remember.

## Install

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest              # tests
.venv/bin/python -m pytest --cov        # tests with branch coverage
```

## Layout

```
lawcorpus/validity.py      the validity + authority vocabularies, and the quote banner
lawcorpus/manifest.py      one manifest schema: read, write, validate
lawcorpus/store.py         gzip corpus store — write-with-hash, read, verify
lawcorpus/cite.py          the citation primitive; quotes never print without a validity banner
lawcorpus/formex.py        Formex XML -> citable text (articles, recitals, paragraph numbering)
lawcorpus/caml.py          CAML XML -> citable text (California codified sections)
lawcorpus/pdf.py           PDF -> citable text via poppler, with running-furniture removal
lawcorpus/fetch/eurlex.py  EUR-Lex / Cellar fetcher, shared by eu-data-law and eidas-eudi
docs/method.md             how the research is done — read before adding to any corpus repo
docs/taxonomy.md           the duty taxonomy, the authority ladder, the validity vocabulary
docs/questions.md          the shared question spine, so findings are comparable across regimes
```

## One thing that will cost you a day if you don't know it

EUR-Lex's metadata notices carry **no operative text**. `Accept: application/xml;notice=branch`
returns 1.8 MB for the GDPR and looks like a full document; it is a bibliographic tree with not one
article in it. The text arrives only under `Accept: application/zip;mtype=fmx4`, as a zip whose
larger member is Formex XML — and that zip contains a second, tiny `.doc.xml` descriptor which also
parses cleanly and also contains no law.

`EurLexFetcher.fetch_formex()` handles both traps. `Accept-Language` is mandatory on every request;
omitting it returns HTTP 400 with a plain-text explanation.

## The manifest

One tab-separated schema for every corpus, so `cite.py` and `sweep.py` work everywhere:

| Column | Meaning |
|---|---|
| `item_id` | stable local key; the filename stem under `corpus/` |
| `citation` | the canonical citation as a lawyer would write it |
| `title` | human-readable name of the instrument or provision |
| `authority_tier` | see above — required |
| `validity` | see above — required |
| `validity_note` | what changed it: the amending act, the judgment, the repeal |
| `version_id` | the version this pins — a consolidation date, a version stamp, a release tag |
| `lang` | ISO 639-3 (`eng`) |
| `source_url` | where it was retrieved from |
| `retrieved` | ISO date |
| `media_type` | as served |
| `bytes` | size of the stored text |
| `sha256` | hash of the stored text |

A refetch that diffs cleanly against `sha256` proves nothing changed. A refetch that doesn't tells
you exactly what to re-read.

## What this repo does not do

It does not decide whether a corpus is complete, and it cannot tell you that an absence is
meaningful. Every regime repo carries its own **Known Gaps** section for that, and every negative
finding ("the law nowhere requires X") is a claim about a corpus, not about the world.

## Licence

[CC BY 4.0](LICENSE). Attribution: Bakobo, *id-law-kit*. No legal corpus is redistributed from this
repo; each regime repo states its own redistribution basis, which differs by jurisdiction and does
not generalise.

**Not legal advice.** This is tooling for textual research, built by non-lawyers.
