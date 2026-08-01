# The question spine

Eight questions, answered per regime in that regime's repo, then compared here. The point is that
findings come out **comparable** rather than as five bespoke essays that cannot be laid side by
side.

Not every question is live in every regime. **A documented "not applicable here, because…" is
itself a comparative result** — arguably the most interesting kind, since it says something about
what a legal system thinks identity is *for*.

Each answer must satisfy [`method.md`](method.md): quote-or-drop, corpus named, layers not searched
named, zeros interrogated.

---

## Q1. Is there a general identity-assurance baseline?

*Or is assurance set interaction by interaction?*

This is the headline question and the one that compares most sharply. Utah's answer — **no general
baseline; requirements range from nothing, through attestation, to documentary proof, set
interaction by interaction** — is a finding about the shape of a legal system, not a detail.

Ask of each regime: is there a provision of general application, or only a pile of specific ones? If
someone claims a universal, they owe the general provision (see quantifier asymmetry in
`method.md` §7).

## Q2. When is identity *proofing* compelled, versus assertion or attestation?

Uses the four-way split in [`taxonomy.md`](taxonomy.md) §1.1. Two things to look for beyond the
obvious:

- **The competing design.** Where a legislature reached for attestation under penalty of perjury
  instead of proofing, that choice is evidence.
- **Collection versus verification.** A rule requiring a form to *collect* a date of birth imposes
  no duty on anyone to *check* it.

## Q3. When is identifying a person prohibited or discouraged?

The inverse question, and the one a Utah-shaped frame will not ask. Data minimisation, anonymity
protections, prohibitions on retaining identifiers, restrictions on identifying by default.

GDPR Art. 11 is the sharp case: a controller is **not required to acquire** identifying data merely
to comply with the regulation. `utah-id-law/findings/second-sweep.md` reaches for the same question
from the other side — where does Utah law *protect* anonymity?

## Q4. What must a party do to verify a rights-requester's identity?

The connective tissue ([`taxonomy.md`](taxonomy.md) §1.3) — the one duty family present in every
regime, running in the direction the Utah framing does not anticipate: the duty falls on the
*controller*, and it is bounded above as well as below.

Confirmed present in GDPR Art. 12(6), LED Art. 12, EUDPR Arts. 14 and 78, and the CCPA's
"verifiable consumer request" (§§ 1798.105, .106, .110, .115, .130, .140, .145, .185). **Start
comparative work here** — the corpora already answer it in four regimes.

Every citation in that sentence was checked against the corpus before it was written, which is not
a flourish: the first draft said "LED Art. 15" and "EUDPR Arts. 80/82" from recall, and both were
wrong.

## Q5. What constrains where identity data may sit, and who may reach it?

Locality, cross-border transfer, and government access. Barely live in Utah; the organising question
of `eu-data-law`.

Note the two-sidedness: Regulation 2018/1807 *prohibits* localisation for non-personal data while
GDPR Chapter V *restricts* transfer of personal data. A regime can push both ways at once, and a
finding that reports only one has not read the other.

## Q6. How are biometrics treated specifically?

Usually a distinct legal category rather than a species of personal data, and the place where
regimes diverge most. Aadhaar is the extreme case: a national biometric identity infrastructure
whose enabling statute has been partly struck down.

## Q7. What are the rules for delegated and derived credentials?

Wallets, authorised agents, guardianship, agents acting for a principal, attestations derived from
other attestations. The forward-looking question, and the one `eidas-eudi` exists to answer.

Bakobo-adjacent, so watch the terminology rule: consult the glossary before using a Bakobo term of
art, and do not let a general word masquerade as a formal one.

## Q8. What is the enforcement posture?

Who enforces, what penalties, and — separately — **what has actually been enforced**. This is where
"reasonable" acquires operational meaning, and it is the weakest layer across every corpus in the
programme: no enforcement decisions are archived anywhere yet. Say so rather than inferring the
answer from the statutory maximum.

---

## Answering these well

**State the corpus, not the world.** "The GDPR corpus contains no provision requiring X" is
checkable. "EU law does not require X" is a claim about 27 national transpositions, ~80 EDPB
guidelines, and a case law we hold only in part.

**Name the layer you did not search.** Every regime repo's README has a Known Gaps section for
exactly this. A finding that does not reference it is incomplete.

**Say which authority tier the answer rests on.** An answer from a recital is weaker than one from
an article; one from a specification is weaker than one from an implementing act.

**Cross-regime findings live in this repo**, under `findings/`, citing sibling checkouts by relative
path (`../eu-data-law/corpus/...`) per the house convention. Single-regime findings live in that
regime's repo.

---

## Current coverage

| | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 |
|---|---|---|---|---|---|---|---|---|
| `utah-id-law` | ✅ | ✅ | ◐ | — | — | — | — | — |
| `eu-data-law` | — | — | — | ◐ | ◐ | — | — | — |
| `eidas-eudi` | — | — | — | — | — | — | ◐ | — |
| `ccpa` | — | — | — | ◐ | — | — | — | — |
| `aadhaar` | — | — | — | — | — | — | — | — |

✅ answered · ◐ corpus supports it, finding not yet written · — not started

Only `utah-id-law` has written findings. The other four have corpora and no analysis, which is the
intended order: **harvest first, so the expensive online research is not repeated when the analysis
happens.** Q4 is the cheapest first comparative finding, because the corpora already contain the
answer in four regimes.
