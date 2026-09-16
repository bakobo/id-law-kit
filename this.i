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
        `dev/standards/error-codes.md` specifies `<sorter>.<descriptor>.<disposition>` — the browser
        refusal would be something like `e.party.refused.f` and the missing extra
        `e.feature.unsupported.f`. Every existing code in this package is flat `BK_*`
        (`BK_LAWCORPUS_ERROR`, `BK_EURLEX_FETCH`, `BK_MANIFEST_INVALID`). Chose consistency with the
        package over conformance in one new module: a caller catching `LawcorpusError` and branching
        on `.code` should not meet two grammars, and prefix matching — the whole point of the dotted
        form — does not work on a set of codes that is half converted. Recorded rather than silently
        copied, because the standard is the standard and this is a deviation with an expiry date: the
        migration is one change across the package, tick ~6fpq.
