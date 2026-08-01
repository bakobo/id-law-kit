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

The recurring shape: **the broken output looks fine.** A footer between "the business shall" and
"not retain" reads plausibly and greps wrong. Layout-only characters are invisible. A `.doc.xml`
descriptor parses cleanly and contains no law.

Rules that follow:

- **Refuse empty extractions.** A PDF that extracts to whitespace is a scanned image needing OCR,
  not a provision with no text. Storing it puts a blank entry in the corpus that reads like success.
- **Normalise layout-only characters**, and only those. No-break spaces, figure spaces, non-breaking
  and soft hyphens go; curly quotes and en dashes stay, because they are visible and in EU drafting
  the quotes mark defined terms.
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
