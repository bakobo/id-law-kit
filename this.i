# id-law-kit — Intent Tree (this.i)

Shared method and tooling for the identity-law corpus programme = goal:
  id: s62c4j
  why: >
    One place to hold the research method, the corpus/manifest schema, and the fetch-and-cite
    tooling that the per-jurisdiction repos (eu-data-law, eidas-eudi, ccpa, aadhaar, and
    retroactively utah-id-law) all need. Rejected duplicating the tooling per repo, which is what
    utah-id-law does today: the adversarial review of 2026-07-29 found two real defects in its
    sweep patterns, and with four more repos that becomes four more places to fix the same bug.
    Rejected folding this into bakobo/dev, which is cross-cutting *engineering* standards — a legal
    research method and a corpus toolkit would dilute it. The driving constraint is concrete: the
    EUR-Lex fetcher is needed by eu-data-law and eidas-eudi on day one, so the second consumer
    exists before the first line is written. Tradeoff accepted: a package boundary and an extra
    repo to clone, imposed before four consumers have proven the abstraction is right.
  children:
    One repo per regime, not a monorepo = decision:
      id: nljwjw
      why: >
        Chose five sibling repos over a single monorepo. utah-id-law is 34 MB of working tree for
        one US state's three layers; the EU corpus (GDPR consolidated + transposition + EDPB +
        CJEU) is plausibly an order of magnitude larger, and a monorepo makes a reader clone India
        to look at California. The acquisition mechanics share nothing at the fetch layer — EUR-Lex
        content negotiation, a California pubinfo zip, a DSpace handle browse, and a GitHub release
        tag have no common code. Decisively, the redistribution posture differs per corpus and
        utah-id-law's reasoning does not transfer: it rests on "edicts of government, no
        copyright", which is US doctrine, while EU material is © European Union reusable under
        Decision 2011/833/EU with attribution, and Indian government works sit under GODL-India.
        Each repo needs its own LICENSE/NOTICE reasoning, which is cleaner per-repo than as a
        matrix in one README. Tradeoff: cross-jurisdiction findings must cite across sibling
        checkouts by relative path (the ../sedi convention already used by utah-id-law) rather than
        by in-repo path, and five repos must be kept in step by hand.

    The manifest records validity and authority tier, not just provenance = decision:
      id: oxu7ik
      why: >
        utah-id-law's manifest records URL, retrieval date, bytes, SHA-256, and a version stamp —
        enough to prove *what text we fetched and when*, which is all Utah needs because its
        statutes are good law until amended. That is not enough here. Aadhaar Act §57 was struck
        down by the Supreme Court in 2018, yet the Act PDF published on uidai.gov.in still carries
        the text; quote-or-drop over that PDF would *manufacture* a false claim, which is precisely
        the failure the rule exists to prevent. So every corpus item carries `validity`
        (in-force | amended | struck-down | read-down | not-yet-applicable | repealed, with a
        pointer to the instrument that did it) and `authority_tier` (making the trust order that
        sources/registry.md states in prose machine-readable). Rejected leaving this to a prose
        caveat in each README, because a caveat is a thing an agent must remember and this must be
        structural. Tradeoff: `validity` cannot be derived mechanically for most items, so it is
        hand-curated and will lag; a wrong `validity` is more dangerous than an absent one, which
        is why it is a required field with no default rather than an optional annotation.
      children:
        `standard` is refused as a tier: an incorporated specification is already delegated = decision:
          id: 3zljqayt
          why: >
            `eidas-eudi/corpus-specs` files OpenID4VCI, OpenID4VP and HAIP at
            `authority_tier: standard`, which `AuthorityTier` does not carry, so that manifest has
            been unreadable since the enum shipped and one of the two has to give. The case for
            admitting the token is real: an open technical specification that an implementing act
            adopts normatively is not the same kind of thing as an explanatory memorandum, and
            `commentary` files them together. Rejected it on membership. Incorporation by reference
            is a property of the *citing instrument*, not of the document — the same OpenID4VP that
            the EUDI implementing acts make operative is, in `japan-id/corpus-specs`, a document
            with no legal force whatever. A tier whose members change according to who is citing
            them cannot order a conflict, which is the single thing @oxu7ik made this field for.
            And where a specification does bind, what binds is the implementing act's incorporation
            of it, and that act is already `delegated`; the specification's own text is still
            evidence of a rule nobody enacted. Decisively, the repo already answers its own
            question: `eidas-eudi/corpus-arf` files all 69 EUDI ARF items at `commentary`, and
            `taxonomy.md` §2 defends that placement by name, so `standard` is one corpus disagreeing
            with its sibling in the same repo about the same class of document. `corpus-specs`
            therefore reads `commentary`, and `lawcorpus.migrate` grows a `--retier old=new` so the
            correction rides the @oa2bvav5 migration instead of becoming a second hand-edit.
            Tradeoff: a finding that quotes an incorporated specification beside a policy slide sees
            them at equal rank and must say in prose which one an implementing act made operative —
            accepted, because that sentence is the analysis, and a tier that encoded it would be
            wrong the moment the same document is cited from another jurisdiction.

    cite.py refuses to quote without printing validity = decision:
      id: xrfhyv
      why: >
        The fetcher refuses to write an item with `validity` unset, and cite.py prints the validity
        banner above every quote it emits. Chose enforcement at the two chokepoints over relying on
        the research method doc, because the Aadhaar §57 trap is exactly the kind an agent working
        fast will walk into while believing it is following quote-or-drop. Accepted tradeoff: a
        noisier citation output, and hand-curation becomes a hard blocker on ingest rather than
        something that can be backfilled later.

    Corpus text is English-only, declared rather than assumed = decision:
      id: om6zsj
      why: >
        All 24 EU language versions are equally authentic and the CJEU resolves ambiguity by
        comparing them, so English-only is a real limitation and not a neutral default. Chose to
        take the limitation deliberately and declare it in every EU-derived finding rather than
        archive EN/FR/DE for load-bearing instruments, because the marginal cost is not the fetch
        (one extra call per CELEX) but the analysis — we cannot read a French divergence we do not
        have the competence to weigh, so archiving it would produce false assurance. Tradeoff: any
        finding that turns on a term of art is weaker than it looks, and must say so.

    translation_status is the Asian analogue of validity = decision:
      id: elsvh64d
      why: >
        Quote-or-drop proves a passage was *published*. `validity` closes the gap between published
        and *in force*. Over a translation neither closes the gap between the text quoted and the
        text that binds: an English My Number Act proves only that somebody translated it. Japan
        says so in its own words — 「法令翻訳は、正文ではなく…法的効力を有するのは日本語の法令自体」, where
        正文 is the technical term for authentic text — and KLRI says the Korean translations are
        "neither official nor legally effective". The KLRI English PIPA on offer is a 2025-10-02
        version against a Korean current text of 2026-09-11, so the staleness is real and dated
        rather than hypothetical. So every corpus item carries `translation_status`
        (authoritative | official-non-authoritative | unofficial | machine), required with no
        default, enforced at the same two chokepoints as `validity` — the item refuses to construct
        without it, and `lawcite` prints a translation banner above every quote whose item is not
        `authoritative`. Rejected making it optional-with-a-default of `authoritative`, which would
        have made every EU item silently correct and every Asian item silently wrong; an absent
        value must stop a harvest the way an absent `validity` does. Rejected inferring it from
        `lang`, because the hazard is not language: the EU's 24 versions are all authentic, and
        Singapore is natively English while SSO clause (8) declares its own text unofficial and
        disapplies Interpretation Act s48 — that is an `authority_tier` hazard and recording it here
        would be a category error the field must not tempt anyone into. Tradeoff: a fourth
        hand-curated field on every item in five corpora that have no translation problem at all,
        which is the price of a required field with no default.
      children:
        A translation is a separate item linked by translation_of = decision:
          id: xsjnzwvu
          why: >
            Chose a second corpus item carrying `translation_of` — the `item_id` of the original —
            over a per-item `translation:` sub-record or a parallel-text column. A translation has
            its own URL, retrieval date, sha256 and staleness, which is exactly the set of fields
            `ManifestItem` already carries, so a sub-record would duplicate the schema and a column
            would give one row two provenance stories. The link is checked when the manifest is
            written, not merely declared, because an unresolvable pointer is the kind of defect that
            surfaces years later in a citation. Two rules ride on it: a non-`authoritative` item must
            name its original, mirroring `validity_note`'s mandatory-when-not-in-force rule, and it
            must sit at `authority_tier: commentary`, because a translation that is not authentic
            text cannot outrank the instrument it renders. Tradeoff: a corpus holding a translation
            whose original is out of scope must fetch the original anyway, which is a real cost and
            is the point — an unanchored translation is what this field exists to refuse.

        Machine translation is never quotable as current law = decision:
          id: c5jtwe4i
          why: >
            `machine` makes `quotable_as_current_law()` False for the item however good its
            `validity` is, so machine output is filtered out by `lawcite --in-force-only` and carries
            a banner saying it is a reading aid rather than evidence. Rejected refusing to store or
            to print it at all: a machine translation is genuinely useful for deciding *which*
            provision to have rendered properly, and refusing to print would push it into an
            untracked scratch file outside every guard this package applies. Rejected treating it as
            merely another tier of non-authoritative text, because the failure mode differs in kind —
            an official-but-non-authoritative translation is wrong at the margin, while a machine
            translation can invert a negation with no signal at all. Tradeoff: the corpus can hold
            text nobody may quote, which is the same tradeoff `struck-down` already takes.

        The corpus repo migrates its own manifest; the reader never infers = decision:
          id: oa2bvav5
          why: >
            @elsvh64d made `translation_status` required and shipped with no migration, so
            `Manifest.read` began refusing every manifest written before it — seven files across
            four repos (`ccpa/corpus`, `ccpa/corpus-regs`, `civil-law-acts/corpus`,
            `eu-data-law/corpus`, and `eidas-eudi`'s `corpus`, `corpus-arf` and `corpus-specs`),
            which is `lawcite` broken against every published corpus except `japan-id`.
            `utah-id-law` is untouched, because it never moved off its three bespoke manifests —
            that is the duplication @s62c4j exists to end, not this defect. Rejected a reader that
            accepts a manifest declaring an older schema and refuses only to write it back: it must
            answer what `banners()` prints for an item whose provenance is unrecorded, and both
            answers are bad — printing nothing is @elsvh64d's rejected default wearing a version
            number, and a fifth vocabulary member is a redesign of the field that every consumer
            then has to handle. It also leaves the old schema readable indefinitely, so nothing ever
            moves the four repos off it. Rejected reading a manifest with no translation columns as
            `authoritative`, which infers the value from the absence of the value: it is right for
            these seven files and wrong for the first corpus that predates the column and holds a
            translation, and being obviously right here is how a default gets adopted that is
            silently wrong there. Chose a one-shot migration shipped in this package,
            `python -m lawcorpus.migrate <manifest> --translation-status authoritative`, whose flag
            has **no default** — the value is typed by the person who knows the corpus, and lands as
            a committed act with an author and a date rather than as a rule nobody signed. It
            refuses every token but `authoritative`, for the reason no script can work around: a
            non-authoritative item owes a `translation_of` (@xsjnzwvu) that an old manifest does not
            record, so that corpus must be re-harvested rather than rewritten. `Manifest.read`
            recognises the superseded header and raises once, naming the command and the path,
            instead of the same missing-column complaint on every row. Tradeoff: `lawcite` stays
            broken in each repo until its owner runs one command, which is the price of not choosing
            the value on their behalf.

        A qualifier that must travel with every quotation gets a column, defaulted = decision:
          id: ublm5oib
          why: >
            Tick ~7kgs deferred this pending a second source, and the second source arrived a day
            later with a different qualifier, which is the finding. `japan-id` writes 「（抄）」 into
            `citation` because e-Gov serves some instruments as `<MainProvision Extract="true">` and
            the partiality has to reach anyone who quotes one. `singapore-id` writes SSO clause (8)
            into `citation` because SSO declares its own text unofficial and disapplies Interpretation
            Act s48 to anything copied from it, and that has to reach the same reader. Two repos,
            two different facts, one workaround: both concluded that `citation` is the only field
            that travels with a quotation, and both said so in their own `this.i` — `singapore-id`'s
            @dt24v5pp ends "worth raising with `id-law-kit` rather than solving twice."
            The second source therefore refutes the shape ~7kgs was holding out for. A
            partial-instrument flag would carry Japan's case and not Singapore's, and the tick's own
            objection to it stands — a boolean does not say what is missing, and a field naming the
            omitted provisions duplicates what the oracle computes. What the two cases share is not
            partiality; it is that **the source qualifies its own text in a way a quotation must
            carry**. So the field is `quotation_qualifier`, free text, and `banners()` prints it
            above every quote beside the validity and translation lines.
            Free text rather than a vocabulary, which is the opposite of what `validity`,
            `authority_tier` and `translation_status` chose, and the difference is deliberate. Those
            three are read by code — they decide `quotable_as_current_law`, they sort by tier, they
            gate a sweep — so an unrecognised token must be refused. This one is read by a person:
            a disclaimer and an excerpt mark have nothing in common to enumerate, and a closed
            vocabulary would have had to be guessed at from one source and then broken by the second,
            which is exactly what just happened to the flag. Nothing branches on its value.
            **Optional, with a safe default, and therefore no migration** — which is the whole reason
            it can land at all. @elsvh64d's cost line ("a fourth hand-curated field on every item in
            five corpora that have no translation problem at all") is the objection, and it only
            applies to a *required* field. Absence here is not a guess about the world the way an
            absent `translation_status` was: an item with no qualifier is an item whose source did
            not qualify it, which is the ordinary case and the honest reading. So `from_row` fills a
            `DEFAULTED_COLUMNS` member that is not present, an existing fifteen-column manifest reads
            unchanged, and the column appears in a file the next time its harvester writes one.
            `LEGACY_COLUMNS` is frozen as a literal in the same change, because it had been derived
            from `COLUMNS` and would otherwise have grown a column it never had — which is how
            @oa2bvav5's seven broken manifests would have become eight.
            Tradeoff: nothing mechanical can filter partial items out of a sweep, which is the cost
            ~7kgs named and this does not pay off. A qualifier is prose, so an agent reading the
            manifest programmatically still cannot classify one — it can only see that there is a
            qualifier and print it, which is what a banner is for. The vocabulary question is
            reopened by a consumer that needs to *filter*, not by a third qualifier.

    Layout-only characters are normalised out of stored text = decision:
      id: f5mvj6
      why: >
        EU documents are typeset rather than typed: "Article 22" contains U+00A0 NO-BREAK SPACE
        between the word and the number (232 occurrences in judgment C-634/21 alone), and case
        numbers use U+2011 NON-BREAKING HYPHEN, so a search for "C-311/18" matches nothing. Both
        are invisible on screen, so a sweep returns zero hits and reads as a finding rather than
        as a bug — the same class of defect the utah-id-law adversarial review found in its own
        sweep patterns on 2026-07-29, but harder to see. Chose to normalise these to their plain
        equivalents at extraction, over the purer alternative of storing bytes verbatim and
        normalising in the search layer. Verbatim storage would keep `rg -z` over the raw corpus
        working the way utah-id-law advertises it, and that is a real loss. It was outweighed by
        the failure mode: a false negative in a sweep is silent, and this corpus exists to support
        negative claims ("the law nowhere requires X") that a silent false negative would
        fabricate. The set is deliberately narrow — only characters whose sole function is layout.
        Curly quotes, en dashes, and ellipses are preserved, because they are visible and because
        EU drafting uses the quotes to mark defined terms. Tradeoff: the stored text is not a
        byte-exact copy of what Cellar served, so the manifest's sha256 attests to our extraction
        rather than to the EU's file, and anyone needing the original bytes must refetch.
      children:
        Normalisation is unconditional, never switched on a language tag = decision:
          id: amdvdsah
          why: >
            The obvious design — apply a CJK fold to CJK documents, a Thai fold to Thai ones — was
            falsified by Phase 0 before it was written. Japanese uses U+3001 and **zero** U+FF0C;
            Korean has no U+3000 and no full-width punctuation at all, but 4,966 instances of
            U+318D `ㆍ`; Chinese uses U+FF0C 69 times and U+3001 79 times; Singapore's English
            carries U+2011, the EU trap. Decisively, the **English-language** CTID specification
            contains stray full-width parentheses — so a document's language tag does not predict
            its characters, and a rule keyed on the tag would have missed the one case that
            motivated it. Chose one set applied to every document, over a per-language switch and
            over the wider alternative of NFKC. NFKC is rejected outright: it decomposes Thai
            U+0E33 into U+0E4D+U+0E32, turning 18 hits for `สำนักงาน` into 0 — the standard remedy
            is itself a silent-false-negative generator. The set is width and invisibility only:
            full-width ASCII variants fold to ASCII because a full-width parenthesis means exactly
            what an ASCII one means, while U+3001, U+3002 and U+318D stay, because they are
            distinct characters carrying meaning rather than width. Tradeoff: stored CJK text is
            no longer typographically what the publisher served, extending @f5mvj6's departure
            from byte-exactness to five more jurisdictions.
          children:
            Query-side normalisation carries what text-side normalisation must not = decision:
              id: liv2lsxs
              why: >
                Two Phase 0 traps cannot be fixed by folding the stored text. Full-width
                enumerators like `（一）` are **structural** — they address provisions, so
                stripping them breaks citation — and U+318D is a visible list separator that
                @f5mvj6's own rule says must stay. Chose a second fold applied to the *search
                pattern* instead: a separator in a query expands to a character class matching all
                five spellings (U+318D, U+00B7, U+2022, U+30FB, U+FF65), and a non-ASCII character
                that the text-side fold rewrites is rewritten the same way in the query but
                regex-escaped, so a user who types a full-width parenthesis gets a literal rather
                than a capturing group. Rejected normalising ASCII characters in a query, which
                would turn `[0-9]` into a broken class — the fold only ever rewrites non-ASCII
                input, and that asymmetry is deliberate. Tradeoff: a separator inside a
                user-written character class produces a nested class that silently matches the
                wrong thing; it is documented rather than parsed for, because parsing a regex to
                normalise it costs more than the trap does.
              children:
                A CJK query tolerates the space letter-spacing puts inside a word = decision:
                  id: ux7izhdj
                  why: >
                    e-Gov writes the supplementary-provision heading as 「附　則」, U+3000 between the
                    two characters — 76 of one Act's 77 `<SupplProvisionLabel>` elements do it —
                    using the ideographic space as *letter-spacing inside a word*, which is ordinary
                    Japanese heading typography. `rg 附則` therefore finds none of those headings
                    while finding 312 cross-references to them in body text, which is @f5mvj6's
                    silent false negative exactly. The first conclusion reverses the obvious
                    reading: **@amdvdsah is not the cause, and narrowing it would not help.** Left
                    unfolded the heading is 「附　則」 and `附則` still matches nothing; folded it is
                    「附 則」 and a user who types an ASCII space at least reaches it. Dropping U+3000
                    from the set would forfeit the chapter-heading case `第一章　総則` and buy
                    nothing, so the rule stands unamended. Rejected collapsing the space on the text
                    side, which is where `japan-id` had to put it: doing it unconditionally welds
                    `第一章総則` together, so it needs a rule for which spaces fall inside a word, and
                    that rule is a Japanese lexicon. Chose the query side, which is what @liv2lsxs
                    is for — `normalise_query` inserts `[ 　]?` between two adjacent CJK
                    characters, so `附則` reaches 「附則」, 「附 則」 and raw 「附　則」 alike. Confined to
                    pairs where *both* characters are CJK, which is what keeps it from ever landing
                    beside a regex metacharacter; ASCII stays untouched, the same asymmetry
                    @liv2lsxs already draws. Tradeoff: a CJK phrase query can now match across a
                    genuine word separator, so 「個人情報」 would hit a line reading 「個人 情報」. That
                    is a false positive, visible the moment the hit is read, and what it replaces is
                    a zero that reads as a finding.

                A query digit reaches every numeral system, which needs the regex parsed = decision:
                  id: 4zotolb5
                  why: >
                    Reverses @liv2lsxs's "the fold only ever rewrites non-ASCII input, and that
                    asymmetry is deliberate". `thailand-id` found what the asymmetry costs:
                    `search_key` folds Thai digits onto Arabic and `normalise_query` does not, so
                    `lawcite --grep 'มาตรา 7'` returns zero against a corpus holding `มาตรา ๗` while
                    `มาตรา ๗` finds it. Two functions in one module disagreed about the same
                    question, and the one a user reaches through the CLI held the wrong answer. That
                    is @f5mvj6's silent false negative produced by the tool built to prevent it, so
                    the asymmetry cannot stand — the stored text keeps the source's own digits
                    (@amdvdsah: they are authentic, not layout), which leaves the query side as the
                    only place the two systems can meet.
                    The rejection @liv2lsxs recorded was not wrong about its reason. Expanding a bare
                    ASCII digit really does break `[0-9]`, and it breaks `\d{1,3}` and `\1` too. What
                    it got wrong was treating "parsing a regex costs more than the trap does" as
                    settled by a separator trap that nobody had hit, when the trap actually hit was a
                    digit — and a digit is not an occasional character in a legal query, it is what a
                    provision is addressed by. So the price is now worth paying: `normalise_query`
                    tracks three states a character can sit in — escaped, inside a character class,
                    inside a `{m,n}` quantifier — and rewrites nothing in the last two. A digit
                    outside them becomes a class holding that digit's spelling in every system;
                    inside a class it is *added to* the class, and an ASCII digit range gains the
                    parallel range in each system, so `[0-9]` becomes `[0-9๐-๙]` rather than the
                    nested rubble @liv2lsxs feared.
                    Two further things fall out of the scanner rather than being aimed at, and both
                    are fixes. @liv2lsxs's documented hole — a separator inside a user-written
                    character class producing a nested class — is closed, because a separator in a
                    class now contributes its five spellings as members. And @ux7izhdj's optional
                    space is no longer inserted inside a class, where `[個人]` had been rewritten to
                    something that is not a character class at all.
                    The systems are declared as data, `NUMERAL_SYSTEMS`, which both functions consume
                    — an asymmetry between them is now a thing that cannot be written rather than a
                    thing a reviewer must notice, and `tests/test_normalise.py` asserts the agreement
                    per system with a positive control in each script. Only systems the programme's
                    corpora actually use are listed, which today is Thai. Rejected enumerating every
                    Unicode decimal-digit script: a sixty-character class per digit buys reach into
                    corpora nobody holds and correlates nothing, and the list is where a future
                    script is added in one line.
                    Rejected folding CJK numerals here, which §8.3 names as a real trap (`第1条` finds
                    0 where `第五十七条` finds 19). `kanji_number` already reads them and the fold is
                    tempting, but `第六条` is not `第6条` spelled differently the way `๗` is `7` — the
                    kanji form is positional (十, 百) and reversing it into a query means generating
                    every spelling of a number rather than translating ten characters. It is a
                    separate decision with a separate risk, and bundling it into this one would hide
                    it. Tradeoff accepted: `normalise_query` now understands enough regex syntax to
                    be wrong about a regex, where before it could only be wrong about a character;
                    the states it tracks are the three that carry digits, and a `{` that is not a
                    quantifier suppresses the fold until the next `}` rather than corrupting it.

    An extraction is refused unless it matches a declared structure = decision:
      id: zpycgven
      why: >
        `method.md` §6's existing guard refuses an extraction that is *empty*. Indonesia produced
        the case it cannot see: UU 27/2022 is a 400-dpi CCITT scan whose OCR layer extracts to 52 KB
        of entirely plausible Indonesian and has silently lost Pasal 22, 70 and 72 and the whole of
        BAB XI–XII. It is full, it reads correctly, and three of the seventy-six articles of the
        Personal Data Protection Law are simply not there — `Pasal 22` returns 0 while `Pasal 21`
        returns 3 and `Pasal 23` returns 2. So a completeness oracle compares an extraction against
        a declared expected structure and **refuses to store on a mismatch**, following the
        California precedent in `method.md` §2 where the harvest aborts against the OAL notice
        rather than accept a chapter that is short. Chose an abort over a warning or a recorded
        `extraction_risk` flag, because a warning is a thing a later agent reads past and the corpus
        is the evidence base for negative claims — a missing provision manufactures "the law
        nowhere requires X" out of an OCR failure. Chose to name the missing provisions in the error
        rather than report a count mismatch, because a count tells the next reader to go looking
        while a list tells them where. Tradeoff: an instrument whose structure nobody has declared
        is stored unchecked, so the oracle's value is bounded by how many sources hand one over —
        which is why the free ones below matter more than the machinery.
      children:
        The three free oracles Phase 0 found are wired in, not hand-declared = decision:
          id: oym7gzus
          why: >
            Hand-declaring an expected structure per instrument is the cost that would stop this
            check being used, so three sources that state their own shape are built in. Japan's
            per-instrument `<TOC><ArticleRange>` is authored by the publisher rather than by our
            parser, which makes it a genuinely independent oracle and a better one than the
            California OAL notice because it ships inside every instrument. Korea's article
            numbering is gapless from 1 to the maximum, because repealed articles survive as `삭제`
            placeholders rather than being removed — it held 7 for 7 across the instruments Phase 0
            retrieved. Indonesia's per-record `status_hukum` maps onto the `validity` vocabulary
            directly (`berlaku` → in-force, `sebagian` → amended, `dicabut` → repealed), so one
            corpus gets machine-derived validity where `taxonomy.md` §3 assumes hand curation.
            Rejected treating Korea's rule as general: it derives the expectation from the
            extraction itself, so it catches an interior gap and is blind to a truncated tail, and
            saying so in the docstring is worth more than pretending otherwise. Tradeoff: three
            jurisdiction-specific readers in a jurisdiction-neutral package, accepted because the
            alternative is the same code written five times in five corpus repos, which is the
            duplication @s62c4j exists to prevent.

        A scan can be bounded, because a schedule restarts the numbering = decision:
          id: qd6p2f3x
          why: >
            `Expectation.verify` reads the whole document and calls the headings out of order unless
            they ascend. Japanese 附則 — supplementary provisions — restart at 第一条 in every
            instrument that has them, and an Act carries one block per amending act, so a correct
            document reads as damaged. `japan-id` worked around it by prefixing every supplementary
            line with its block label, which is a rendering changed to satisfy a checker, and the
            wrong place for the fix: nothing about this is Japanese. A UK schedule, a French annexe
            and a US appendix all restart their numbering. Chose a `boundary` regex on `scan` and on
            `Expectation`, matched per line, that ends the scan at the first line matching it — over
            teaching `verify` to tolerate a descending step. Tolerance is the weaker answer twice
            over: it would forgive the OCR misread @zpycgven's own message describes, UU 27/2022's
            BAB XI reading as a bare I between IX and X, and it would let a provision surviving only
            inside a schedule satisfy a declaration about the main body — so a lost article would
            read as present. Bounding the scan fixes both at once, because what is declared and what
            is scanned then describe the same part of the document. The two built-in oracles set
            their own boundary (附則, 부칙), since knowing where a jurisdiction's schedules begin is
            exactly what a jurisdiction-specific oracle is for. Default `None`, so no existing caller
            changes. Tradeoff: everything past the boundary is checked by nothing, and a corpus that
            wants its schedules verified declares a second expectation over them rather than getting
            it free.

        The Japanese oracle reads the two shapes that make a correct document look damaged = decision:
          id: y3aozl55
          why: >
            `japanese_article_range` refused two documents e-Gov serves with nothing wrong with them.
            First, 「第十条から第十五条まで　削除」 — six consecutive repealed articles collapsed into one
            heading, which is ordinary drafting; a heading scan reads the first and reports the other
            five missing. Second, `<MainProvision Extract="true">`, e-Gov saying it is serving a
            *part* of an instrument whose table of contents still describes the whole, so the oracle
            declares articles the response was never going to carry. `japan-id` handled both in its
            own harvester, so the next Japanese corpus would have written them again. For the
            collapsed range, chose to read it from the instrument's own `<ArticleTitle>` and drop
            those articles from the expectation, over emitting five headings the source does not
            contain so that the count comes out — an oracle permitted to edit its evidence passes
            everything eventually. For the partial document, chose an expectation that declares
            nothing and still checks **order**, over the caller's workaround of skipping the oracle
            outright: order is what caught a rendering bug in `japan-id` nobody was looking for,
            where a sub-item opening 「第九条第四号に掲げる…」 read as article 9 arriving after article
            10. Tradeoff: a partial instrument is then verified by almost nothing, so its `source`
            string has to say so in the words of the refusal it will never raise — an expectation
            that passes everything is worse than no oracle at all (@zpycgven), and the only defence
            against it being mistaken for one is that it announces itself.

        The kanji numeral reader is public, because Chinese will want the same door = decision:
          id: ooyin3yr
          why: >
            `_kanji` was private, so `japan-id` read a single article number by calling
            `scan("第五十七条", "第", numerals="kanji")[0]` — assembling a fake heading in order to
            reach a parser. Chose to publish it as `kanji_number`. It is fifteen lines, it is not
            Japanese but CJK — the same characters number Chinese provisions — and a corpus that
            must read 一二三十百 outside a heading scan has no other way in. Rejected publishing the
            arabic, roman and thai readers beside it for symmetry: `int()` and a digit fold need no
            door, and symmetry here would be four public names covering one real need. Tradeoff: one
            more public name to keep stable, against a caller otherwise reaching into a private one,
            which is the same dependency with none of the obligation admitted.

        A sub-numbered provision is a value, not a number it collapses onto = decision:
          id: kolycpun
          why: >
            `scan` read `มาตรา ๓๒/๒` as 32, `第六条の二` as 6, `제24조의2` as 24 and `Pasal 13A` as 13 —
            four jurisdictions, one behaviour, and it was written down as intended rather than
            noticed as a defect. Inserted provisions are how every one of these systems amends a
            statute without renumbering it, so the collapse is not an edge case; it is the ordinary
            shape of an amended act. What it costs is an oracle that cannot tell an inserted section
            from a duplicate heading, so a declaration of `32` is satisfied by a document that
            carries only `32/2` — the oracle silently accepting a short extraction, which is the one
            thing @zpycgven exists to stop.
            Chose a value type, `Provision`, over the two alternatives that keep `scan` returning
            plain integers. A decimal (32.2) collides — 32/2 and 32/20 are not 32.2 and 32.20 — and a
            string loses ordering, where the whole point of the sequence is that 6/2 sorts before
            6/10 and both sort between 6 and 7. `Provision` carries the base and a tuple of
            sub-tokens, and **compares equal to its own base integer when it has no sub-number**, so
            an `Expectation` declared over ordinary integers — which is every consumer today, and
            what `korean_gapless` derives — keeps working untouched. Hashing agrees with that
            equality, because the check is a set membership test and a type that is equal but hashes
            differently fails it silently.
            Sub-numbering is declared per numeral system rather than built into `scan`, so Thai's
            `/`, Japanese's `の` and common-law's bare letter suffix are three table entries and a
            fourth is a line. A letter suffix sorts after the bare number and before the next one,
            which is what `23 < 23A < 23B < 24` requires and what a tuple of mixed tokens gives once
            each token carries its own kind in the sort key.
            Rejected Korean's `조의2`, which needs `조` in the pattern and would put a Korean particle
            into the numeral system every Latin corpus uses. Rejected folding a letter suffix to a
            number: `23A` and `23/1` are different provisions in different drafting traditions, and
            making them the same value would be this defect again with the collapse moved.
            Tradeoff, and it is the loud one: **`scan` no longer returns integers**, so a consumer
            doing arithmetic on its result breaks. `Provision` carries `__index__` so `range()` and
            `int()` reach the base, and `korean_gapless` is corrected here — but a corpus repo that
            scans and adds must be re-run, and a document carrying `13A` where its oracle declares
            `13` now fails where it used to pass, which is the check working rather than the change
            regressing.

        An instrument with no provision labels is checkable, and its own index is not evidence = decision:
          id: q5fyyb4q
          why: >
            `Expectation` scans `<label><number>` headings, and Singapore's drafting has no label:
            a section heading is a bare `3.—(1)`. `singapore-id` could not use the class at all and
            wrote its own, which is the per-corpus duplication this package exists to prevent — and
            it hit a second failure in the same document, because an SSO PDF prints its own table of
            contents before the body, so every section number appears two to four times and the
            out-of-order check fires on a perfectly good extraction.
            Two additions, and they are deliberately not a switch that turns the order check off.
            `terminator` is a regex the number must be followed by, which is what makes a label-less
            scan safe — `3.` followed by an em dash or a space is a heading, where a bare `3` at the
            start of a line is any wrapped list item. An empty label with no terminator is refused
            rather than scanned, because that pattern matches most of a document and an oracle that
            matches everything passes everything. `start` is the mirror of `boundary`: it marks
            where the body begins, and the text before it is dropped. With the contents page cut off
            the front and the Schedules cut off the back, the numbers are in ascending order again
            and the check that @zpycgven relies on survives intact.
            `start` fails closed. A declared opener that is not found raises rather than scanning the
            whole text, because the failure it prevents is the document's own index vouching for
            sections the body may not contain — a truncated PDF still lists its missing tail on its
            contents page, so an oracle reading both certifies the damage as complete.
            Rejected `singapore-id`'s shape of answer, a set-membership check with the ordering
            replaced by a highest-present tail/interior classification. Its diagnosis is better and
            its check is weaker, and the weaker half is load-bearing: order is what caught a renderer
            dropping sub-item numbers in `japan-id` (@y3aozl55). Keeping the order check and cutting
            the front matter gets both. Rejected a caller-supplied callable for the body boundary,
            which is a regex wearing a function. Tradeoff: an instrument whose body opener cannot be
            expressed as a line regex is not served here, and `_window` gives a caller no way to say
            "the second match" — recorded now rather than discovered by a corpus that needs it.

    A lettered provision number is a structural opener = decision:
      id: zr3b5ll2
      why: >
        `_STRUCTURAL` is the list of line openers `_rejoin_wrapped_lines` must never weld to the
        line above, and it recognised `\d+\.` and not `23A.`. The consequence is not cosmetic and it
        is not confined to the heading: a lettered section's heading is glued onto the marginal note
        preceding it, so the section stops being line-anchored, so `completeness.scan` — which is
        line-anchored on purpose (@qd6p2f3x) — cannot see it at all. `singapore-id` measured it on
        the National Registration Act 1965: 33 of 34 sections scan and the one that fails is the
        lettered one, which is the whole shape of the Electronic Transactions Act's Part 2A, ss.16A
        to 16S — the provisions that repo exists to read. So one missing alternative in one regex
        silently removed a jurisdiction's central finding from every scan run over it.
        Chose `\d+[A-Z]{0,2}\.`, which is `singapore-id`'s own measured pattern less its lookahead.
        Lettered and suffixed provisions are near-universal in common-law drafting — Singapore,
        Malaysia, India, the UK, and Indonesia's `Pasal 13A` — so this is a hole in the general
        cleaner rather than a Singapore quirk, which is why it is fixed here rather than worked
        around per corpus. Two uppercase letters covers every form observed; three would begin to
        admit an all-caps word followed by a full stop. Rejected `singapore-id`'s `(?=—|\s)`
        lookahead: that pattern has to run mid-line, where a bare `1965.` ending a sentence reads as
        section 1965, and this one is anchored at the start of a line where that cannot arise.
        Tradeoff: a line opening with a year and a full stop was already treated as structural by
        `\d+\.` and still is, so the change adds no new false opener — but it does mean a document
        whose lines genuinely begin `12A.` mid-sentence will no longer be rejoined, which is the
        direction this package errs in deliberately: an unjoined line is visible, a welded one is not.

    Furniture is recognised by its shape, not only by its repeated text = decision:
      id: ly7tho4y
      why: >
        `strip_repeated_furniture` matches a running head by exact text repeated at the page edges,
        and a publisher that prints the page number *inside* the header line defeats it completely,
        because no two pages then carry the same string. Singapore's SSO writes
        `2020 Ed.   National Registration Act 1965   6`. Measured on the Personal Data Protection
        Act: 124 of 124 footers stripped, and the header survived on 120 of 123 pages, landing
        mid-provision through a 194,000-character document. A running header inside a sentence is
        `method.md` §6's canonical case of output that looks fine and greps wrong, and `_PAGE_NUMBER`
        does not reach it because the line is not a page number, it merely contains one.
        Chose a shape rule beside the text rule rather than instead of it: each edge line is reduced
        to a template by collapsing whitespace and masking every digit run, and a template is
        furniture when it recurs across pages, carries at least one letter, and has at least one
        masked field whose values **strictly increase** with the pages carrying it. The increasing
        field is what makes the rule safe. "Constant except for a varying number" on its own would
        also describe the edge rows of a long numbered table, and a rule that eats content to remove
        furniture is worse than the furniture; a field that counts up with the pages is a page
        number and nothing else in a statute behaves that way.
        The threshold for the shape rule is lower than `FURNITURE_THRESHOLD`, and that is forced
        rather than tuned. Printed legal publishing mirrors its running heads between recto and
        verso — SSO puts the page number on the left of an even page and the right of an odd one —
        so a mirrored header is two templates each appearing on about half the pages, and any
        threshold above one half structurally cannot see one. 0.4 leaves margin for a title page and
        a landscape insert.
        Rejected lifting `singapore-id`'s answer, which anchors on the literal `<year> Ed.` edition
        mark. It is correct and it is measured, and it is a Singapore string: every other publisher
        would need its own anchor, which is the per-corpus duplication the kit exists to stop.
        Rejected a caller-supplied anchor regex for the same reason — it makes each corpus solve it
        again, with the added cost that a repo which does not know it has this problem will not pass
        one. Tradeoff: the shape rule can in principle eat a genuine edge line that repeats on 40% of
        pages with a page-correlated number in it, and the three conditions are what make that
        unlikely rather than impossible; `raw_pages` remains available for a caller that needs the
        pages before any of this runs.

    A Japanese PDF path, because the English cleaner corrupts one silently = decision:
      id: 3i2xqflu
      why: >
        `pdf.extract`'s line rejoiner is English. `_UNTERMINATED` judges a line mid-sentence unless
        it ends in `.:;?!`, so every Japanese line ending in 。 is read as unfinished and welded to
        the one below — and the weld inserts **a space**, which Japanese does not put between words.
        Over a Digital Agency slide it turns 「③発行者の電子署名から構成される」 into 「③発行者の 電子署名
        から構成される」, and the phrase can no longer be found at all: the cleaner manufacturing the
        false negative rather than the PDF. `japan-id` wrote its own extractor and cited @7xsnhink
        for doing it, which is the right precedent in the wrong place — the next Japanese corpus
        writes it again. Two halves, following @7xsnhink in both. `pdf.clean_pages` **refuses** an
        extraction whose CJK character share crosses a threshold, naming the module that handles it:
        a gate, not a repair, because text stored after being welded is the failure that looks like
        success, and the English path had no way of announcing that it was the wrong one. And
        `japanese.py` carries the working path — rejoin with no separator, only where the previous
        line ends mid-sentence by Japanese punctuation and the next opens with a Japanese character
        rather than a bullet or an enumerator. Conservative in both directions, because welding two
        unrelated slide fragments together invents a phrase, which is the same failure pointing the
        other way. Rejected a `script=` argument on `extract`: @amdvdsah's finding is that a document
        does not reliably declare its script and the caller frequently does not know either, so the
        share is measured rather than declared. Hangul is deliberately outside the measure — Korean
        writes spaces between words, so the English rejoiner is approximately right there and a gate
        would refuse documents it can handle. Tradeoff: a genuinely mixed document has to be routed
        by hand, and the threshold is a number read off the documents in hand rather than derived
        from anything.

    Thai PDFs get their own path, which refuses more than it repairs = decision:
      id: 7xsnhink
      why: >
        `pdftotext` drops U+0E33 `ำ` from Gazette PDFs **100% of the time**: `กำหนด` — "to
        prescribe", among the highest-frequency verbs in any statute — occurs 87 times in the PDPA
        and matches zero. The loss is producer-dependent, so a spot check on a Word-produced
        document finds nothing wrong. A second class of Gazette PDF carries a subset font with no
        ToUnicode CMap and extracts to non-empty, plausibly-Thai-looking noise, which the
        empty-extraction guard cannot see. Chose to gate rather than to repair: an extraction whose
        Thai character ratio collapses, or which contains no U+0E33 at all in 200 KB of Thai prose,
        is **refused** and routed to OCR. Rejected storing it with an `extraction_risk` flag, for
        the reason @zpycgven gives — a flag is a thing a later agent reads past, and this corpus
        exists to support negative claims. Rejected NFKC as the normalisation, in the strongest
        terms available: it takes `สำนักงาน` from 18 hits to 0, so the standard remedy is the
        failure. Tradeoff: Thai instruments that a human could read past the damage are refused
        outright, and the Thai corpus depends on the API's section-by-section JSON as its text with
        the Gazette PDF as provenance only.
      children:
        Mark reordering is repaired only where a repair cannot be wrong = decision:
          id: psletl4a
          why: >
            `pdftotext` orders glyphs by horizontal position, so a Thai tone mark sitting above its
            base consonant is emitted *after* the following consonant: `เล่ม` extracts as `เลม่`,
            `หน้า` as `หนา้`. Nothing in Unicode normalisation repairs it — NFC of `เลม่` is not
            `เล่ม`. The tempting fix, moving any mark left past the preceding consonant, is wrong:
            `กล่าว` is a correct consonant cluster with the mark on the *second* consonant, and the
            two cases are indistinguishable without a lexicon. So the repair is confined to the
            sequence that can never be correct — a tone mark following U+0E32/U+0E33/U+0E45, which
            repairs `หนา้` — and the ambiguous cluster case is left alone rather than guessed at.
            Rejected a lexicon-based repair as out of proportion to a kit whose Thai text comes from
            an API in the first place; the Gazette header, where the reordering was observed, is
            stripped as furniture instead. Tradeoff: a Thai corpus built from PDFs still carries
            reordered marks in body text, and `search_key` does not fold them, so a phrase search
            across one can still under-count — recorded as a tick rather than pretended away.

        A mixed-script page is judged on whether its Latin reads as words = decision:
          id: szp4xt3n
          why: >
            @7xsnhink's mojibake gate reads a collapsed Thai character ratio as noise from a subset
            font, and on a Thai document containing Latin it is simply wrong. `thailand-id` had five
            documents refused, **four of them sound**, and every refusal was a bibliography page —
            Latin citations inside a Thai instrument, where the Thai share of the letters legitimately
            falls below half. A gate that refuses good documents is worse than no gate, because the
            remedy a person reaches for is turning it off, and then the one genuine mojibake document
            is stored.
            The discrimination is `thailand-id`'s, lifted rather than reinvented: the share of Latin
            runs on the page that **read as words** — three or more letters with at least one vowel.
            Measured 0.92, 0.94, 0.94 and 0.97 on the sound pages against 0.12 on the damaged one, an
            order of magnitude apart rather than a margin, which is why a crude test is the right one.
            Mojibake from an encoding-less subset font lands as Latin letters in runs that are short
            and vowelless; real citations do not.
            It is wired as a **reprieve inside the gate, not a replacement for it**. The ratio still
            decides that a page is suspect; the word test can then clear it, and only when there are
            at least eight Latin runs to judge — below that the score is noise and the page is refused
            as before, which keeps the gate fail-closed on the case it cannot see. Rejected lifting
            `thailand-id`'s second test as well, the Thai-OCR trigram agreement: it is a better
            discriminator and it needs tesseract and a Thai traineddata file, so putting it here would
            make a gate in the core path depend on a binary most consumers do not install. That test
            belongs where it is, in the consumer that already pays for OCR. Tradeoff: a damaged page
            whose noise happens to read as English words is now stored where it used to be refused —
            bounded by the fact that the failure mode is an encoding, not a language model, and the
            measured gap is eight to one.

        Dropped tone marks are the third corruption mode, and nothing saw them = decision:
          id: h4srdl2g
          why: >
            @7xsnhink names two ways a Thai extraction is silently wrong, and `thailand-id` found a
            third that passes both. The DOPA/ThaID manual extracts with U+0E33 intact — sixteen
            occurrences, so the sara-am gate is satisfied — and with every tone mark gone: `สราง` for
            `สร้าง`, `ใหม` for `ใหม่`, `พิสูจน` for `พิสูจน์`. Its Thai character ratio is high, so the
            mojibake gate is satisfied too. The text is readable, wrong, and greps wrong, which is the
            exact profile @zpycgven refuses to store.
            Chose the same shape as the sara-am gate, deliberately, because the evidence has the same
            shape: not one tone mark in a document long enough that zero is impossible. Thai writes
            U+0E48–U+0E4B on the order of one character in twenty, so 500 Thai characters carrying
            none is a typesetter that lost them rather than prose that happens not to need them —
            a wider margin than the sara-am gate runs on at the same floor. A separate error class,
            because the remediation differs from the other two only in what to tell the reader, and
            @7xsnhink's family prefix is what a caller matches on.
            Rejected a *proportional* test — tone marks below some share of the Thai characters —
            which is what a partial loss would need. Every observed instance is total, a threshold on
            a ratio needs a corpus to calibrate that nobody has measured, and a gate calibrated by
            guess refuses good documents, which is @szp4xt3n's lesson from the same week. Rejected
            also gating on U+FFFD, which `thailand-id` notes is a usable signal in the same document:
            it is a real signal and a different obstacle — bytes that did not decode, not marks that
            were dropped — and bundling it here would put two unrelated refusals behind one code.
            Tradeoff: a document losing *most* of its tone marks still passes, and the gate's honesty
            is that it says what it checked rather than implying the text is sound.

    A browser fetcher, scoped to the two obstacles a browser can actually remove = decision:
      id: lkm7beuo
      why: >
        Phase 0 (asia-id-strategy.md §8.5) established that every *primary* acquisition route in the
        Asian set needs no browser: Japan's e-Gov API, Singapore's `?ViewType=Pdf`, Indonesia's
        `jdih.setneg.go.id` JSON API, Thailand's `apig.law.go.th`. A browser earns its place against
        exactly two secondary obstacles that nonetheless hold load-bearing answers. First, Cloudflare
        managed challenges on HTML routes — `ratchakitcha.soc.go.th` returns `cf-mitigated: challenge`
        on HTML while serving `/documents/<id>.pdf` straight through, so the authoritative publication
        is retrievable and its search UI is not. Second, pages with no API behind them:
        `bora.dopa.go.th` answers 200 and renders client-side, and Phase 0 could read four links out
        of it, which is why ThaID's wire format is still the Thailand spike's largest gap. Rejected
        the broader framing of "a browser fetcher for hard sites", because it is false advertising for
        the two Indonesian cases that matter most: `peraturan.go.id` black-holes the TCP SYN and every
        `kemendagri.go.id` host is blocked outright, and no browser reaches a socket that never opens.
        The module docstring says so in those words, so nobody spends a day pointing Chromium at a
        dead socket. Tradeoff accepted: a second acquisition mechanism to maintain, whose failure
        modes (browser versions, cached binaries, a page that renders differently headless) are less
        legible than curl's.

    Playwright is an optional extra, never a core dependency = decision:
      id: 2sc5rmg4
      why: >
        `lawcorpus` is imported by five corpus repos, most of which will never launch a browser, and
        a browser is ~170 MB of cached binaries plus a driver process. So `playwright` sits behind a
        named extra (`pip install 'lawcorpus[browser]'`), the import happens inside the call rather
        than at module scope, and its absence raises a code of its own naming the install command.
        Rejected a soft `try: import playwright / except: playwright = None` at module top, which
        turns a missing dependency into an AttributeError at the first call site. Rejected vendoring
        or shelling out to a system browser, which trades one dependency for a less inspectable one.
        Tradeoff: an error path that only fires on machines without the extra, which is exactly the
        path most likely to rot — so it is unit-tested by injecting the importer rather than by
        trusting the environment.

    A challenge page is refused, never returned, and refusal is a first-class outcome = decision:
      id: 5bo2uarc
      why: >
        Phase 0's worst finding was an extraction that looked fine and had silently lost four
        articles (§8.4). An interstitial stored as law is that same failure wearing a different hat,
        and it is worse, because "Just a moment..." is 29 KB of plausible HTML that a completeness
        check over an unknown structure would not catch. So detection runs on every fetch, in both
        modes, and refuses on: a `cf-mitigated` header, a Cloudflare interstitial or deny body, any
        status that is not 200, and an empty 200. Verified against live hosts 2026-09-16 — the
        Gazette answers `cf-mitigated: challenge` with title "Just a moment..." even to a real
        headless Chromium, and `peraturan.bpk.go.id` answers a static "Access Denied … Country: US",
        which is a different obstacle needing a different remedy (an Indonesian egress, not a
        browser) and therefore carries a different code. Chose to raise rather than return a
        `refused` result object: a returned result is a thing a caller can ignore by reading only its
        `body`, and this repo's whole posture is that the dangerous failure is the one that looks
        like success. The refusal carries its provenance, so a caller can still record what happened.
        Tradeoff: a caller who genuinely wants the interstitial bytes (to diagnose a WAF) must read
        them off the exception rather than from a return value.

    We do not defeat access controls; the honest outcome is "retrieve it by hand" = decision:
      id: v2xlormp
      why: >
        The fetcher uses a real browser with its ordinary user agent and ordinary behaviour, and
        stops there. No CAPTCHA or Turnstile solving, no stealth patches to hide the automation
        flags, no user-agent or proxy rotation, no retry loop that waits out a challenge. Where a
        site has said no, the supported outcome is a refusal naming the host and telling the caller
        to retrieve the document by hand — which is what the Thailand spike itself did, recording the
        challenge as a finding rather than routing around it. Rate limiting is on by default (one
        navigation per interval, configurable) rather than opt-in, because a polite default that
        someone must switch off fails safe and an impolite one does not. The reasoning is not only
        ethical: a corpus assembled by misrepresenting who we are is evidence we could not cite in
        the regulatory conversations this programme exists to have. Tradeoff: some documents stay
        unreachable that a less scrupulous tool would fetch, and the Gazette's search UI is one of
        them.

    Provenance for a rendered page attests to our rendering, not to the server's bytes = decision:
      id: rl2fgk3p
      why: >
        A browser fetch that cannot report its status code is not manifestable, so every fetch
        records the final URL after redirects, the HTTP status, the content type, the byte count and
        the SHA-256, and hands back the same fields a manifest row needs. But the two modes differ in
        what the digest covers, and the difference is not cosmetic: in document mode it is the bytes
        the server sent, and in rendered mode it is the serialised DOM *after* client-side scripts
        ran, which no refetch will reproduce byte-for-byte. Chose to keep both under one provenance
        type with the mode recorded in it, over inventing a second manifest shape. This is the same
        tradeoff already accepted at @f5mvj6 for normalised text, and it needs the same warning
        attached: a rendered item's sha256 attests to what we saw, so anything load-bearing should be
        quoted from a document-mode fetch where one exists.

    Access windows belong to the kit, not to one jurisdiction's harvester = decision:
      id: asbhej3z
      why: >
        Singapore's SSO clause (13)(d) permits automated extraction only between 3 a.m. and 7 a.m.
        Singapore Time (§8.2), which is the first instance of a general shape: a source that grants
        permission conditionally on when you ask. Chose a declarative `AccessWindow` on the fetcher —
        local hours plus an IANA zone, refusing outside the window with a message naming the source's
        own term — over a cron entry in the Singapore repo. A cron entry encodes the rule where
        nobody reading the fetcher can see it, and it enforces nothing if a human runs the harvester
        by hand at noon. The window is checked before the browser launches, so an out-of-window run
        costs nothing and cannot half-happen. Tradeoff: the kit now carries a timezone dependency and
        a notion of "now" that must be injectable for tests; and a window is a blunt instrument for
        what is really a revocable contractual permission, so the licence reasoning still has to live
        in the corpus repo's this.i.

    Error codes stay in this package's `BK_*` idiom rather than the dotted standard = decision:
      id: 4jeup7vd
      why: >
        *** Reversed 2026-09-16 by @sqxhmdkt, which supersedes this node for all new code. The
        reasoning below is kept because the tradeoff it names is real and still governs the nine
        *published* `BK_*` codes, which do not change identity. What it got wrong is recorded at
        @sqxhmdkt: two other modules written the same day conformed, so the consistency this node
        was buying had already been spent before it was written. ***
        `dev/standards/error-codes.md` specifies `<sorter>.<descriptor>.<disposition>` — the browser
        refusal would be something like `e.party.refused.f` and the missing extra
        `e.feature.unsupported.f`. Every existing code in this package is flat `BK_*`
        (`BK_LAWCORPUS_ERROR`, `BK_EURLEX_FETCH`, `BK_MANIFEST_INVALID`). Chose consistency with the
        package over conformance in one new module: a caller catching `LawcorpusError` and branching
        on `.code` should not meet two grammars, and prefix matching — the whole point of the dotted
        form — does not work on a set of codes that is half converted. Recorded rather than silently
        copied, because the standard is the standard and this is a deviation with an expiry date: the
        migration is one change across the package, tick ~6fpq.

    New code conforms to the dotted standard; only published codes stay flat = decision:
      id: sqxhmdkt
      why: >
        Reverses @4jeup7vd. That node argued for consistency with the package, and the argument was
        already false when it was written: `thai.py`, `completeness.py` and `validity.py` landed the
        same day in the dotted grammar, so the package was mixed either way and the only question
        left was which idiom the *next* module joins. The tie is broken by the asymmetry in cost. A
        published code's identity may not change (`error-codes.md`, "a code's meaning and `args`
        signature never change once shipped"), so every flat code we add is another deprecation the
        ~6fpq migration must pay for, while a new module written dotted costs nothing at all. The
        rule is therefore: new code is dotted, the nine shipped `BK_*` codes keep their identity
        until ~6fpq retires them with named successors, and no tenth flat code is ever minted —
        `tests/test_error_codes.py` enforces that against a frozen list rather than trusting a
        reader to notice. Rejected converting the published nine in this change, which is the same
        false economy in the other direction: nine identity changes bundled into a grammar cleanup,
        with no deprecation window for the corpus repos that catch them.
        The five browser codes are classified by obstacle, not by the module that raises them, which
        is what put four of them under four different first descriptors. `e.party.refused.f` for a
        Cloudflare challenge or a deny page: a host that serves an interstitial is an actor that
        chose, which is the standard's own agency test for `party` against `env`, and this is the
        registered example verbatim. Final, not retryable, and the disposition is load-bearing here
        — @v2xlormp forbids a loop that waits out a challenge, so an `r` would advertise the very
        behaviour the design refuses. `e.rule.access.window.r` for a fetch outside the hours a
        source permits automation: `rule` is "a norm we enforce, neither authority nor
        verification", and that is exactly what @asbhej3z does with SSO clause (13)(d) — nobody's
        credential is being evaluated, so it is not `grant`, and the `grant` reading would have been
        tempting because a window looks like `validFrom`/`validUntil`. Retryable, because the window
        reopens; the contrast with the challenge above is the whole reason the disposition is a
        token rather than prose. Chose `access.window` over `access-window` on the standard's own
        hyphen test — access is a subject that can have other problems in this package (a robots
        directive, SSO clause (19)'s ban on caching), so it is a level, not half a name.
        `e.self.config.browser.f` for a missing Playwright extra or browser binary: the settled
        boundary says the locus decides, and the reason we cannot reach the material is our own
        installation rather than the world's. Rejected @4jeup7vd's guess of
        `e.feature.unsupported.f` — `unsupported` means nobody can, and this capability ships, it is
        merely not installed here. `e.input.format.f` for a URL, window or interval the caller
        declared wrong: decidable by inspecting the arguments alone, which is the `input` boundary,
        and deliberately the bare registered code rather than a leaf of our own, because nobody
        diagnoses, documents or counts "bad argument to a browser fetcher" separately from any other
        malformed argument. `e.env.browser.f`, with `e.env.browser.r` below, for everything else the
        browser channel fails to deliver.
        One inconsistency in the sibling modules is fixed in the same change.
        `e.input.translation-status.f` put a leaf of ours at the level the standard fills with
        `.missing`/`.format`/`.range`/`.multi`, so it was unreachable from `e.input.format.` while
        its neighbour `e.input.format.oracle.f` — the same kind of obstacle, a declared token this
        package cannot read — was reachable. Now `e.input.format.translation-status.f`. The other
        six dotted codes are right as minted and are left alone.
      children:
        Retryability is read off the code, which forced a second browser error class = decision:
          id: 3tkymxtr
          why: >
            `LawcorpusError` carries a `transient` flag and the dotted grammar carries a disposition
            token, and until now nothing kept them in step. `BrowserError` proved it: one class, one
            code, and six raise sites of which two passed `transient=True` (a timeout or dead
            browser process, and a 5xx from the source) and four did not (a browser that will not
            start, a navigation with no response, an unexpected status, an empty 200). Any single
            disposition on that code would have been a lie about four sites or two. Chose to make
            the code authoritative — `transient` now defaults to whatever the code's last token says
            — and to split off `BrowserTransientError` carrying `e.env.browser.r` for the two sites
            that genuinely may succeed on a later attempt. Rejected leaving the flag to each raise
            site and choosing the majority disposition, which is what makes a caller give up on a
            timeout. Rejected deriving the whole code string from the flag, which `error-codes.md`
            forbids: codes are module-scope literals so a catalog can be extracted by static
            analysis. Rejected re-homing the four final sites into other classes to avoid a new
            class, because that changes which exception a caller catches, and this repo's consumers
            catch these by type. The base keeps the `f`, so a subclass that forgets to declare a
            code inherits the fail-closed answer rather than promising a retry. Tradeoff: one more
            public class in `fetch/browser.py`, and a caller that wants both halves now matches the
            prefix `e.env.browser.` rather than one code — which is what prefixes are for, and is
            why the subject sits above the disposition.
