# Taxonomy — the vocabularies these corpora share

Four vocabularies, so findings from ten jurisdictions can be compared instead of merely collected:
**what kind of duty** a provision imposes, **how binding** the text is, **whether it is still law**,
and **whether it is the text that binds**.

The last three are machine-readable fields on every corpus item (`lawcorpus/validity.py`); the first
is analytical and lives in prose.

---

## 1. The duty taxonomy

### 1.1 The four duties

Inherited unchanged from `utah-id-law`, because it generalises cleanly. Four distinct duties get
conflated under loose phrases like "strong identification" — which appears in the Utah Code exactly
**zero** times.

| Duty | What it establishes | Typical phrasing |
|---|---|---|
| **Identity assertion** | A name is on record | "shall provide the applicant's name" |
| **Identity proofing** | The claimed identity is real and belongs to the claimant (~NIST IAL2) | "proof of identity", "documentary evidence" |
| **Status verification** | An attribute holds — age, residency, lawful presence | "verify the lawful presence" |
| **Authentication** | A returning party is the same as the record (~NIST AAL) | "credential", "multifactor" |

**A statute demanding the third does not demand the second.** Utah §63G-12-402 demands status
verification and accepts attestation to satisfy it. Conflating these is the single most common
analytical error in this domain.

A fifth distinction earns its place from the rules layer: **collection is not proofing.** Utah rule
R657-45-2 requires a licence form to *collect* name, date of birth, address and physical
description, and requires no one to *verify* any of it.

### 1.2 The second axis: direction of the duty

Utah's four-way split assumes the question is "when must the state identify a person". GDPR and CCPA
regulate a partly opposite direction, and a taxonomy that cannot express "you must **not** retain
identifying data" is useless for them.

| Direction | Question | Example |
|---|---|---|
| `compelled-identification` | When must a party be identified? | Utah §76-8-301.5 — disclose name on a lawful stop |
| `permitted-identification` | When *may* a party be identified, at whose option? | Alternative opt-out mechanisms |
| `prohibited-identification` | When must identity **not** be collected or retained? | GDPR Art. 5(1)(c) data minimisation; Art. 11 |
| `data-locality` | Where may the data sit, and who may reach it? | GDPR Chapter V; Reg. 2018/1807 |
| `requester-verification` | How must you identify someone exercising a right **against you**? | GDPR Art. 12(6); CCPA §1798.130 |

### 1.3 Why `requester-verification` is the connective tissue

It is the one duty family present in every regime in the programme, and it runs in the direction
Utah's framing does not anticipate: the duty falls on the controller, and it is *bounded above* as
well as below — verify enough, but do not use the request as a pretext to collect more.

Confirmed present across the corpora by a single query:

- **GDPR Art. 12(6)** — "where the controller has reasonable doubts concerning the identity of the
  natural person making the request … may request the provision of additional information necessary
  to confirm the identity"
- **LED Art. 12** and **EUDPR Arts. 14 and 78** — the same construction, near-verbatim
- **CCPA** — "verifiable consumer request", the statutory term of art, 21 lines across 8 sections
- **GDPR Art. 11** — the ceiling: a controller need not acquire identifying data merely to comply

A comparative finding on *"how must you identify someone exercising a right against you?"* spans all
five corpora. That is the strongest argument these are one research programme rather than four
hobbies.

---

## 2. The authority ladder

`utah-id-law/sources/registry.md` stated a trust order in prose — "statute and CFR text > official
agency publication > case law > commentary". This makes it a field, so a conflict surfaces in the
citation rather than being resolved silently by whichever text a search happened to hit first.

| `authority_tier` | Rank | What belongs here |
|---|---:|---|
| `constitutional` | 0 | Charters, basic law, apex constitutional judgments |
| `legislative` | 1 | Statutes; EU regulations and directives |
| `delegated` | 2 | Agency rules; EU implementing acts; Commission decisions |
| `judicial` | 3 | Binding court decisions |
| `regulatory-guidance` | 4 | EDPB guidelines, agency manuals, enforcement policy |
| `commentary` | 5 | Technical specifications, explanatory memoranda, everything else |

Lower rank is more authoritative; `Manifest.by_authority()` sorts binding text first.

Two placements worth defending:

**Judicial below delegated is a filing decision, not a jurisprudential one.** It orders *how much
weight the text of the document carries as a statement of the rule*, not who wins a conflict — a
judgment invalidating a Commission decision obviously prevails, and the manifest records that
through `validity` on the invalidated item, not through rank. Where case law is genuinely the
operative source, say so in the finding.

**The EUDI ARF sits at `commentary`.** It is a specification, not law, and cannot override an
implementing act. Filing it below the legal text means a finding that cites the ARF against a
Commission regulation has its ordering visibly backwards.

---

## 3. The validity vocabulary

The field that closes the hole in quote-or-drop. **Required, no default.**

| `validity` | Meaning | Quotable as current law? |
|---|---|---|
| `in-force` | Enacted, applicable, unamended | **Yes** |
| `amended` | Superseded by a later version of the same instrument | No — quote the consolidated text |
| `struck-down` | Invalidated by a court | No |
| `read-down` | Narrowed by a court; the text as written overstates it | No — not without the judgment |
| `not-yet-applicable` | Enacted but not yet in application | No |
| `repealed` | Withdrawn by the legislature | No |

`quotable_as_current_law()` returns True only for `in-force`.

**"Not quotable as current law" is not "useless."** A struck-down provision is still evidence of
what a legislature once enacted, and a superseded wording is what governed conduct at the time. The
corpora keep them deliberately — `ccpa/corpus-regs/` holds 30 superseded 2023 wordings alongside the
current text. The rule is only that a finding may not present them as current law, which the banner
enforces and `lawcite --in-force-only` filters.

### `validity_note` is mandatory whenever validity is not `in-force`

A bare `struck-down` is a dead end for the next reader. The note names **the instrument that did
it** — the amending act, the judgment, the repeal — so the claim can be checked rather than taken
on trust. `ManifestItem` refuses to construct without it.

### Granularity

The field is per corpus **item**, which is the right grain when an instrument is wholly in force or
wholly repealed. It is the wrong grain for the Aadhaar Act, where one section was struck down,
others were read down, and a 2019 amendment rewrote parts. Recording `amended` for the Act as a
whole would hide the thing that matters.

Two ways to get the grain right, in order of preference:

1. **Make the provision the item.** `ccpa/corpus-regs/` stores one section per item, so validity is
   naturally per-section. Prefer this.
2. **Carry a provision-level overlay in the repo that needs it**, rather than pushing the complexity
   into the shared schema for four repos that do not. This is the recorded plan for `aadhaar`
   (`this.i` @4sxgog), with the cost noted: an overlay is a second place that can drift.

### Validity is hand-curated, and that is the point

It cannot be derived mechanically for most items, so it lags. **A wrong `validity` is more dangerous
than an absent one** — which is why it is required with no default rather than an optional
annotation: absence stops the harvest, and a guess would not.

---

## 4. The translation vocabulary

The field that closes the hole in quote-or-drop one layer down. **Required, no default.**

Quote-or-drop over a translation proves that a passage was *translated*. It does not prove that the
passage is the text that binds. Japan's e-Gov translation service says so in its own words —
「法令翻訳は、正文ではなく…法的効力を有するのは日本語の法令自体であり、翻訳はあくまでその理解を助けるための参考資料です」, where
正文 is the technical term for authentic text — and Korea's KLRI says its translations are "neither
official nor legally effective". The English PIPA on offer there is a 2025-10-02 version against a
Korean current text of 2026-09-11, so the staleness is dated rather than hypothetical.

| `translation_status` | Meaning | Quotable? |
|---|---|---|
| `authoritative` | This *is* authentic text — the EU's 24 language versions, a bilingual statute | **Yes**, and no banner |
| `official-non-authoritative` | Published by the state, disclaiming legal effect — Japan's e-Gov, Korea's KLRI | Yes, bannered |
| `unofficial` | A third party's rendering | Yes, bannered |
| `machine` | Machine output | **No** — `quotable_as_current_law()` is False |

`machine` is unquotable because the failure mode differs in kind: an official translation is wrong at
the margin and its banner says so, while machine output can invert a negation with no signal at all.
It is kept in the corpus as a reading aid for deciding *which* provision to have rendered properly.

### A translation is a separate item, linked to its original

`translation_of` names the `item_id` of the text it renders. It is mandatory whenever
`translation_status` is not `authoritative` — the same rule, for the same reason, as
`validity_note` — and `Manifest.write()` refuses a pointer that does not resolve. A translation is
filed at `authority_tier: commentary`, because a rendering that is not authentic text cannot outrank
the instrument it renders.

### The hazard is provenance, not language

**Singapore is the case this field does not cover.** Its legislation is natively English, so nothing
is translated — and Singapore Statutes Online clause (8) nevertheless declares its own text
**unofficial** and disapplies Interpretation Act s48, so the electronic version is not the one a
court reads. That is an `authority_tier` matter. Recording it as `translation_status` would be a
category error, and would leave the corpus claiming a translation problem where there is none.

Conversely an English-language corpus is not an authoritative one merely by being in English, and a
non-English item is not a translation merely by being foreign: the EU's 24 language versions are all
`authoritative`, and `lang` says nothing about which.
