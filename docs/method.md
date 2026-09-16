# Method — how these corpora are built and used

The jurisdiction-neutral generalisation of `utah-id-law/docs/research-strategy.md`. Read this before
adding to any corpus repo.

The failure mode in AI-assisted legal research is not sloppiness. It is **fluent, confident,
fabricated citation** — and, a layer beneath that, **fluent, confident, fabricated absence**. Most
of what follows is machinery against those two.

---

## 1. Corpus first, model second

**Every claim about the law must be produced by `lawcite`, not from memory.** A model asked "what
does X law require for Y" will produce a plausible section number with a plausible quotation, and
both may be inventions.

> **Quote-or-drop.** A claim is admissible only with (a) a citation and (b) a verbatim quotation
> retrievable from `corpus/`. If the quote cannot be reproduced, the claim is **deleted** — not
> hedged, not softened. "I recall that the GDPR requires…" is not evidence.

Retrieval is `lawcite` and `rg -z`, never recall.

### Quote-or-drop has a hole, and it is the dangerous one

Quote-or-drop proves a passage was **published**. It does not prove the passage is **law**.

Section 57 of India's Aadhaar Act was struck down by the Supreme Court in 2018. The Act PDF that
UIDAI publishes today still contains it. An agent diligently following quote-or-drop over that PDF
produces a confidently false claim — the exact failure the rule was written to prevent, arrived at
by obeying the rule.

So every corpus item carries `validity` and `authority_tier`, both **required with no default**, and
`lawcite` prints a validity banner above every quote. Enforcement sits at two chokepoints — the
fetcher refuses to write, the citer refuses to print silently — rather than in a document someone
has to remember. See [`taxonomy.md`](taxonomy.md).

### And a second hole, one layer down, wherever the text is not in your language

Quote-or-drop over a *translation* proves only that a passage was translated. Japan's e-Gov service
and Korea's KLRI both publish official English renderings and both disclaim legal effect in their own
words; KLRI's English PIPA is eleven months behind the Korean text it renders.

So every item also carries `translation_status`, required with no default, enforced at the same two
chokepoints, and a translation is a separate corpus item linked to its original by `translation_of`.
Machine translation is quotable by nothing: it is a reading aid for deciding which provision to have
rendered properly. See [`taxonomy.md`](taxonomy.md) §4 — including Singapore, which is natively
English and *still* not authoritative, for a reason this field deliberately does not cover.

---

## 2. Verify the work-list before you harvest it

A remembered citation is exactly the kind of plausible fabrication this whole apparatus exists to
catch, and once the text is in the corpus the error is invisible: you have real law, correctly
manifested, under the wrong name.

**So every candidate carries an expected phrase, and the harvester checks it against the title the
source actually returns.** `eu-data-law/tools/candidates.py` is the pattern.

This is not theoretical. It caught a real error in the first EU harvest: C-634/21 is universally
cited as *SCHUFA*, but SCHUFA Holding AG was the intervener — the official party name is
*OQ v Land Hessen*, and no EUR-Lex title contains the word "SCHUFA". The CELEX was right and the
label was wrong, which is the direction of error nothing else would have surfaced.

**Where an independent authority states what the corpus should contain, make it a hard oracle.**
The California regulations harvest checks its section list against the Office of Administrative
Law's Notice of Approval and *aborts* on a mismatch, because a partial chapter that looks complete
is worse than a failed run. It matched 49 for 49 — which simultaneously verified the PDF
extraction, the section splitter, and the scope decision.

---

## 3. Searching well

### The phrase-family problem

Keyword search under-detects, because law expresses the same duty many ways. Any sweep supporting a
**negative** conclusion must run the whole family:

- **Proofing:** `proof of identity`, `verif\w+ the identity`, `identity verification`,
  `documentary evidence`, `satisfactory evidence of identity`
- **Document presentation:** `present .{0,30}(driver licen[cs]e|identification card)`,
  `valid .{0,20}identification`, `government-issued`, `photo identification`
- **Attestation (the competing design):** `under penalty of perjury`, `sworn statement`,
  `affidavit`, `attest`
- **Status checks:** `lawful presence`, `status verification`, `E-verify`
- **Identifiers as proxies:** `social security number`, `date of birth`, `biometric`

Two rules learned the hard way in Utah:

1. **Search for the competing design too.** 89 "penalty of perjury" against 17 "verify the identity"
   is a stronger result than either count alone, because it shows the legislature had a
   verification option available and chose otherwise.
2. **Report where hits cluster, not just how many.** The distribution is more probative than the
   total.

### Terms of art beat plain language, and you must find out which you have

`verify the identity of the consumer` returns **nothing** in the CCPA. `verifiable consumer request`
returns 21 lines across 8 sections. The statute has a term of art; the plain-language phrase is not
it. Until you have found the term of art, a zero tells you nothing about the law.

### Counts are pointers to read, never findings

Including our own. Utah's Title 78B once ranked among the top identity-proofing titles in a keyword
sweep — until the hits turned out to be a *blockchain* definitions section.

---

## 4. A zero result is a question, not an answer

This deserves its own section because it is the most repeated lesson across four regimes, and every
instance was silent.

**Interrogate every zero before reporting it.** Run a positive control: search for something you
*know* is in the corpus, using the same tool and a similar pattern. If the control also returns
zero, the tool is broken, not the law.

Four real instances from building these repos, none of which announced itself:

| What returned zero | Why | How it would have read |
|---|---|---|
| `Article 22` across the EU corpus | EU text uses **U+00A0** between "Article" and the number — 232 times in one judgment | "The GDPR does not discuss automated decision-making" |
| `C-311/18` | **U+2011** non-breaking hyphen in case numbers | "Schrems II is not cited anywhere" |
| Every search over the ARF corpus | `CorpusStore` hardcoded `.txt`; the ARF is stored as `.md` | "The ARF nowhere mentions zero-knowledge proofs" |
| `verify the identity of the consumer` in the CCPA | Wrong term of art | "California imposes no identity-verification duty" |

The first three are now fixed in `lawcorpus`. The fourth is not fixable in code — it is why the rule
above exists.

**And a zero that survives interrogation is still only a claim about a corpus, not about the world.**
Absence of a phrase family is evidence of absence, not proof of it. Every negative finding must name
the corpus it searched and the layer it did not.

---

## 5. Layers — and the ways a corpus is silently incomplete

A complete answer usually spans more layers than the obvious one. Utah reached a wrong answer from
statute alone **twice**: the fishing-licence identity requirement existed only in the administrative
rules, and the court-filing question was unanswerable until the court rules arrived.

| Layer | Typical form | How it goes missing |
|---|---|---|
| Constitutional | charters, basic law, apex judgments | assumed rather than read |
| Legislative | statutes, regulations (EU sense) | the layer people stop at |
| Delegated | agency rules, implementing acts | *the one that changes answers* |
| Judicial | binding decisions | excluded as "not text" |
| Regulator guidance | EDPB opinions, agency manuals | not published as a corpus |
| Sub-national / transposition | 27 member states, county policy | too large to archive, so silently skipped |

Two failure shapes worth naming:

**No consolidated current text exists.** For CCR Title 11 there is no reachable document containing
the current chapter; it had to be assembled from two rulemaking packages, and twelve sections
appeared in only one of them. Whether those were *unchanged* or *repealed* was not inferable from
the texts — only the OAL notice said. When you cannot tell, **find the instrument that says**; do
not infer.

**Original vs. consolidated.** EUR-Lex serves both `32016R0679` (as published in 2016) and
`02016R0679-<date>` (incorporating amendments). For an instrument amended more than once, quoting
the original is simply wrong. The corpus pins a *version*, not just an identifier — the analogue of
Utah's version stamps.

---

## 6. Extraction is where corpora quietly go wrong

Three renderers ship in `lawcorpus`, in descending order of trustworthiness:

| Format | Module | Risk |
|---|---|---|
| **Formex** (EU) | `formex.py` | Low — it is markup; structure is given |
| **CAML** (California) | `caml.py` | Low, one trap: subdivision labels separated by an empty `<span class="EnSpace"/>`, so a naive tag-strip yields `(a)A business` |
| **PDF** | `pdf.py` | High — a page description, so reading order is *inferred* and running headers land mid-sentence |
| **PDF, Thai** | `thai.py` | Highest — the general path loses characters silently; see below |

The recurring shape: **the broken output looks fine.** A footer between "the business shall" and
"not retain" reads plausibly and greps wrong. Layout-only characters are invisible. A `.doc.xml`
descriptor parses cleanly and contains no law.

Rules that follow:

- **Refuse empty extractions.** A PDF that extracts to whitespace is a scanned image needing OCR,
  not a provision with no text. Storing it puts a blank entry in the corpus that reads like success.

- **Refuse *incomplete* extractions, which is the harder half.** The empty guard catches the failure
  that announces itself. Indonesia's UU 27/2022 is fifty 400-dpi CCITT scans with an OCR layer: it
  extracts to 52 KB of entirely plausible Indonesian, passes every emptiness check, and is missing
  Pasal 22, 70 and 72 and the whole of BAB XI–XII. `Pasal 22` returns 0 where `Pasal 21` returns 3
  and `Pasal 23` returns 2.

  So `lawcorpus/completeness.py` compares an extraction against a declared structure and **aborts**,
  the way the California harvest aborts against the OAL notice. It catches interior gaps *and*
  truncated tails — the Indonesian failure is both — and the error names the missing provisions
  rather than reporting a count, because a count sends the next reader looking and a list tells them
  where. `CorpusStore.write(..., expect=...)` refuses before anything reaches disk.

  **Three sources declare their own structure, so most instruments need no hand-written oracle.**
  Japan's per-instrument `<TOC><ArticleRange>` is authored by the publisher, so it is independent
  evidence and needs no second document. Korea's article numbering is gapless from 1 to the maximum,
  because a repealed article survives as a `삭제` placeholder — it held 7 for 7 in Phase 0, and being
  self-derived it sees an interior gap but not a truncated tail. Indonesia's per-record
  `status_hukum` maps onto the `validity` vocabulary directly, which is the one place in this
  programme where validity is machine-derived rather than curated.
- **Normalise layout-only characters**, and only those — **unconditionally, for every document,
  whatever language it is in.** No-break spaces, figure spaces, the ideographic space, non-breaking
  and soft hyphens, zero-width characters and the full-width variants of ASCII all go; curly quotes,
  en dashes, U+3001 `、`, U+3002 `。` and U+318D `ㆍ` stay, because they are visible characters
  carrying their own meaning rather than width. `lawcorpus/normalise.py` is the one set.

  **Never switch this on a language tag.** Phase 0 tested that design and falsified it: Japanese
  uses U+3001 and *zero* U+FF0C, Korean has no full-width punctuation at all but 4,966 instances of
  U+318D, Chinese uses both commas with the ideographic one ahead, Singapore's English carries the
  EU's U+2011 — and the **English-language** CTID specification contains stray full-width
  parentheses, which no language-keyed rule would have routed to a fix.

  **And never reach for NFKC.** It looks like the general form of this fold. Applied to Thai it
  decomposes U+0E33 `ำ`, taking `สำนักงาน` from 18 hits to 0: the standard remedy generating the
  exact silent false negative the rule exists to prevent.

- **Some characters must survive normalisation and still be searchable, so the query moves instead.**
  Full-width enumerators like `（一）` address provisions, so stripping them breaks citation; U+318D
  is visible, so it stays. `lawcorpus.normalise.normalise_query` folds the *pattern* the same way the
  text was folded and expands a list separator to match all five of its spellings, which is why
  `lawcite --grep` finds text no literal `rg` would. For comparing two strings rather than searching
  — the expected-phrase check of §2 — use `search_key`, which also folds Thai and Arabic numerals
  together and collapses the line wrapping that made that check abort on a *correct* Thai document.
- **Use `thai.py` for Thai PDFs, and let it refuse.** `pdftotext` drops U+0E33 `ำ` from Royal
  Gazette PDFs **100% of the time**, so `กำหนด` — "to prescribe" — occurs 87 times in the PDPA and
  matches zero. It is producer-dependent, so a spot check on a Word-produced document finds nothing
  wrong. Other Gazette PDFs carry a subset font with no ToUnicode CMap and extract to non-empty,
  plausibly-Thai-looking noise, with the running header extracting *correctly* while the body does
  not. So a page whose Thai character ratio collapses, and a document with no `ำ` at all, are
  refused and routed to OCR. Never reach for NFKC on Thai; the Thai API text is the corpus and the
  Gazette PDF is provenance.

- **Preserve structure.** "Article 5(1)(a)" must be locatable in the stored text, or quote-or-drop
  degrades into "the phrase appears somewhere in a 90,000-word file."
- **Sanity-check the shape.** The GDPR has 99 articles and 173 recitals. If your extraction says
  otherwise, it is your extraction that is wrong.

---

## 7. Panel design — adversarial, not survey

Fan out only after the cheap probe.

- **Steelman** — build the strongest case *for* the claim under test. Run first; if it comes back
  thin, the question may already be closed.
- **Refuter** — hunt counterexamples, and hunt **exemption lists** specifically. A legislature
  enumerating exceptions has often refuted a universal claim in its own words.
- **Definitions** — resolve the terms of art against [`taxonomy.md`](taxonomy.md) before arguing.
- **Domain probes, in parallel** — one per program family. Each answers: what duty, from which
  provision, with what scope conditions and exemptions.
- **Verifier** — one adversarial pass per surviving claim, prompted to *refute*, with corpus access.
  Its job is to break the quote-to-claim link, not to agree.
- **Cross-model check** — put the final conclusion to `codex exec` or `gemini -p`. Different model,
  genuine perspective variety, cheap.

**Quantifier asymmetry.** A universal claim ("any time…") is refuted by one well-sourced
counterexample; it is *established* only by a general provision. Whoever asserts the universal owes
the citation. Refutation is cheap — do it first.

Respect the machine limits in `~/.claude/CLAUDE.md`: at most 4 general-purpose subagents at once
(6–8 if the extras are read-only), and `nice -n 19` for anything heavy.

---

## 8. Standing cautions

- **Not legal advice.** This is textual research by non-lawyers. For a specific programme the
  binding answer often lives in an agency manual or unpublished policy.
- **Law changes.** Findings cite retrieval dates and version identifiers for this reason. Refetch
  before relying on an old finding.
- **Redistribution bases do not generalise.** "Edicts of government carry no copyright" is US
  doctrine. EU material is © European Union under Decision 2011/833/EU with attribution; Indian
  government works sit under GODL-India. Each repo states its own — never copy one repo's licence
  reasoning into another.
- **Scope is a file, not a vibe.** Where a regime has no natural edge, write the boundary down
  (`candidates.py`, `regs_sources.py`) so that "out of scope" is a decision rather than an oversight,
  and put what was left out in the README's Known Gaps with a date.
