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
