"""Browser fetcher — for the two obstacles a browser can actually remove, and no others.

Phase 0 of the Asian programme (`asia-id-strategy.md` §8.5) established that every *primary*
acquisition route needs no browser: Japan's e-Gov API, Singapore's `?ViewType=Pdf`, Indonesia's
`jdih.setneg.go.id` JSON API, Thailand's `apig.law.go.th`. Use `urllib` for those. A browser earns
its place against exactly two secondary obstacles that nonetheless hold load-bearing answers:

1. **Cloudflare managed challenges on HTML routes.** `ratchakitcha.soc.go.th` — Thailand's Royal
   Gazette, the authoritative publication — answers `cf-mitigated: challenge` on its HTML app and
   search routes while serving `/documents/<id>.pdf` straight through. `peraturan.bpk.go.id`
   answers a country-keyed deny.
2. **Pages with no API behind them.** `www.bora.dopa.go.th` — the ThaID surface — answers 200 and
   renders client-side; its static HTML carries four links, and its rendered DOM carries 451.

**A browser will not help with a blocked socket.** `peraturan.go.id` black-holes the TCP SYN from
this egress, and every `kemendagri.go.id` host — the ministry that owns Indonesian civil
registration — is blocked outright. Those are network-level, and Chromium reaches them exactly as
well as curl does, which is to say not at all. The remedy there is a different egress, not a
different client. Pointing this module at one of those hosts wastes a browser launch and a timeout.

Two modes, because the two obstacles differ:

    fetch_document(url)   the bytes a resource actually serves        (the Gazette PDF)
    fetch_rendered(url)   the DOM after client-side scripts have run  (bora.dopa.go.th)

**This module refuses rather than returns when a host says no.** A challenge page, an interstitial
or a `cf-mitigated` response is detected and raised as `BrowserRefusedError`, never handed back as
content. Phase 0's worst finding was an extraction that looked fine and had silently lost four
articles; "Just a moment..." stored as law is that same failure wearing a different hat, and it is
29 KB of plausible HTML that no completeness check over an unknown structure would catch.

**And it does not defeat access controls.** Ordinary browser, ordinary user agent, ordinary
behaviour, rate-limited by default. No CAPTCHA or Turnstile solving, no stealth patches, no user
agent or proxy rotation, no loop that waits out a challenge. Where a site has said no, the
supported outcome is a refusal naming the host and telling the caller to retrieve the document by
hand. Verified 2026-09-16: the Gazette challenges a real headless Chromium exactly as it challenges
curl, and that is a finding rather than an obstacle to route around.

Where a source grants automated access only within a window — Singapore's SSO terms clause (13)(d)
permits extraction between 3 a.m. and 7 a.m. Singapore Time — declare it with `AccessWindow` and
the fetcher refuses outside it, before the browser starts. See `SSO_AUTOMATION_WINDOW`.

Playwright is an optional dependency: `pip install 'lawcorpus[browser]'`, then
`playwright install chromium`. The rest of the toolkit works without it (this.i @2sc5rmg4).

Design decisions: this.i @lkm7beuo, @2sc5rmg4, @5bo2uarc, @v2xlormp, @rl2fgk3p, @asbhej3z.
"""

from __future__ import annotations

import hashlib
import importlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..errors import LawcorpusError

MODE_DOCUMENT = "document"
MODE_RENDERED = "rendered"

# A real browser's own user agent is used by default (None = whatever the browser sends). This
# constant exists for callers who want to identify the project; it is not a disguise.
USER_AGENT = None

DEFAULT_TIMEOUT_MS = 45_000
DEFAULT_MIN_INTERVAL = 2.0
DEFAULT_WAIT_UNTIL = "domcontentloaded"
DEFAULT_SETTLE_MS = 2_000

# How much of a body is scanned for interstitial markers. A challenge page is small and its
# markers are in the first few KB; scanning a 50 MB PDF for them would cost more than the fetch.
_SCAN_LIMIT = 65_536

_CHALLENGE_MARKERS = (
    "just a moment...",
    "challenges.cloudflare.com",
    "cf_chl_opt",
    "__cf_chl",
    "checking your browser",
    "performing security verification",
    "enable javascript and cookies to continue",
)
# Only consulted on a failing status: "access denied" is ordinary English that appears in real
# statutory text about records, and a served page containing it is not evidence of a refusal.
_DENY_MARKERS = (
    "access denied",
    "akses ditolak",
    "attention required! | cloudflare",
    "you have been blocked",
    "error 1020",
)

_TEXTUAL_HINTS = ("text/", "html", "xml", "json", "javascript")


class BrowserError(LawcorpusError):
    """A browser fetch that did not come back usable, and will not on a second attempt.

    `env`, because the obstacle is a system we depend on — the browser and what it reaches —
    failing to deliver: a browser that will not start, a navigation that reports no response, a
    status that is not 200 and is not a challenge, or a 200 with an empty body. Final; the
    retryable half of the same family is `BrowserTransientError`, and `e.env.browser.` gathers
    both (this.i @sqxhmdkt, @3tkymxtr).
    """

    code = "e.env.browser.f"


class BrowserTransientError(BrowserError):
    """The retrieval did not complete, and the same request may succeed later.

    A timeout, a dropped connection, a dead browser process, or a source answering 5xx. Separate
    from its parent only in the disposition, which is the one thing a caller reacts to
    differently — and the parent stays final so that a subclass which forgets to declare a code
    inherits the fail-closed answer.
    """

    code = "e.env.browser.r"


class BrowserConfigError(BrowserError):
    """The fetcher, a URL, or an access window was declared wrong. Nothing was fetched.

    `input`, because every one of these is decidable by inspecting the arguments alone, with no
    lookup — the standard's own boundary between `input` and everything else. The bare registered
    code rather than a leaf of our own: nobody diagnoses "a bad argument to a browser fetcher"
    separately from any other malformed argument.
    """

    code = "e.input.format.f"


class BrowserUnavailableError(BrowserError):
    """No browser to drive: the optional extra is missing, or its binaries are not installed.

    `self.config`, not `feature.unsupported`: the capability ships, and the reason we cannot use
    it is our own installation rather than the world's. The message names the command that fixes
    it, which is what makes the locus the useful thing to say (this.i @2sc5rmg4).
    """

    code = "e.self.config.browser.f"


class BrowserRefusedError(BrowserError):
    """The host refused programmatic access. Retrieve the document by hand.

    This is a supported outcome, not a defect to engineer around. It carries the provenance and
    the refused body so a caller can record what happened and diagnose it.

    `party`, because agency is the test the standard sets between an actor and a machine: a host
    serving a challenge or a deny page chose. Final, and that matters — @v2xlormp forbids a loop
    that waits a challenge out, so an `r` here would advertise the behaviour this module refuses.
    """

    code = "e.party.refused.f"

    def __init__(self, message: str, *, provenance=None, body: bytes = b"", transient: bool = None):
        self.provenance = provenance
        self.body = body
        super().__init__(message, transient=transient)


class WindowClosedError(BrowserError):
    """It is outside the hours this source permits automated access. Retry inside the window.

    `rule` — "a norm we enforce, neither authority nor verification" — because nobody's
    credential is being evaluated here: we are holding ourselves to a source's own term
    (@asbhej3z). Retryable, because the window reopens, which is the whole contrast with the
    refusal above.
    """

    code = "e.rule.access.window.r"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AccessWindow:
    """Hours during which a source permits automated access, in the source's own timezone.

    Singapore's SSO terms are the motivating case and not the only one: a window is the general
    shape of "you may automate, but only then". Hours are local wall-clock, the start is inside
    and the end is outside (03:00–07:00 means a fetch at 06:59 is permitted and one at 07:00 is
    not), and a window whose start is later than its end wraps past midnight.
    """

    start_hour: int
    end_hour: int
    tz: str
    source: str = ""

    def __post_init__(self):
        for name, value, top in (
            ("start_hour", self.start_hour, 23),
            ("end_hour", self.end_hour, 24),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise BrowserConfigError(
                    f"The {name} is {value!r}, which is not a whole number of hours. Give a local "
                    f"wall-clock hour, such as 3 for 3 a.m."
                )
            if not 0 <= value <= top:
                raise BrowserConfigError(
                    f"The {name} is {value}, which is not an hour of the day. Give a number "
                    f"between 0 and {top}."
                )
        if self.start_hour == self.end_hour:
            raise BrowserConfigError(
                f"The window starts and ends at {self.start_hour}, which is either no time at all "
                f"or every hour of the day. Say which — use (0, 24) for always-open."
            )
        if not str(self.source).strip():
            raise BrowserConfigError(
                "The window has no source. Name the term that grants the access — 'SSO terms "
                "clause (13)(d)' — so a reader can check the permission rather than take our "
                "word for it."
            )
        try:
            zone = ZoneInfo(self.tz)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise BrowserConfigError(
                f"'{self.tz}' is not a timezone this machine knows: {e}. Use an IANA name such as "
                f"'Asia/Singapore'. On a system without a tz database, install `tzdata`."
            ) from e
        object.__setattr__(self, "_zone", zone)

    @property
    def zone(self) -> ZoneInfo:
        return self.__dict__["_zone"]

    def contains(self, moment: datetime = None) -> bool:
        """Is `moment` (default: now) inside the window?"""
        moment = moment or _utc_now()
        if moment.tzinfo is None:
            raise BrowserConfigError(
                "The moment given has no time zone, so it cannot be compared against a window in "
                f"{self.tz}. Pass an aware datetime — datetime.now(timezone.utc)."
            )
        hour = moment.astimezone(self.zone).hour
        if self.start_hour < self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour

    def check(self, moment: datetime = None) -> None:
        """Refuse unless `moment` is inside the window."""
        moment = moment or _utc_now()
        if self.contains(moment):
            return None
        local = moment.astimezone(self.zone)
        raise WindowClosedError(
            f"This source permits automated access only {self.describe()}, and it is "
            f"{local:%H:%M} there now. Run the harvest inside the window; the same request will "
            f"succeed then."
        )

    def describe(self) -> str:
        return f"{self.start_hour:02d}:00–{self.end_hour:02d}:00 {self.tz} ({self.source})"


# Singapore Statutes Online grants reproduction rights at clause (13), and (13)(d) expressly
# contemplates automated extraction between 3 a.m. and 7 a.m. Singapore Time (strategy §8.2).
# The permission is revocable and clause (19) prohibits caching, so the corpus repo still owes
# its own licence reasoning — this constant enforces only the hours.
SSO_AUTOMATION_WINDOW = AccessWindow(
    3, 7, "Asia/Singapore", source="Singapore Statutes Online terms clause (13)(d)"
)


@dataclass(frozen=True)
class RawResponse:
    """What a browser saw: the wire facts, before any judgement about them."""

    status: int
    headers: dict
    body: bytes
    url: str


@dataclass(frozen=True)
class FetchProvenance:
    """The provenance a manifest row needs, captured through a browser.

    `sha256` covers what was actually retrieved, which differs by mode and the difference
    matters: in document mode it is the bytes the server sent, and in rendered mode it is the
    serialised DOM *after* client-side scripts ran, which no refetch reproduces byte for byte.
    Anything load-bearing should be quoted from a document-mode fetch where one exists
    (this.i @rl2fgk3p).
    """

    url: str
    final_url: str
    status: int
    media_type: str
    bytes: int
    sha256: str
    retrieved: str
    mode: str

    def manifest_fields(self) -> dict:
        """The subset of `manifest.COLUMNS` a fetch can fill in by itself.

        `source_url` is the URL that actually served the bytes, not the one asked for — a
        redirect target is what a reader needs to refetch.
        """
        return {
            "source_url": self.final_url,
            "retrieved": self.retrieved,
            "media_type": self.media_type,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class BrowserDocument:
    """One retrieved body with its provenance."""

    body: bytes
    provenance: FetchProvenance

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def _lower_headers(headers) -> dict:
    return {str(k).lower(): v for k, v in dict(headers or {}).items()}


def _scannable(headers: dict, body: bytes) -> str:
    """The head of `body` as lowercase text, or "" when it is not worth scanning."""
    content_type = str(headers.get("content-type", "")).lower()
    looks_textual = any(hint in content_type for hint in _TEXTUAL_HINTS)
    head = body[:_SCAN_LIMIT]
    if not looks_textual and head.lstrip()[:1] != b"<":
        return ""
    return head.decode("utf-8", "replace").lower()


def detect_refusal(*, status: int, headers, body: bytes) -> str:
    """Name the way this response refuses automated access, or return None if it does not.

    Detection is deliberately conservative about *denials* and liberal about *challenges*: a
    challenge interstitial is sometimes served with status 200, so its markers count at any
    status, while "access denied" is ordinary English and counts only on a failing status.

    A plain 403 with no markers returns None. It is still a failed fetch — the caller raises on
    the status — but calling it a refusal of automation would be a guess, and the remedy for a
    guess is different from the remedy for evidence.
    """
    headers = _lower_headers(headers)
    mitigated = str(headers.get("cf-mitigated", "")).strip()
    if mitigated:
        return f"a Cloudflare managed challenge (cf-mitigated: {mitigated})"

    text = _scannable(headers, body)
    if not text:
        return None
    for marker in _CHALLENGE_MARKERS:
        if marker in text:
            return f"a bot challenge interstitial (the body contains '{marker}')"
    if status >= 400:
        for marker in _DENY_MARKERS:
            if marker in text:
                return f"an access denial page (the body contains '{marker}')"
    return None


def load_sync_playwright(importer=importlib.import_module):
    """Return `playwright.sync_api.sync_playwright`, or say how to install it."""
    try:
        module = importer("playwright.sync_api")
    except ImportError as e:
        raise BrowserUnavailableError(
            "Playwright is not installed, so there is no browser to drive. It is an optional "
            "extra because most corpus work needs no browser: install it with "
            "`pip install 'lawcorpus[browser]'`, then fetch the browser binaries with "
            f"`playwright install chromium`. ({e})"
        ) from e
    return module.sync_playwright


class PlaywrightSession:
    """One browser and one context, driven through Playwright's sync API.

    The `sync_playwright` factory is injected rather than imported here, so this adapter is
    testable on a machine without the extra — which is every machine that runs the coverage gate.
    """

    def __init__(
        self,
        sync_playwright=None,
        *,
        browser: str = "chromium",
        headless: bool = True,
        user_agent=USER_AGENT,
        locale: str = "en-US",
    ):
        sync_playwright = sync_playwright or load_sync_playwright()
        self._playwright = sync_playwright().start()
        browser_type = getattr(self._playwright, str(browser), None)
        if browser_type is None:
            self._playwright.stop()
            raise BrowserConfigError(
                f"'{browser}' is not a browser Playwright drives. Use 'chromium', 'firefox' or "
                f"'webkit'."
            )
        try:
            self._browser = browser_type.launch(headless=headless)
        except Exception as e:
            self._playwright.stop()
            if "Executable doesn't exist" in str(e):
                raise BrowserUnavailableError(
                    f"Playwright is installed but the {browser} binary is not: run "
                    f"`playwright install {browser}`. ({e})"
                ) from e
            raise BrowserError(f"The {browser} browser would not start: {e}") from e
        context_args = {"locale": locale}
        if user_agent:
            context_args["user_agent"] = user_agent
        self._context = self._browser.new_context(**context_args)
        self._closed = False

    def fetch_document(self, url: str, *, timeout_ms: int) -> RawResponse:
        """Retrieve a resource's bytes through the browser context, without rendering it.

        The request carries the context's cookies and the browser's own TLS and header
        fingerprint — which is what gets a PDF through a host that challenges its HTML routes —
        but nothing is executed, so a PDF does not turn into a download the page API cannot read.
        """
        response = self._context.request.get(url, timeout=timeout_ms)
        return RawResponse(
            status=response.status,
            headers=_lower_headers(response.headers),
            body=response.body(),
            url=response.url,
        )

    def fetch_rendered(
        self, url: str, *, timeout_ms: int, wait_until: str, wait_for_selector, settle_ms: int
    ) -> RawResponse:
        """Navigate, let the page's own scripts run, and return the serialised DOM."""
        page = self._context.new_page()
        try:
            response = page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            if response is None:
                raise BrowserError(
                    f"Navigating to {url} produced no response — the browser neither loaded a "
                    f"document nor reported a status, so there is nothing to record provenance "
                    f"from. This usually means the navigation was aborted or served from a "
                    f"download."
                )
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
            if settle_ms:
                page.wait_for_timeout(settle_ms)
            return RawResponse(
                status=response.status,
                headers=_lower_headers(response.headers),
                body=page.content().encode("utf-8"),
                url=page.url,
            )
        finally:
            page.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._browser.close()
        self._playwright.stop()


class BrowserFetcher:
    """Retrieve URLs through a real browser, with manifestable provenance.

    `session_factory` is injected so the fetcher can be tested without a browser. It takes no
    arguments and returns something with `fetch_document`, `fetch_rendered` and `close`.
    """

    def __init__(
        self,
        session_factory=None,
        *,
        browser: str = "chromium",
        headless: bool = True,
        user_agent=USER_AGENT,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        access_window: AccessWindow = None,
        clock=time.monotonic,
        sleeper=time.sleep,
        now=_utc_now,
    ):
        try:
            min_interval = float(min_interval)
        except (TypeError, ValueError) as e:
            raise BrowserConfigError(
                f"The min_interval is {min_interval!r}, which is not a number of seconds."
            ) from e
        if min_interval < 0:
            raise BrowserConfigError(
                f"The min_interval is {min_interval}, but a delay between requests cannot be "
                f"negative. Use 0 to disable rate limiting — deliberately, and not against a "
                f"government host."
            )
        self.min_interval = min_interval
        self.timeout_ms = int(timeout_ms)
        self.access_window = access_window
        self._factory = session_factory or (
            lambda: PlaywrightSession(
                browser=browser, headless=headless, user_agent=user_agent
            )
        )
        self._clock = clock
        self._sleeper = sleeper
        self._now = now
        self._session = None
        self._last_fetch = None

    def __enter__(self) -> "BrowserFetcher":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        if self._session is None:
            return
        self._session.close()
        self._session = None

    def fetch_document(self, url: str) -> BrowserDocument:
        """Retrieve the bytes a resource serves, without rendering it."""
        url = self._check_url(url)
        session = self._begin()
        raw = self._call(lambda: session.fetch_document(url, timeout_ms=self.timeout_ms), url)
        return self._judge(url, raw, MODE_DOCUMENT)

    def fetch_rendered(
        self,
        url: str,
        *,
        wait_until: str = DEFAULT_WAIT_UNTIL,
        wait_for_selector=None,
        settle_ms: int = DEFAULT_SETTLE_MS,
    ) -> BrowserDocument:
        """Retrieve a page's DOM after its own scripts have run."""
        url = self._check_url(url)
        session = self._begin()
        raw = self._call(
            lambda: session.fetch_rendered(
                url,
                timeout_ms=self.timeout_ms,
                wait_until=wait_until,
                wait_for_selector=wait_for_selector,
                settle_ms=settle_ms,
            ),
            url,
        )
        return self._judge(url, raw, MODE_RENDERED)

    def _check_url(self, url) -> str:
        text = ("" if url is None else str(url)).strip()
        if not text:
            raise BrowserConfigError("No URL was given, so there is nothing to fetch.")
        if not text.startswith(("http://", "https://")):
            raise BrowserConfigError(
                f"'{text[:60]}' is not an http(s) URL. This fetcher drives a browser at remote "
                f"hosts; read local files directly instead."
            )
        return text

    def _begin(self):
        """Check the access window, wait our turn, and hand back a live session."""
        if self.access_window is not None:
            self.access_window.check(self._now())
        self._wait_turn()
        if self._session is None:
            self._session = self._factory()
        return self._session

    def _wait_turn(self) -> None:
        now = self._clock()
        if self._last_fetch is not None:
            waited = now - self._last_fetch
            if waited < self.min_interval:
                self._sleeper(self.min_interval - waited)
        self._last_fetch = self._clock()

    @staticmethod
    def _call(action, url):
        try:
            return action()
        except LawcorpusError:
            raise
        except Exception as e:
            raise BrowserTransientError(
                f"The browser did not complete the request to {url}: {e}. This is usually a "
                f"network, timeout or browser-process problem rather than a rejection — but note "
                f"that a host which black-holes the connection (peraturan.go.id, every "
                f"kemendagri.go.id host) looks exactly like this, and no browser will fix that."
            ) from e

    def _judge(self, url: str, raw: RawResponse, mode: str) -> BrowserDocument:
        """Turn a raw response into a document, or refuse it. Nothing else returns content."""
        provenance = FetchProvenance(
            url=url,
            final_url=raw.url or url,
            status=raw.status,
            media_type=str(raw.headers.get("content-type", "")).strip(),
            bytes=len(raw.body),
            sha256=hashlib.sha256(raw.body).hexdigest(),
            retrieved=self._now().date().isoformat(),
            mode=mode,
        )
        reason = detect_refusal(status=raw.status, headers=raw.headers, body=raw.body)
        if reason:
            raise BrowserRefusedError(
                f"{provenance.final_url} answered with {reason}, so this is not the document — it "
                f"is the host refusing automated access. Storing it would put an interstitial in "
                f"the corpus that reads like law. Retrieve this one by hand, or find a route that "
                f"is served: the Royal Gazette challenges its HTML routes and serves "
                f"/documents/<id>.pdf. Solving the challenge is not a supported option.",
                provenance=provenance,
                body=raw.body,
            )
        if raw.status >= 500:
            raise BrowserTransientError(
                f"{provenance.final_url} answered {raw.status}. The service is failing or "
                f"overloaded, not rejecting the request."
            )
        if raw.status != 200:
            raise BrowserError(
                f"{provenance.final_url} answered {raw.status}, and nothing in the response says "
                f"it is a bot challenge. Check the URL before assuming the host is blocking us."
            )
        if not raw.body:
            raise BrowserError(
                f"{provenance.final_url} answered 200 with an empty body. Treat this as a failed "
                f"retrieval — storing it would put a zero-byte entry in the corpus that reads "
                f"like a successful fetch."
            )
        return BrowserDocument(body=raw.body, provenance=provenance)
