# Q8 is still empty after nine corpora, Q6 is answerable in seven, and holding all nine at once surfaced six defects

*Cross-regime triage. Corpora read 2026-09-16; the artefact list is [`q4-requester-verification-is-not-universal.md`](q4-requester-verification-is-not-universal.md) §0. Answers, or declines to answer, [`docs/questions.md`](../docs/questions.md) **Q3, Q5, Q6 and Q8** — and records what nine corpora look like when a reader holds them all at once for the first time.*

**Conclusion, in four parts.**

1. **Q8 is still empty, and now the emptiness is a nine-for-nine result rather than a suspicion.** `questions.md` calls enforcement "the weakest layer across every corpus in the programme: no enforcement decisions are archived anywhere yet." Four more corpora have been built since that sentence and it has not moved. Not one of the nine holds a single enforcement decision, penalty order, supervisory-authority action or settlement. What every one of them holds instead is **statutory maxima** — and `id-law-strategy.md` §3.1 named the gap correctly in 2026-07: "CPPA enforcement orders and AG settlements are where 'reasonable verification' acquires meaning."
2. **Q6 is the best-supported of the four**, answerable at legislative tier in seven of nine, and it is where the regimes diverge most — from a defined special category with an in-statute definition (Thailand, Indonesia, the EU) to an absolute non-sharing rule with criminal backing (India) to nothing at all beyond a breach-notification example (Singapore).
3. **Q3 and Q5 are each answerable in about half the set**, and in both cases the split is not regional — it tracks whether the corpus contains an omnibus data-protection statute. Q5 in particular is answerable at length in two corpora and structurally unanswerable in three.
4. **Holding nine corpora at once is itself a method, and it found six defects nothing else would have.** Four are in this repo's own binding documents and tooling. They are in §5, with ticks.

---

## 1. Q8 — enforcement: none in corpus, nine times over

Each row below is a search for enforcement *artefacts*, not for penalty provisions. Every row was run with `lawcite --grep` except Utah, whose corpus `lawcite` cannot read at all (see §5.2).

| Corpus | Enforcement artefacts | What is there instead |
|---|---|---|
| `utah-id-law` | **None.** Statute, agency rules and court rules only; README Known Gap 4 excludes case law outright | Penalty grades — § 76-8-301.5(3) class B misdemeanour, § 53-3-217(3) infraction |
| `eu-data-law` | **None.** The 7 `judicial` items are CJEU judgments reviewing instruments, not DPA actions against controllers | GDPR Art. 83 fining powers; README Known Gap 4: "National supervisory authority decisions and fines. … Absent." |
| `eidas-eudi` | **None**, and structurally: `cut -f4` over all three manifests returns only `delegated`, `legislative`, `commentary` — no `judicial`, no `regulatory-guidance` | Art. 45h-type penalty clauses |
| `ccpa` | **None.** `consent order` → 0, `In the Matter of` → 0; the 4 `enforcement action` hits are the statute authorising one | § 1798.155(a) $2,500/$7,500 administrative fine caps |
| `japan-id` | **None.** 是正命令 → 0, 行政指導 → 0; 個人情報保護委員会 → 126 hits, every one a statutory reference to the body | 勧告 33 hits, 課徴金 2 — powers, not exercises |
| `singapore-id` | **None.** `PDPC` hits are an email address and a website. No `judicial` or `regulatory-guidance` item exists — and Singapore's PDPC *publishes* its decisions, so this is an unharvested layer rather than a non-existent one | — |
| `thailand-id` | **None.** คำวินิจฉัย hits are Constitutional Court rulings carried in unrelated preambles | — |
| `indonesia-id` | **None**, and it is worse than absent: the PDP Law's supervisory institution may not exist yet. Pasal 58(3) says the institution "ditetapkan oleh Presiden" and (5) delegates its constitution to a Peraturan Presiden; none of the four Perpres held concerns it | Pasal 57 administrative fines to 2% of annual revenue; Pasal 67 criminal penalties to 5 years / Rp5bn |
| `aadhaar` | **None.** `order of the Board` → 0, `enforcement action` → 0; `Data Protection Board` → 3, all establishment provisions — and those are `not-yet-applicable` until 2027 | Aadhaar Act ss. 37, 40, 42–44; the DPDP penalty schedule |

**Three things follow, and the third is the useful one.**

The absence is **structural, not a search failure**. Eight of the nine corpora are legislative-plus-delegated by declared scope; only `eu-data-law` and `aadhaar` hold a `judicial` tier at all, and in both cases those are constitutional judgments about instruments rather than enforcement against a party.

**Two of the nine cannot have an enforcement answer yet.** India's Data Protection Board provisions do not commence until 13 May 2027, and Indonesia's supervisory institution is not shown constituted. Saying "no enforcement decisions" about those two would be true and misleading; the honest statement is that the enforcing body does not yet exist in the corpus.

**And Singapore is the cheapest fix in the programme.** The PDPC publishes its enforcement decisions, and they are the one place in this whole set where "reasonable" acquires operational meaning against a named respondent. A Q8 finding is impossible today and would be possible for one jurisdiction after one harvest.

---

## 2. Q6 — biometrics: answerable in seven, and the divergence is real

Counts below are pointers to read, not findings, and are presented as such.

| Corpus | Supports a finding? | Key provision |
|---|---|---|
| `eu-data-law` | **Yes** | GDPR Art. 9 special category; `biometric data` → 24 lines in 9 items |
| `aadhaar` | **Yes, the extreme case** | s. 2(j) defines "core biometric information"; s. 29(1) forbids sharing it "with anyone for any reason whatsoever"; `core biometric information` → 7 lines in 6 items |
| `thailand-id` | **Yes** | PDPA มาตรา ๒๖ makes ข้อมูลชีวภาพ a consent-gated special category and defines it in the article itself |
| `indonesia-id` | **Yes** | UU 27/2022 Pasal 4(2)(b) puts `data biometrik` in the `spesifik` category, with the elucidation supplying a GDPR-shaped definition |
| `ccpa` | **Yes** | § 1798.140 brings "the processing of biometric information for the purpose of uniquely identifying a consumer" into sensitive personal information; `sensitive personal information` → 37 lines in 7 items |
| `eidas-eudi` | **Partly** | Wallet enrolment evidence; the load-bearing text sits in `32024R2977`, which is `amended` and has no consolidated version in the corpus |
| `japan-id` | **Partly, and narrowly** | 生体 → 3 lines in 2 items, every one the same defined term 生体認証符号等 — a device-local unlock alternative to a PIN. 指紋, 顔認証, 虹彩 all 0. Biometrics is not a legal category in this corpus |
| `singapore-id` | **No** | `biometric` → 1 line in 1 item: a breach-notification regulation listing it as an example of an account credential. The PDPA has no special category |
| `utah-id-law` | **Not assessed here** | The existing findings report biometric proofing in specific programmes; no general category was sought |

**The finding available, if someone writes it:** biometric data is a *distinct legal category* in five of the nine, a *device capability* in Japan, and *not a category at all* in Singapore. India is the outlier in both directions at once — the strictest rule in the set, an absolute bar on sharing core biometric information, sitting on the largest biometric identity infrastructure in the set.

**The `ข้อมูลชีวภาพ` result also carries a method lesson.** It was found by *reading* the single `ยืนยันตัวตน` hit in the Thai PDPA while sweeping for Q4, not by searching for biometrics. A sweep for the Thai term `ชีวมาตร` returns 0 — that is the wrong term of art, and a Q6 finding that had started there would have reported Thailand as having no biometric category, which is false.

---

## 3. Q5 — locality and cross-border transfer: two strong, three partial, four out of scope

| Corpus | Supports a finding? | Notes |
|---|---|---|
| `eu-data-law` | **Yes, and it is the organising question** | Reg. 2018/1807 prohibits localisation for non-personal data while GDPR Chapter V restricts transfer of personal data. `questions.md` Q5's warning applies: a finding that reports only one side has not read the other |
| `indonesia-id` | **Yes, and already written** — `pdp-law-cross-border-transfer-is-a-three-step-ladder.md` | Pasal 56's adequacy → binding safeguards → consent ladder, with the divergence from the GDPR named: adequacy is a duty the controller self-discharges, with no list and no naming authority. Pasal 2's extraterritorial reach is wider than GDPR Art. 3(2). `luar wilayah hukum` → 8 lines in 2 items |
| `singapore-id` | **Partly** | `transfer.{0,40}outside Singapore` → 4 lines in 2 items — the PDPA s. 26 machinery is there, the guidance that gives it content is not |
| `aadhaar` | **Partly** | `outside India` → 8 lines in 4 items; the DPDP transfer provision is `not-yet-applicable` |
| `thailand-id` | **Partly, and the repo says so** | README Known Gap 8 records that the PDPA's cross-border chapter is unread even though the Act is held in full. `ต่างประเทศ` → 46 lines in 23 items, uninterrogated |
| `japan-id` | **No** | 国外 → 163 lines in 12 items, but they are 国外転出者 — residents who have moved abroad — not data transfer. Japan's transfer rules are APPI's, and APPI is out of scope |
| `ccpa`, `eidas-eudi`, `utah-id-law` | **No** | Not a live question in any of the three by declared scope |

---

## 4. Q3 — prohibited identification: five clear, and the best material is not in the data-protection statutes

The inverse question, and `questions.md` is right that a Utah-shaped frame will not ask it. Material exists in five corpora at a quotable tier.

- **EU.** GDPR Art. 5(1)(c) data minimisation and Art. 11 (see the Q4 finding). And eIDAS carries a *pseudonym right* that the data-protection instruments do not: relying parties "shall … not refuse the use of pseudonyms, where the identification of the user is not required by Union or national law".
- **India — the strongest single provision in the set.** `AADHAAR-2016-s8A(4)(b)`, `in-force`: an offline verification-seeking entity shall not "collect, use, or store an Aadhaar number or biometric information of any individual for any purpose". A hard bar on a *verifier* retaining the identifier at all. And s. 29(1)'s absolute bar on sharing core biometric information.
- **California.** The rights for which verification is *forbidden* — CCR 11 § 7060(b) — plus the § 7060(d) deletion duty and the § 7023(j)/§ 7024(d) redaction rules.
- **Utah.** `second-sweep.md` already reaches this from the other side, finding affirmative anonymity protections in gamete donation, SafeUT, safe-haven and whistleblower statutes. Title 63A Chapter 20 now adds two more: § 63A-20-302(7)(a)'s "may not require collection of information that is not necessary to verify identity or eligibility", and a statutory right "to be free from surveillance, profiling, tracking, or persistent monitoring of the individual's assertions of digital identity by the state, except as authorized by law".
- **Thailand.** `เท่าที่จำเป็น` ("only as necessary") → 12 lines in 9 items, 3 of them in the PDPA; `นามแฝง` (pseudonym) → 7 lines in 7 items. Material exists and is uninterrogated. `นิรนาม` (anonymous) → 0.

Thin or absent: **Japan** (番号法 is a use-restriction statute, but 収集してはならない → 0 against a control of 収集 → 167; the restrictions are framed as 提供してはならない, 17 lines in 3 items, which is a disclosure bar rather than an identification bar), **Singapore**, and **Indonesia**, whose Pasal 5 transparency right runs the other way.

---

## 5. Six defects, found only by holding all nine at once

This is the part that could not have come from any single repo.

### 5.1 The taxonomy's universality claim is refuted — tick `~4dae`

`taxonomy.md` §1.3 and `questions.md` Q4 both say `requester-verification` "is the one duty family present in every regime in the programme". Four of nine refute it. The evidence is in [`q4-requester-verification-is-not-universal.md`](q4-requester-verification-is-not-universal.md); the two binding documents are deliberately left unedited, per `this.i` @wzkt4y2j.

### 5.2 `utah-id-law` cannot be read by the shared tooling — tick `~5t2g`

Three manifests on the pre-`lawcorpus` schema, no `item_id`, no `authority_tier`, no `validity`, no `translation_status`. `lawcite` refuses. **The repo the method came from is the one repo the method's tooling cannot quote**, and every Utah claim in this programme is therefore unbannered by construction. Any future cross-regime sweep script that assumes `lawcite` works uniformly will silently produce a Utah-shaped hole.

### 5.3 `lawcite --grep` searches without banners on in-force items — tick `~4j4t`

`cite.py` prints an item's banners in grep mode only when `quotable_as_current_law()` is false. So an `in-force` item's translation banner and `quotation_qualifier` never appear in search output. Concretely: all 20 Singapore items carry the SSO clause (8) disclaimer that their text is unofficial and that Interpretation Act s48 does not apply to it, and **not one search hit in this whole comparison displayed it**. `AGENTS.md` says "Any change that lets text out of this package unbannered is a defect"; this is text leaving the package unbannered.

### 5.4 `taxonomy.md` §2 prescribes a migration that has already been applied — tick `~56bo`

It states that `eidas-eudi/corpus-specs/MANIFEST.tsv` "files OpenID4VCI, OpenID4VP and HAIP at `standard`, which `AuthorityTier` has never carried" and gives the command to fix it. The manifest today files all three at `commentary`. A binding document instructing a reader to perform a completed migration is a document the reader learns to distrust. (`eidas-eudi/sources/registry.md` §2a reportedly still carries the same stale description, which is that repo's to fix.)

### 5.5 `utah-id-law`'s findings predate a statute in its own corpus — tick `~4hx6`

Title 63A Chapter 20, State-Endorsed Digital Identity, enacted 2026 Ch. 436, sits in `corpus/utah-code/C63A_2021050520210701.xml.gz`, and no finding cites § 63A-20-303 or § 63A-20-302. Detail in [`q1-no-regime-has-a-general-assurance-baseline.md`](q1-no-regime-has-a-general-assurance-baseline.md) §6.3. The headline survives; the reasoning behind it does not, unchanged.

### 5.6 `asia-id-strategy.md` §8.1 and `thailand-id/findings/04` disagree about what gates a Thai verifier

The strategy table's "what gates a verifier" column reads, for Thailand: *"Royal Decree on DID B.E. 2565 s.9: licensees must be Thai companies."* The repo built to test that concludes the opposite about verifiers specifically — its title is *"Operating a digital-ID service in Thailand needs a Thai company; relying on one appears not to need a licence at all"*, and its second conclusion is that a pure relying party escapes the regime **by exhaustion of the four licensable services in s. 7**, at moderate confidence and by interpretation rather than by an express exemption.

Both statements are true of different actors. s. 9 gates a *licensee*; the strategy table files it under *verifier*. Since the column's whole purpose is to say what stops a foreign party from verifying a citizen credential, the row overstates the obstacle for Thailand — and it is the one row in that table where the repo has since found the gate may not exist. Worth a dated correction in the strategy document, which this finding does not own.

### 5.7 A seventh, which is mine

Three Thai zeros in an early draft of §4 — `เท่าที่จำเป็น`, `ไม่เกินความจำเป็น`, `นิรนาม` — were produced by a shell whose working directory was still `japan-id`, so a Thai pattern was swept over a Japanese corpus. Two of the three were real; `เท่าที่จำเป็น` is 12, not 0. Nothing announced the error. It was caught by running a positive control, which is the §4 rule the programme already has, and it is recorded here because `method.md`'s table of four silent zeros should probably have a fifth row: **a zero produced by the wrong corpus**. Every count in these three findings now names its corpus by absolute path in the command that produced it.

---

## 6. What should be written next, in order of cost

1. **A Q6 finding.** Answerable at legislative tier in five regimes today, with a genuine divergence to report, and no acquisition needed.
2. **A Singapore PDPC enforcement harvest.** The only route to a Q8 finding anywhere in the programme, and the decisions are published.
3. **A Q3 finding**, once Thailand's `เท่าที่จำเป็น` and `นามแฝง` hits are read rather than counted.
4. **A Q5 finding**, which needs Thailand's cross-border chapter read first — it is held and unexamined, so this is reading, not acquisition.
5. **Not Q2 and not Q7 from here.** Q2 is answered well in `utah-id-law` and thinly elsewhere; Q7 is `eidas-eudi`'s question and is being answered on the bridge axis in `interop` rather than the legal one.
