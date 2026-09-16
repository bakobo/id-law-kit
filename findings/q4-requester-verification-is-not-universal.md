# Requester verification is not the connective tissue. It is a European and Californian design, absent from four of the nine corpora

*Cross-regime finding. Corpora read 2026-09-16 from the sibling checkouts named below. Answers [`docs/questions.md`](../docs/questions.md) **Q4** — "what must a party do to verify a rights-requester's identity?" — across nine regimes.*

**Conclusion, in four parts.**

1. **The premise of Q4 fails.** [`docs/taxonomy.md`](../docs/taxonomy.md) §1.3 and [`docs/questions.md`](../docs/questions.md) Q4 both assert that `requester-verification` "is the one duty family present in every regime in the programme". That was true of the five regimes the sentence was written over. Against nine it is false. **The Singapore, Thai, Indonesian and Indian corpora each carry a statutory right of access and impose no duty on the party receiving the request to check who is asking** — and, having no floor, they have no ceiling either.
2. **Where the duty exists, it exists in three distinct shapes, and the difference is the finding.** A *bounded pair* — a floor and a ceiling in the same instrument — in GDPR, EUDPR and the CCPA. A *floor alone* in the Law Enforcement Directive, in Japan's ministerial-ordinance layer, and in Utah's. And *silence* in the four above. No corpus in the programme contains a ceiling without a floor.
3. **The two bounded regimes discharge the bound by opposite mechanisms**, which a comparison that stopped at "both have Art. 11" would miss. GDPR Art. 11(2) resolves the conflict by **switching the rights off** — if the controller demonstrates it cannot identify the data subject, Arts. 15 to 20 do not apply. CCR 11 § 7060(d) resolves it by **compelling deletion** — the business may ask for more, and must delete what it collected as soon as practical after processing the request. One narrows the right; the other narrows the retention.
4. **Where the answer rests below the statute, it rests there entirely.** Japan's requester-verification duty is carried by two 省令 (ministerial ordinances) and by no Act; California's whole verification standard is in CCR Title 11, with the statute supplying only the term of art; Utah's single clear instance is one agency rule. Four of the nine answers would be wrong if read from the legislative layer alone — the failure `method.md` §5 names.

---

## 0. The artefacts, because a negative that names no artefact list is not a finding

Every count and every zero below is over these items and no others. The rule is `thailand-id`'s, adopted at its `this.i` @j4viqege after `credential` was published as 0 over "the five ThaID artefacts" — a set nobody, including its author, could reconstruct — when `client_credentials` in an OAuth grant-types list made it 1.

| Corpus | Manifest | Items | `authority_tier` | `validity` |
|---|---|---:|---|---|
| [`../../utah-id-law/corpus/utah-code`](../../utah-id-law/corpus/utah-code) | `MANIFEST-utah-code.tsv` | 96 | *field does not exist* | *field does not exist* |
| [`../../utah-id-law/corpus/admin-rules`](../../utah-id-law/corpus/admin-rules) | `MANIFEST-admin-rules.tsv` | 2,294 | *field does not exist* | *field does not exist* |
| [`../../utah-id-law/corpus/court-rules`](../../utah-id-law/corpus/court-rules) | `MANIFEST-court-rules.tsv` | 661 | *field does not exist* | *field does not exist* |
| [`../../eu-data-law/corpus`](../../eu-data-law/corpus) | `MANIFEST.tsv` | 18 | 6 legislative, 5 delegated, 7 judicial | 18 in-force |
| [`../../eidas-eudi/corpus`](../../eidas-eudi/corpus) | `MANIFEST.tsv` | 33 | 3 legislative, 30 delegated | 27 in-force, 6 amended |
| [`../../eidas-eudi/corpus-arf`](../../eidas-eudi/corpus-arf) | `MANIFEST.tsv` | 69 | 69 commentary | 69 in-force |
| [`../../eidas-eudi/corpus-specs`](../../eidas-eudi/corpus-specs) | `MANIFEST.tsv` | 3 | 3 commentary | 3 in-force |
| [`../../ccpa/corpus`](../../ccpa/corpus) | `MANIFEST.tsv` | 46 | 46 legislative | 46 in-force |
| [`../../ccpa/corpus-regs`](../../ccpa/corpus-regs) | `MANIFEST.tsv` | 91 | 91 delegated | 61 in-force, 30 amended |
| [`../../japan-id/corpus`](../../japan-id/corpus) | `MANIFEST.tsv` | 40 | 6 legislative, 34 delegated | 38 in-force, 2 repealed |
| [`../../japan-id/corpus-specs`](../../japan-id/corpus-specs) | `MANIFEST.tsv` | 2 | 2 commentary | 2 in-force |
| [`../../singapore-id/corpus`](../../singapore-id/corpus) | `MANIFEST.tsv` | 20 | 4 legislative, 16 delegated | 20 in-force |
| [`../../singapore-id/corpus-specs`](../../singapore-id/corpus-specs) | `MANIFEST.tsv` | 5 | 5 commentary | 5 in-force |
| [`../../thailand-id/corpus`](../../thailand-id/corpus) | `MANIFEST.tsv` | 35 | 35 legislative | 17 in-force, 18 amended |
| [`../../thailand-id/corpus-specs`](../../thailand-id/corpus-specs) | `MANIFEST.tsv` | 14 | 9 commentary, 5 delegated | 11 in-force, 3 repealed |
| [`../../indonesia-id/corpus`](../../indonesia-id/corpus) | `MANIFEST.tsv` | 11 | 6 legislative, 5 delegated | 6 in-force, 5 amended |
| [`../../aadhaar/corpus-acts`](../../aadhaar/corpus-acts) | `MANIFEST.tsv` | 121 | 121 legislative | 92 in-force, 26 not-yet-applicable, 2 read-down, 1 repealed |
| [`../../aadhaar/corpus-delegated`](../../aadhaar/corpus-delegated) | `MANIFEST.tsv` | 10 | 9 delegated, 1 constitutional | 9 in-force, 1 not-yet-applicable |
| [`../../aadhaar/corpus-judgments`](../../aadhaar/corpus-judgments) | `MANIFEST.tsv` | 3 | 3 judicial | 3 in-force |

**The query path** is `lawcite --grep`, which is `lawcorpus.normalise.normalise_query` under `re.IGNORECASE`, so every count here is reproducible with the shipped tool: `/home/daniel/code/bakobo/id-law-kit/.venv/bin/lawcite --grep '<pattern>' --corpus <dir>`. **Case folding is insensitive throughout this file** unless a count says otherwise. Where a query digit had to reach a Thai-digit corpus, the fold is `normalise_query`'s numeral table, not a literal `rg`.

**Three caveats travel with the table.**

**`utah-id-law` cannot be read by `lawcite` at all**, and this is the first document to say so. Its three manifests predate the shared schema and carry `rule/name/agency/program/effective/url/retrieved/bytes/sha256` — no `item_id`, no `authority_tier`, no `validity`, no `translation_status`. The tool refuses:

```
$ cd ../utah-id-law && lawcite --grep 'proof of identity' --corpus corpus
[BK_CITE_UNRESOLVED] No manifest at corpus/MANIFEST.tsv. Run the corpus fetcher for this
repo to create it. Retrying will not change this; change the input instead.
```

So every Utah count below is `zcat | grep` over the three directories — 3,051 files — and carries no validity banner, because there is no validity field to print. The origin repo of this programme is the one repo its tooling cannot quote. Recorded as tick `~5t2g`.

**`singapore-id`'s 20 items all carry the same `quotation_qualifier`:** *"SSO informal consolidation; s48 of the Interpretation Act 1965 does not apply to it, per SSO Terms of Use clause (8). The authoritative text is the printed Revised Edition."* Nothing quoted from Singapore below is the text that binds a court.

**And that qualifier does not print in search output**, which this comparison found by looking for it. `cite.py` emits an item's banners in `--grep` mode only when `quotable_as_current_law()` is false, so an `in-force` item's translation banner and `quotation_qualifier` are both suppressed — every Singapore grep hit prints without the SSO disclaimer, and Thailand's ETDA official English (`official-non-authoritative`, `in-force`) prints without its translation banner. Quote mode prints both correctly. Recorded as tick `~4j4t`; the banners in this file were obtained from the manifests and from `lawcite <item_id>`, not from the search output.

**`indonesia-id` was being re-harvested while this was written.** Its figures and quotes are **as read at 2026-09-16T21:30 UTC, at HEAD `07e2f14`**. The `corpus/` tree did not change during the read, but the repo's prose did, twice.

---

## 1. The bounded pair: GDPR, EUDPR, CCPA

### 1.1 GDPR — the floor and the ceiling in one instrument

Floor, **Art. 12(6)**, `32016R0679`, `legislative`, `in-force`. Command: `lawcite --grep 'reasonable doubts concerning the identity' --corpus corpus` in `../eu-data-law`, 4 lines in 3 items:

> Without prejudice to Article 11, where the controller has reasonable doubts concerning the identity of the natural person making the request referred to in Articles 15 to 21, the controller may request the provision of additional information necessary to confirm the identity of the data subject.

The provision is permissive, not mandatory — *may* request — and the trigger is the controller's own doubt. It opens by subordinating itself to the ceiling.

Ceiling, **Art. 11**, same item, same tier and validity. Command: `lawcite --grep 'shall not be obliged to maintain, acquire or process' --corpus corpus`, 2 lines in 2 items:

> **Article 11 — Processing which does not require identification**
>
> 1. If the purposes for which a controller processes personal data do not or do no longer require the identification of a data subject by the controller, the controller shall not be obliged to maintain, acquire or process additional information in order to identify the data subject for the sole purpose of complying with this Regulation.
>
> 2. Where, in cases referred to in paragraph 1 of this Article, the controller is able to demonstrate that it is not in a position to identify the data subject, the controller shall inform the data subject accordingly, if possible. In such cases, Articles 15 to 20 shall not apply except where the data subject, for the purpose of exercising his or her rights under those articles, provides additional information enabling his or her identification.

**Paragraph 2 is the half that gets dropped, and it is the operative half.** A ceiling on its own would leave the requester with a right and the controller with no obligation to exercise it; Art. 11(2) answers that by suspending Arts. 15 to 20 outright, and hands the key back to the data subject, who may re-enable them by volunteering identifying information. The right is not defeated — it is made contingent on the requester's own choice to be identifiable.

**One authority-tier caution.** The phrasing most often quoted for the ceiling — "should not be obliged to acquire additional information in order to identify the data subject" — is **Recital 57**, not the article, and a recital is weaker than an article on the ladder in `taxonomy.md` §2. Recital 64, likewise, carries "the controller should use all reasonable measures to verify the identity of a data subject who requests access" — which reads like a *duty* to verify and would, if quoted as the rule, invert Art. 12(6)'s permissive construction. Cite the articles.

### 1.2 EUDPR carries both; the Law Enforcement Directive carries only the floor

`32018R1725` (EUDPR) reproduces the construction twice — **Art. 14** for the general rights and **Art. 78** for the operational-data rights — and its ceiling is **Art. 12**, not Art. 11. Article numbers confirmed by walking back from each hit line to its nearest `Article N` header in the stored text, because the numbering does not match the GDPR's and a comparison that assumed it did would cite the wrong provision.

`32016L0680` (LED) carries the floor at **Art. 12** in near-identical words — and **no ceiling at all**. Interrogated: over the stored LED text, `not be obliged` → 0, `identification of a data subject` → 0, `sole purpose of complying` → 0, against `acquire` → 3, every one of which is the definition of genetic data ("inherited or acquired genetic characteristics") or a DPO-designation recital. The phrase family that carries Art. 11 in two instruments is absent from the third.

**This is the sharpest result inside the EU stack itself.** The instrument governing police and criminal-justice processing gives the controller the power to demand more identification of a requester and does not give the requester the countervailing protection that the general regulation does.

### 1.3 CCPA — the same shape, built entirely out of delegated legislation

The statute supplies the term of art and almost nothing else. `verify the identity of the consumer` → **0** in `../ccpa/corpus`; `verifiable consumer request` → **21 lines in 8 items** (`CIV-1798.105, .106, .110, .115, .130, .140, .145, .185`). This is the `method.md` §3 case: until the term of art is found, a zero says nothing.

The definition, `CIV-1798.140`, § 1798.140(ak), `legislative`, `in-force`, makes verification a **precondition of the duty** rather than a power:

> A business is not obligated to provide information to the consumer pursuant to Sections 1798.110 and 1798.115, to delete personal information pursuant to Section 1798.105, or to correct inaccurate personal information pursuant to Section 1798.106, if the business cannot verify … that the consumer making the request is the consumer about whom the business has collected information …

The standard itself is in the regulations. `CCR-11-7062`, `delegated`, `in-force`:

> (b) A business's compliance with a request to know categories of personal information requires that the business verify the identity of the consumer making the request to a reasonable degree of certainty. A reasonable degree of certainty may include matching at least two data points provided by the consumer with data points maintained by the business that it has determined to be reliable for the purpose of verifying the consumer.
>
> (c) A business's compliance with a request to know specific pieces of personal information, or a request to access ADMT, requires that the business verify the identity of the consumer making the request to a reasonably high degree of certainty. A reasonably high degree of certainty may include matching at least three pieces of personal information … together with a signed declaration under penalty of perjury …

**California is the only regime in the programme that grades assurance by which right is being exercised** — two data points to know categories, three plus a perjury declaration to know specific pieces. Everywhere else the requester-verification duty, where it exists at all, is one standard for all rights.

The ceiling, `CCR-11-7060(d)`, `delegated`, `in-force`:

> (d) A business shall generally avoid requesting additional information from the consumer for purposes of verification. If, however, the business cannot verify the identity of the consumer from the information already maintained by the business, the business may request additional information from the consumer, which shall only be used for the purposes of verifying the identity of the consumer seeking to exercise their rights under the CCPA, security, or fraud- prevention. The business shall delete any new personal information collected for the purposes of verification as soon as practical after processing the consumer's request, except as required to comply with section 7101.

Compared against `CCR-11-7060@2023`, the superseded 2023 wording held in the same corpus, subsection (d) is word-for-word identical; only its subsection letter moved. The ceiling predates and survived the 2025 rulemaking. (`lawcite` prints the superseded item under an `[AMENDED since enactment: quote the consolidated version, not this one …]` banner, which is how the two were told apart.)

California adds two things the GDPR has not got.

**A set of rights for which verification is forbidden**, `CCR-11-7060(b)`:

> (b) A business shall not require a consumer to verify their identity to make a request to opt-out of sale/sharing, or to make a request to limit, or to make a request to opt-out of ADMT. A business may ask the consumer for information necessary to complete the request; however, it shall not be burdensome on the consumer. For example, a business may ask the consumer for their name, but it shall not require the consumer to take a picture of themselves with their driver's license.

**And a cost rule**, `CCR-11-7060(e)` — quoted as stored, including an amendment-markup artefact where the struck word survives the extraction:

> (e) A business shall not require the consumer or the consumer's authorized agent to pay a fee for the verification of their request to delete, request to correct, or request to know. For example, a business may must not require a consumer to provide a notarized affidavit to verify their identity unless the business pays for or compensates the consumer for the cost of notarization.

Hold that sentence for §3.1. Utah, on the one occasion it imposes a requester-verification duty, requires exactly the notarized affidavit that California forbids a business to require for free.

At statute level the same instinct appears once, `CIV-1798.130(a)(2)(A)`, `legislative`, `in-force`: the business "may require authentication of the consumer that is reasonable in light of the nature of the personal information requested, but shall not require the consumer to create an account with the business in order to make a verifiable consumer request".

### 1.4 eIDAS and the EUDI wallet: not applicable here, and the reason is worth recording

`../eidas-eudi` is a regime about *providing* identification, not about *exercising rights against a controller*, so Q4 does not live there — the wallet's data-subject rights are the GDPR's. The sweep is reported anyway because two of its three hits are instructive.

Over `corpus` (33 items): `reasonable doubts` → 1, `making the request` → 2, `data subject.{0,40}request` → 0, against a control of `identification` → 766 lines in 33 items.

**The single `reasonable doubts` hit is a false positive**, and exactly the kind `method.md` §3 warns that a count will hide. In `32024R2981` it is a risk register: *"loss of trust, stemming from the user's reasonable doubts, and loss of ecosystem"*. Nothing to do with identity.

**The `making the request` hits are a different duty family wearing the same words.** `32025R1569`, `delegated`, `in-force`: "(a) identification of the entity making the request; (b) where applicable, a reference to Union or national law … under which the entity making the request is considered to be a primary source of information". The party being identified is a *relying party querying an authentic source*, not a natural person exercising a right.

Over `corpus-arf` (69 items, all `commentary`) the phrase does appear in its proper sense — because **the ARF quotes GDPR Art. 12(6) verbatim** inside a discussion topic on data deletion. A finding that cited that hit would be citing a specification's reproduction of a regulation. Cite `32016R0679`.

---

## 2. Silence: Singapore, Thailand, Indonesia, India

All four have a statutory right of access. None imposes on the recipient a duty to verify who is asking. The four silences are not equivalent, and the difference is in how much of the answer's layer is missing.

### 2.1 Singapore — the strongest of the four zeros, because the delegated layer is held

PDPA 2012 s. 21(1), `PDPA2012`, `legislative`, `in-force`:

> 21.—(1) Subject to subsections (2), (3) and (4), on request of an individual, an organisation must, as soon as reasonably possible, provide the individual with — (a) personal data about the individual that is in the possession or under the control of the organisation …

Over `../singapore-id/corpus` (20 items): `reasonable.{0,20}doubt` → **0**, `evidence of identity` → **0**, `verify the identity of the` → **0**, `proof of identity` → **0**, `requester`/`requestor` → **0**/**0**, `access request` → **0**. Controls on the same 20 items: `identity` → 136 lines in 7 items, `verif` → 32 lines in 5 items. The tool works; the concept is not there.

The closest provision is in the delegated layer and is **collection, not verification** — `PDPA2012-S63-2021` (Personal Data Protection Regulations 2021), reg. 3(1), `delegated`, `in-force`:

> 3.—(1) A request to an organisation must be made in writing and must include sufficient detail to enable the organisation, with a reasonable effort, to identify — (a) the applicant making the request; …

The organisation must be *able to identify* the applicant from what the applicant supplies. It is not obliged to test the claim, and nothing bounds what it may ask for. This is `taxonomy.md` §1.1's fifth distinction — collection is not proofing — landing on the requester-verification axis.

**This zero is strong because the layer where the duty would live is in the corpus and does not contain it.** The layer not searched is `regulatory-guidance`: the PDPC's advisory guidelines, which `singapore-id`'s README lists as absent and which are entirely unrepresented in the corpus (0 items at that tier). State it as *the Singapore corpus does not name this duty*, not as *Singapore law has none*.

### 2.2 Thailand — a weaker zero, and the statute says where the answer went

PDPA B.E. 2562, มาตรา ๓๐, `th-11029`, `legislative`, `in-force`, `authoritative`, `lang: tha`:

> มาตรา ๓๐ เจ้าของข้อมูลส่วนบุคคลมีสิทธิขอเข้าถึงและขอรับสำเนาข้อมูลส่วนบุคคลที่เกี่ยวกับตนซึ่งอยู่ในความรับผิดชอบของผู้ควบคุมข้อมูลส่วนบุคคล … ให้ผู้ควบคุมข้อมูลส่วนบุคคลดำเนินการตามคำขอโดยไม่ชักช้า แต่ต้องไม่เกินสามสิบวันนับแต่วันที่ได้รับคำขอ **คณะกรรมการอาจกำหนดหลักเกณฑ์เกี่ยวกับการเข้าถึงและการขอรับสำเนาตามวรรคหนึ่ง** รวมทั้งการขยายระยะเวลาตามวรรคสี่หรือหลักเกณฑ์อื่นตามความเหมาะสมก็ได้

*My gloss, not corpus text:* the data subject has the right to request access to and a copy of personal data about themselves held by the controller; the controller must act without delay and within thirty days of receiving the request; **the Committee may prescribe rules concerning access and the obtaining of copies under paragraph one**, including extensions and other appropriate criteria.

The article says nothing about checking who is asking — and in its last paragraph it **expressly delegates the access-request rules to the PDPC**.

Sweep over `../thailand-id/corpus` (35 items), restricted counts over `th-11029`: `พิสูจน์ตัวตน` → 0, `การพิสูจน์และยืนยันตัวตน` → 0, `ตรวจสอบตัวตน` → 0, `ยืนยันตัวตน` → **1**. Control: `เจ้าของข้อมูลส่วนบุคคล` → 34.

**The 1 was read, and it is not a Q4 hit.** It falls in มาตรา ๒๖, inside the definition of ข้อมูลชีวภาพ — biometric data — *"ทำให้สามารถยืนยันตัวตนของบุคคลนั้นที่ไม่เหมือนกับบุคคลอื่นได้ เช่น ข้อมูลภาพจำลองใบหน้า ข้อมูลจำลองม่านตา หรือข้อมูลจำลองลายนิ้วมือ"* (my gloss: enabling that person's identity to be confirmed as distinct from others, such as facial-image, iris or fingerprint templates). It is a Q6 provision. Counting it as a Q4 hit would have produced the false positive; reading it produced a Q6 answer instead.

**The layer not searched is not merely unharvested — it is unreachable by construction.** `thailand-id`'s README Known Gap 10 records that the `law_list` API behind the corpus carries 1,107 พระราชบัญญัติ and **zero** พระราชกฤษฎีกา, so the PDPA's กฎกระทรวง and the PDPC's own ประกาศ have no mechanical route into this corpus at all. Combine that with มาตรา ๓๐'s closing delegation and the honest statement is narrow: **the Thai statute does not impose a requester-verification duty and expressly empowers the Committee to write the access rules; whether it has done so is not answerable from this corpus.**

The Royal Decree on Digital ID and มธอ. ๑๑-๒๕๖๖ do not fill the gap. They regulate identity-proofing and authentication *services* — a licensing perimeter, `compelled-identification` in the §1.2 direction vocabulary, not `requester-verification`.

### 2.3 Indonesia — GDPR-descended, and this is where it diverges from the parent

UU 27/2022 is modelled on the GDPR closely enough that Chapter V's transfer ladder is recognisable. **The requester-verification machinery did not come across.** The entire statutory text on how a rights request is made is Pasal 14, `UU-27-2022`, `legislative`, `in-force`:

> Pelaksanaan hak Subjek Data Pribadi sebagaimana dimaksud dalam Pasal 6 sampai dengan Pasal 11 diajukan melalui permohonan tercatat yang disampaikan secara elektronik atau nonelektronik kepada Pengendali Data Pribadi.

*My gloss:* the exercise of the data subject's rights under Pasal 6 to 11 is submitted by a recorded application, electronic or non-electronic, to the personal data controller.

A channel, and nothing else. No doubt trigger, no additional-information power, no ceiling, no time limit tied to verification.

Sweeps over `../indonesia-id/corpus` (11 items), as read at 2026-09-16T21:30 UTC, HEAD `07e2f14`. Zero for all of: `memastikan.{0,30}identitas`, `keraguan`, `bukti identitas`, `tanpa perlu`, `tidak wajib`, `tidak diwajibkan`, `tidak diharuskan`, `data tambahan`, `informasi tambahan`, `minimalisasi`, `mengonfirmasi`, `otentikasi`. Controls on `UU-27-2022`: `Subjek Data Pribadi` → 61, `Pengendali Data Pribadi` → 79, `permintaan` → 12.

**Two non-zeros, both read, both pointing the wrong way.** `verifikasi` → 1 in `UU-27-2022`, at Pasal 29(2), which obliges the controller to verify **the data**, not the requester — a GDPR Art. 5(1)(d) accuracy duty. `identitas` → 1, at Pasal 5, which gives the data subject the right to be told the identity of *whoever is asking for their data* — the mirror image of Q4, running from the controller to the subject.

**And the competing design is informative.** The drafting attention in Chapter IV went into Pasal 15, an exemption list carving out defence, law enforcement, public administration, financial supervision and statistics — scope-carving, not requester authentication. `method.md` §3's rule that a legislature's alternative choice is evidence applies: Indonesia had the GDPR in front of it and spent its rights-chapter effort elsewhere.

**Layer not searched:** UU 27/2022's implementing PP. `indonesia-id`'s README Known Gap 3 records that no implementing regulation was located, and instructs that this be treated as *not found* rather than *does not exist* — 11 of 6,976 national instruments are held, against a relevance-matching search endpoint. Neither Pasal 14 nor the rights chapter contains its own delegation clause, unlike Pasal 10(2), 12(2) and 13(3), so there is no lower layer earmarked for this question — but the general implementing regulation could still carry it.

### 2.4 India — absent, and not yet in force either way

DPDP Act 2023 ss. 11–15 (access, correction and erasure, grievance redressal, nomination, duties of the Data Principal) contain no power for a Data Fiduciary to demand identification of a requester. Over `../aadhaar/corpus-acts` (121 items): `reasonable doubt` → **0**, `identity of the Data Principal` → **0**, `not be obliged` → **0**. Controls: `Data Principal` → 60 lines in 17 items, `verif` → 33 lines in 12 items.

The nearest neighbour runs the other way — `DPDP-2023-s15`, s. 15(e), `legislative`, **`not-yet-applicable`**:

> (e) to furnish only such information as is verifiably authentic, while exercising the right to correction or erasure under the provisions of this Act or the rules made thereunder.

A duty of candour on the *requester*. The fiduciary gets no corresponding power.

**Two qualifications, both material.** All 26 of the DPDP items covering ss. 3–9, 10–17, 27–34, 36, 37 and 44 are `not-yet-applicable` — G.S.R. 843(E) of 13 November 2025 appoints **13 May 2027** for the rights sections — so even a positive hit would have carried that banner. And the DPDP Rules 2025 (`DPDP-RULES-2025`, `delegated`, `not-yet-applicable`) do have identity-checking rules, at rules 10–11, but they run the opposite way from Art. 11: they *require* a fiduciary to obtain and verify a parent's or guardian's identity before processing a child's data. A ceiling and a mandatory acquisition are not the same instrument pointed in different directions; they are different rules.

---

## 3. The floor without a ceiling: Utah and Japan

### 3.1 Utah — one agency rule, and it demands more than the EU floor allows

Utah has no general requester-verification duty. GRAMA, the state records-access statute, is pure collection — § 63G-2-204(1) requires a written request containing "the person's: name; mailing address; email address, if the person has an email address and is willing to accept communications by email relating to the person's records request; and daytime telephone number; and a description of the record requested that identifies the record with reasonable specificity", and imposes no verification duty on the governmental entity.

The duty appears once, clearly, in one administrative rule: **R156-37f-301**, the Controlled Substance Database rule of the Division of Professional Licensing.

> (3) … (c) The Division shall require a requester to verify the requester's identity.

And for the genuine subject-access case — an individual obtaining their own record *and an accounting of everyone who has looked at it*, which is a stronger right than the CCPA's:

> (7) … (b) The individual may request the information by submitting an original signed and notarized request as furnished by the Division that includes: (i) the individual's: (A) full name, including aliases; (B) complete home address; (C) telephone number; and (D) date of birth; (ii) a clearly legible copy of government-issued picture identification confirming the individual's identity; and (iii) requested date range for the information.

**A notarized request plus a government photo ID.** This is the strictest requester-verification standard anywhere in the nine corpora — and it is the exact demand CCR 11 § 7060(e) forbids a California business to make unless it pays for the notarization. The comparison is worth stating plainly: the same act, subject access, is bounded above in California and bounded below in Utah, and neither regime knows the other's constraint exists.

Subsection (7)(c) also handles a third party requesting on the individual's behalf — power of attorney, parent, court-appointed guardian, or a notarized release — which is Q7 territory reached from the Q4 side.

A second, weaker instance sits in the court rules: UCJA-4-202.04(1)(B) and UCJA-4-202.05(1) require a person requesting a **non-public** court record to present identification, while a request for a **public** record under the same rule requires none. The trigger is the sensitivity of the record, not the fact of a request.

Counts over the 3,051 Utah files, by `zcat | grep -iE` because `lawcite` cannot read this corpus: `verif` 3,548; `requester` 326; `request.{0,40}identif` 108; `reasonable doubt` 64, of which one concerns identity; `establish.{0,20}identity` 12; `proof of identity` 6; `identity of the (requester|person making)` 1. No pattern returned zero, so no positive control was needed. **No ceiling-shaped provision was found** — nothing bounding what a Utah entity may demand of a requester, nothing requiring verification material to be deleted. Not exhaustively ruled out: this is a keyword sweep over a corpus the repo's own README calls "samples, not an exhaustive reading".

### 3.2 Japan — the duty is real, and it is not where you would look for it

**番号法 §16 is not the answer, and mistaking it for the answer is the trap.** `425AC0000000027`, `legislative`, `in-force`:

> (本人確認の措置)
> 第十六条 個人番号利用事務等実施者は、第十四条第一項の規定により本人から個人番号の提供を受けるときは、次の各号のいずれかに掲げる措置をとらなければならない。

*My gloss:* a person executing My-Number-related affairs must, when receiving a My Number **from the person themselves** under §14(1), take one of the listed measures — presentation of the individual number card, confirmation of the phone-borne card-substitute record, or a measure prescribed by Cabinet Order.

The trigger is §14(1), which is the *collector* asking the individual **for** their number. The duty is to verify the person **supplying** identification, not the person **demanding** something. It is `compelled-identification` in the §1.2 vocabulary, and it is the mirror of Q4, not an instance of it. The Cabinet Order fleshing out the third route, `426CO0000000155` §12, `delegated`, `in-force`, asks for a certified copy of the resident record bearing name, date of birth, sex, address and the number — documentary proofing, one delegation further out.

The genuine Q4 duty is in the 省令 layer of two *other* statutes.

`415M60000008120` (公的個人認証法施行規則) §75, `delegated`, `in-force`, implementing 公的個人認証法 §58(1) — a person's request for disclosure of their own certification-business records — requires the requester to present a passport, residence card, individual number card, driver's licence or equivalent photo document *"開示請求者が当該開示請求者本人であることを確認するため機構又は住所地市町村長が適当と認める書類"* — my gloss: a document the Organisation or the municipal head considers appropriate for confirming that the requester is the requester themselves. The same article extends the machinery to agents (代理人) and to correction requesters (訂正等請求者).

`411M50000008035` (住基法施行規則) §4, `delegated`, `in-force`, does the same for a request for a copy of one's own resident record, with the test written explicitly as the recipient's satisfaction: *"当該請求者が本人であることを確認するため市町村長が適当と認めるものとする"*.

**Two consequences.** Japan's answer sits entirely in delegated legislation; the Acts state the right and the ordinances state the check. And **no ceiling exists** — nothing in either ordinance bounds what may be demanded or requires the identification copy to be destroyed.

**The layer not searched is named and is decisive.** 個人情報保護法 (APPI), Japan's general data-protection statute, **is not in this corpus** — `japan-id`'s README Known Gap 4 says so by name, and the corpus scope is the 番号法 / 住民基本台帳法 / 公的個人認証法 / J-LIS families. APPI carries Japan's general disclosure-request regime. So Japan's entry in the table below is the answer *for the identity-number statutes*, and the general answer is genuinely outside the harvested layer rather than merely unsearched.

---

## 4. The comparison

| Regime | Floor — must the recipient check who is asking? | Ceiling — is the demand bounded above? | Tier the answer rests on |
|---|---|---|---|
| **GDPR** `32016R0679` | Yes, permissive: Art. 12(6) | **Yes** — Art. 11(1), with Art. 11(2) suspending Arts. 15–20 | legislative |
| **EUDPR** `32018R1725` | Yes: Arts. 14, 78 | **Yes** — Art. 12 | legislative |
| **LED** `32016L0680` | Yes: Art. 12 | **No** — phrase family absent | legislative |
| **eIDAS / EUDI** | Not applicable — not a rights regime | — | — |
| **CCPA** | Yes, as a precondition: § 1798.140(ak); graded by right, CCR 7062 | **Yes** — CCR 7060(d) delete-after-use, 7060(b) no verification for opt-outs, 7060(e) fee rule, § 1798.130(a)(2)(A) no forced account | legislative + **delegated** |
| **Utah** | Only in one agency rule: R156-37f-301(3)(c), (7)(b); and for non-public court records | **No** — and the one instance demands notarization plus photo ID | **delegated** + court rule |
| **Japan** | Yes, but not in 番号法: 公的個人認証法施行規則 §75, 住基法施行規則 §4 | **No** | **delegated** |
| **Singapore** | **No** — reg. 3(1) is collection, not verification | No floor, so no ceiling | — |
| **Thailand** | **No** in the statute; มาตรา ๓๐ delegates the access rules to the Committee | No floor, so no ceiling | — |
| **Indonesia** | **No** — Pasal 14 is a bare channel clause | No floor, so no ceiling | — |
| **India** | **No** in DPDP ss. 11–15, and those sections are `not-yet-applicable` until 13 May 2027 | No floor, so no ceiling | — |

Four observations the table makes available.

**The duty tracks the omnibus-data-protection lineage, not the presence of a rights regime.** All nine regimes give somebody a right to reach their own data. Only the GDPR family and California tell the recipient what to do about identity. Singapore's PDPA (2012), Thailand's (2019), Indonesia's (2022) and India's DPDP (2023) are all later than the GDPR and three of them are visibly shaped by it — and none of them imported Art. 12(6) or Art. 11.

**The ceiling is rarer than the floor and never appears alone.** Three regimes bound the demand; six do not. No regime in the programme protects a requester from over-collection without first obliging the recipient to verify.

**Delegated legislation carries the answer in four of the five regimes that have one.** Reading California, Utah or Japan from the statute alone yields "no duty", which is wrong in all three.

**The four silences differ in strength, and a comparison that flattens them is worthless.** Singapore's is the strongest — the regulations that would carry the duty are in the corpus and do not. Indonesia's is next — the statute is complete and silent, and the implementing regulation was searched for and not found. India's is a statute not yet in force. Thailand's is the weakest — the statute expressly hands the question to a notification layer that this corpus has no mechanical route to at all.

---

## 5. What this finding does not establish

- **Nothing about the four silent regimes' non-statutory layers.** PDPC advisory guidelines (Singapore), PDPC notifications (Thailand), the PDP implementing regulation (Indonesia) and the DPDP Rules as they will read in 2027 (India) are all unread here, and any of them could supply the duty.
- **Nothing about APPI**, which is Japan's general data-protection statute and is outside `japan-id`'s scope by decision, not by oversight.
- **Nothing about enforcement.** Whether a "reasonable degree of certainty" or "reasonable doubts" means anything in practice is Q8, and no corpus in the programme holds a single enforcement decision. See [`q3-q5-q6-q8-what-nine-corpora-can-support.md`](q3-q5-q6-q8-what-nine-corpora-can-support.md).
- **Nothing about national transpositions** of the GDPR or LED, which are absent from `eu-data-law` by declared scope and are where a Member State could add a ceiling the Directive omits.
- **Nothing that turns on a term of art in translation.** Every non-English quotation above is authentic text; every English rendering of one is marked as my gloss and is not evidence.
