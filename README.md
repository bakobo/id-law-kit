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

The same hole opens a second time wherever the text is not in your language. Quote-or-drop over an
English rendering of a Japanese Act proves only that somebody translated it — and Japan's and
Korea's official translation services both disclaim legal effect in their own words, while Korea's
English privacy statute runs eleven months behind the Korean text it renders.

So every corpus item here carries three fields beyond provenance:

- **`validity`** — `in-force` · `amended` · `struck-down` · `read-down` · `not-yet-applicable` ·
  `repealed`, with a pointer to the instrument that changed it.
- **`authority_tier`** — `constitutional` · `legislative` · `delegated` · `judicial` ·
  `regulatory-guidance` · `commentary`.
- **`translation_status`** — `authoritative` · `official-non-authoritative` · `unofficial` ·
  `machine`, with `translation_of` naming the item this renders. Machine output is never quotable.

All three are **required, with no default**. The fetcher refuses to write an item without them, and
`cite.py` prints a validity banner — and a translation banner, where the text is not authentic —
above every quote. Enforcement sits at those two chokepoints rather than in a document someone has
to remember.

## Install

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest              # tests
.venv/bin/python -m pytest --cov        # tests with branch coverage
```

## Layout

```
lawcorpus/validity.py      the validity, authority and translation vocabularies, and the banners
lawcorpus/manifest.py      one manifest schema: read, write, validate
lawcorpus/migrate.py       bring a manifest onto the current schema, with the value stated
lawcorpus/store.py         gzip corpus store — write-with-hash, read, verify
lawcorpus/cite.py          the citation primitive; quotes never print without a validity banner
lawcorpus/normalise.py     the one layout fold, applied to every document whatever its language
lawcorpus/completeness.py  refuses an extraction that is full but missing provisions
lawcorpus/formex.py        Formex XML -> citable text (articles, recitals, paragraph numbering)
lawcorpus/caml.py          CAML XML -> citable text (California codified sections)
lawcorpus/pdf.py           PDF -> citable text via poppler, with running-furniture removal
lawcorpus/thai.py          Thai PDFs, which the general path loses characters from silently
lawcorpus/japanese.py      Japanese PDFs, which the general path welds a space into silently
lawcorpus/fetch/eurlex.py  EUR-Lex / Cellar fetcher, shared by eu-data-law and eidas-eudi
lawcorpus/fetch/browser.py browser fetcher for challenge-fronted and JS-rendered sources
                           (optional: `pip install 'lawcorpus[browser]'`)
docs/method.md             how the research is done — read before adding to any corpus repo
docs/taxonomy.md           the duty taxonomy, the authority ladder, validity and translation
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

## A third thing, if the corpus is not in a Latin script

`pdf.extract` is English below the surface. Its line rejoiner reads a line as mid-sentence unless it
ends in `.:;?!` and rejoins with **a space**, which neither Japanese nor Thai writes between words.
It now refuses a predominantly CJK extraction and names `lawcorpus.japanese.extract_japanese`,
which rejoins with no separator; `lawcorpus.thai.extract_thai` gates the two ways `pdftotext`
destroys Thai. Neither is a repair of the general path — both refuse more than they fix, because
text stored after being mangled is the failure that looks like success.

On the search side, a CJK query built with `normalise_query` tolerates the space that Japanese
heading typography puts *inside* a short word: e-Gov writes 「附　則」, so a bare `rg 附則` finds none
of the supplementary-provision headings in a corpus while finding every cross-reference to them.
`lawcite --grep` already goes through it; a hand-written `rg` does not.

## A second thing, if you reach for the browser fetcher

`lawcorpus.fetch.browser` exists for two obstacles only: a Cloudflare challenge on a site's HTML
routes (Thailand's Royal Gazette serves `/documents/<id>.pdf` while challenging everything else),
and a page that renders client-side with no API behind it (`bora.dopa.go.th`). **It does not help
with a blocked socket** — `peraturan.go.id` black-holes the TCP SYN and every `kemendagri.go.id`
host is blocked outright, and Chromium reaches those exactly as well as curl does. The remedy there
is a different egress, not a different client.

It refuses rather than returns when a host says no, and it does not solve challenges. Where a
source permits automation only within hours — Singapore's SSO terms clause (13)(d), 3–7 a.m. SGT —
declare an `AccessWindow` and the fetch is refused outside it before the browser starts.

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
| `translation_status` | see above — required |
| `translation_of` | the `item_id` this renders; mandatory unless `translation_status` is `authoritative` |
| `version_id` | the version this pins — a consolidation date, a version stamp, a release tag |
| `lang` | ISO 639-3 (`eng`) |
| `source_url` | where it was retrieved from |
| `retrieved` | ISO date |
| `media_type` | as served |
| `bytes` | size of the stored text |
| `sha256` | hash of the stored text |

A refetch that diffs cleanly against `sha256` proves nothing changed. A refetch that doesn't tells
you exactly what to re-read.

### Migrating a manifest written before `translation_status`

`translation_status` and `translation_of` were added as required fields, so a manifest written
before them no longer reads — `Manifest.read` refuses it by name and prints the command below. The
kit does **not** infer the missing value: reading "no translation columns" as `authoritative` is the
default the field exists to refuse, and it would be silently wrong for the first corpus that
predates the column and holds a translation. Somebody who knows the corpus states the value once,
and commits it:

```sh
python -m lawcorpus.migrate corpus/MANIFEST.tsv --translation-status authoritative
python -m lawcorpus.migrate corpus/MANIFEST.tsv --translation-status authoritative --dry-run
```

`--translation-status` is required and has no default. Only `authoritative` may be assigned in bulk;
a rendering that is not authentic text owes a `translation_of` that an old manifest does not record,
so a corpus of translations is re-harvested rather than rewritten. Every row is rebuilt through
`ManifestItem`, so the migration revalidates the whole file and writes nothing if any row fails.
`--retier old=new` rewrites an `authority_tier` in the same pass — `--retier standard=commentary`
is the one this programme needed. See `this.i` @oa2bvav5 and @3zljqayt.

## What this repo does not do

It does not decide whether a corpus is complete, and it cannot tell you that an absence is
meaningful. Every regime repo carries its own **Known Gaps** section for that, and every negative
finding ("the law nowhere requires X") is a claim about a corpus, not about the world.

## Licence

[CC BY 4.0](LICENSE). Attribution: Bakobo, *id-law-kit*. No legal corpus is redistributed from this
repo; each regime repo states its own redistribution basis, which differs by jurisdiction and does
not generalise.

**Not legal advice.** This is tooling for textual research, built by non-lawyers.
