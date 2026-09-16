"""The browser fetcher.

The browser is injected — every test here runs without playwright installed and without touching
the network, including the tests of the playwright adapter itself, which drives a fake standing in
for `playwright.sync_api`. That is deliberate: CI installs `.[dev]` and not `.[browser]`, so an
adapter tested only against the real library would be uncovered code on the machine that enforces
the coverage gate (this.i @2sc5rmg4).

The tests that really talk to Bangkok and Jakarta are marked `network` and deselected by default.
"""

import hashlib
from datetime import datetime, timezone

import pytest

from lawcorpus.fetch.browser import (
    MODE_DOCUMENT,
    MODE_RENDERED,
    SSO_AUTOMATION_WINDOW,
    AccessWindow,
    BrowserConfigError,
    BrowserError,
    BrowserFetcher,
    BrowserRefusedError,
    BrowserTransientError,
    BrowserUnavailableError,
    PlaywrightSession,
    RawResponse,
    WindowClosedError,
    detect_refusal,
    load_sync_playwright,
)

HTML = "text/html; charset=utf-8"

CHALLENGE_BODY = (
    b"<!DOCTYPE html><html lang=\"en-US\"><head><title>Just a moment...</title>"
    b"<script src=\"https://challenges.cloudflare.com/turnstile/v0/api.js\"></script></head>"
    b"<body>Performing security verification</body></html>"
)

DENY_BODY = (
    b"<html><head><title>Access Denied / Akses Ditolak</title></head><body>"
    b"<h1 id=\"title\">Access Denied</h1><p>Your access to this page has been denied by BPK-RI."
    b"</p><p>Country: US</p></body></html>"
)

GOOD_HTML = b"<html><head><title>UU 27/2022</title></head><body>Pasal 1</body></html>"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FakeSession:
    """Stands in for a browser. Records calls, replays canned responses."""

    def __init__(self, document=None, rendered=None):
        self.document = document or RawResponse(
            status=200, headers={"content-type": "application/pdf"}, body=b"%PDF-1.4 ...",
            url="https://example.gov/doc.pdf",
        )
        self.rendered = rendered or RawResponse(
            status=200, headers={"content-type": HTML}, body=GOOD_HTML,
            url="https://example.gov/page",
        )
        self.calls = []
        self.closed = 0

    def fetch_document(self, url, *, timeout_ms):
        self.calls.append(("document", url, timeout_ms))
        if isinstance(self.document, Exception):
            raise self.document
        return self.document

    def fetch_rendered(self, url, *, timeout_ms, wait_until, wait_for_selector, settle_ms):
        self.calls.append(("rendered", url, timeout_ms, wait_until, wait_for_selector, settle_ms))
        if isinstance(self.rendered, Exception):
            raise self.rendered
        return self.rendered

    def close(self):
        self.closed += 1


class Factory:
    """A session factory that hands out one FakeSession and counts how often it was asked."""

    def __init__(self, session=None):
        self.session = session or FakeSession()
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.session


def make_fetcher(session=None, **kwargs):
    factory = Factory(session)
    kwargs.setdefault("min_interval", 0)
    kwargs.setdefault("now", lambda: datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))
    return BrowserFetcher(session_factory=factory, **kwargs), factory


class TestTheCodesTheseErrorsCarry:
    """Classified by the obstacle, never by the module that raised it (this.i @sqxhmdkt).

    The grammar itself is checked package-wide in `test_error_codes.py`; what is pinned here is
    the classification, because that is the judgement a later reader is most likely to undo.
    """

    def test_a_host_that_challenges_us_is_an_actor_that_chose(self):
        assert BrowserRefusedError.code == "e.party.refused.f"

    def test_a_refusal_is_final_because_we_never_wait_a_challenge_out(self):
        assert BrowserRefusedError("no").transient is False  # this.i @v2xlormp

    def test_a_closed_window_is_a_norm_we_enforce_on_ourselves(self):
        assert WindowClosedError.code == "e.rule.access.window.r"

    def test_a_closed_window_is_retryable_because_the_window_reopens(self):
        assert WindowClosedError("not yet").transient is True

    def test_a_missing_browser_is_our_own_installation_not_a_capability_nobody_has(self):
        assert BrowserUnavailableError.code == "e.self.config.browser.f"

    def test_a_badly_declared_fetch_is_what_the_caller_sent(self):
        assert BrowserConfigError.code == "e.input.format.f"

    def test_the_browser_channel_carries_both_dispositions_under_one_prefix(self):
        assert BrowserError.code == "e.env.browser.f"
        assert BrowserTransientError.code == "e.env.browser.r"
        assert issubclass(BrowserTransientError, BrowserError)
        assert BrowserError.code.rsplit(".", 1)[0] == BrowserTransientError.code.rsplit(".", 1)[0]


class TestAccessWindow:
    """Singapore's SSO terms permit automated extraction only 3–7 a.m. SGT (strategy §8.2)."""

    def test_inside_a_simple_window(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        assert window.contains(datetime(2026, 9, 16, 20, 0, tzinfo=timezone.utc))  # 04:00 SGT

    def test_outside_a_simple_window(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        assert not window.contains(datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))  # 20:00 SGT

    def test_the_start_hour_is_inside(self):
        window = AccessWindow(3, 7, "UTC", source="a test")
        assert window.contains(datetime(2026, 9, 16, 3, 0, tzinfo=timezone.utc))

    def test_the_end_hour_is_outside(self):
        window = AccessWindow(3, 7, "UTC", source="a test")
        assert not window.contains(datetime(2026, 9, 16, 7, 0, tzinfo=timezone.utc))

    def test_a_window_that_wraps_past_midnight_holds_the_late_hours(self):
        window = AccessWindow(22, 4, "UTC", source="a test")
        assert window.contains(datetime(2026, 9, 16, 23, 0, tzinfo=timezone.utc))

    def test_a_window_that_wraps_past_midnight_holds_the_early_hours(self):
        window = AccessWindow(22, 4, "UTC", source="a test")
        assert window.contains(datetime(2026, 9, 16, 1, 0, tzinfo=timezone.utc))

    def test_a_window_that_wraps_past_midnight_excludes_the_middle(self):
        window = AccessWindow(22, 4, "UTC", source="a test")
        assert not window.contains(datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))

    def test_a_naive_moment_is_refused(self):
        window = AccessWindow(3, 7, "UTC", source="a test")
        with pytest.raises(BrowserConfigError) as e:
            window.contains(datetime(2026, 9, 16, 4, 0))
        assert "time zone" in str(e.value)

    def test_the_default_moment_is_now(self):
        hour = datetime.now(timezone.utc).hour
        window = AccessWindow(hour, (hour + 1) % 24, "UTC", source="a test")
        assert window.contains() is True

    def test_equal_hours_are_refused_as_ambiguous(self):
        with pytest.raises(BrowserConfigError) as e:
            AccessWindow(3, 3, "UTC", source="a test")
        assert "3" in str(e.value)

    def test_an_hour_out_of_range_is_refused(self):
        with pytest.raises(BrowserConfigError):
            AccessWindow(3, 25, "UTC", source="a test")

    def test_a_non_integer_hour_is_refused(self):
        with pytest.raises(BrowserConfigError):
            AccessWindow("dawn", 7, "UTC", source="a test")

    def test_an_unknown_timezone_is_refused(self):
        with pytest.raises(BrowserConfigError) as e:
            AccessWindow(3, 7, "Asia/Atlantis", source="a test")
        assert "Asia/Atlantis" in str(e.value)

    def test_a_source_is_required(self):
        with pytest.raises(BrowserConfigError) as e:
            AccessWindow(3, 7, "UTC", source="  ")
        assert "source" in str(e.value)

    def test_check_passes_inside_the_window(self):
        window = AccessWindow(3, 7, "UTC", source="a test")
        assert window.check(datetime(2026, 9, 16, 4, 0, tzinfo=timezone.utc)) is None

    def test_check_refuses_outside_the_window_and_names_the_source(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        with pytest.raises(WindowClosedError) as e:
            window.check(datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc))
        message = str(e.value)
        assert "SSO clause (13)(d)" in message
        assert "20:00" in message  # the local time it actually is
        assert e.value.transient is True  # the same request works at the right hour

    def test_describe_states_the_window_in_local_terms(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        assert window.describe() == "03:00–07:00 Asia/Singapore (SSO clause (13)(d))"

    def test_the_singapore_window_is_the_one_the_terms_grant(self):
        assert SSO_AUTOMATION_WINDOW.start_hour == 3
        assert SSO_AUTOMATION_WINDOW.end_hour == 7
        assert SSO_AUTOMATION_WINDOW.tz == "Asia/Singapore"
        assert "13" in SSO_AUTOMATION_WINDOW.source


class TestDetectRefusal:
    """A challenge page stored as law is Phase 0's silent-truncation failure in a new hat."""

    def test_the_cf_mitigated_header_is_conclusive(self):
        reason = detect_refusal(status=403, headers={"cf-mitigated": "challenge"}, body=b"")
        assert reason is not None
        assert "cf-mitigated" in reason

    def test_a_just_a_moment_interstitial_is_a_challenge(self):
        reason = detect_refusal(
            status=403, headers={"content-type": HTML}, body=CHALLENGE_BODY
        )
        assert "challenge" in reason.lower()

    def test_an_interstitial_served_with_status_200_is_still_a_challenge(self):
        reason = detect_refusal(status=200, headers={"content-type": HTML}, body=CHALLENGE_BODY)
        assert reason is not None

    def test_a_country_keyed_deny_is_named_as_a_denial_not_a_challenge(self):
        reason = detect_refusal(status=403, headers={"content-type": HTML}, body=DENY_BODY)
        assert "denied" in reason.lower()
        assert "challenge" not in reason.lower()

    def test_a_deny_phrase_inside_a_served_page_is_not_a_refusal(self):
        # "Access denied" is ordinary English and appears in real statutory text about records.
        body = b"<html><body>Where access is denied, the officer shall record the reason.</body></html>"
        assert detect_refusal(status=200, headers={"content-type": HTML}, body=body) is None

    def test_a_served_page_is_not_a_refusal(self):
        assert detect_refusal(status=200, headers={"content-type": HTML}, body=GOOD_HTML) is None

    def test_a_pdf_body_is_not_scanned_for_markers(self):
        body = b"%PDF-1.4\r" + b"Just a moment..." + b"\rstream"
        assert detect_refusal(
            status=200, headers={"content-type": "application/pdf"}, body=body
        ) is None

    def test_an_html_body_without_an_html_content_type_is_still_scanned(self):
        assert detect_refusal(status=403, headers={}, body=CHALLENGE_BODY) is not None

    def test_the_body_scan_is_bounded(self):
        body = b"<html>" + b"x" * 200_000 + b"Just a moment..."
        assert detect_refusal(status=403, headers={"content-type": HTML}, body=body) is None

    def test_headers_are_matched_case_insensitively(self):
        assert detect_refusal(status=403, headers={"CF-Mitigated": "challenge"}, body=b"") is not None

    def test_a_plain_403_with_no_markers_is_not_classified_as_a_refusal(self):
        # It is still a failure — the fetcher raises on the status — but it is not evidence
        # that the host refuses automation, and saying so would be a guess.
        assert detect_refusal(status=403, headers={}, body=b"nope") is None


class TestFetchDocument:
    def test_it_returns_the_bytes_and_the_provenance_a_manifest_row_needs(self):
        body = b"%PDF-1.4 the Royal Gazette"
        session = FakeSession(
            document=RawResponse(
                status=200,
                headers={"content-type": "application/pdf"},
                body=body,
                url="https://ratchakitcha.soc.go.th/documents/1517406.pdf",
            )
        )
        fetcher, _ = make_fetcher(session)
        doc = fetcher.fetch_document("https://ratchakitcha.soc.go.th/documents/1517406.pdf")
        assert doc.body == body
        p = doc.provenance
        assert p.status == 200
        assert p.media_type == "application/pdf"
        assert p.bytes == len(body)
        assert p.sha256 == _sha(body)
        assert p.mode == MODE_DOCUMENT
        assert p.retrieved == "2026-09-16"

    def test_the_final_url_after_a_redirect_is_what_is_recorded(self):
        session = FakeSession(
            document=RawResponse(
                status=200, headers={"content-type": "application/pdf"}, body=b"%PDF",
                url="https://host.example/final.pdf",
            )
        )
        fetcher, _ = make_fetcher(session)
        doc = fetcher.fetch_document("https://host.example/start")
        assert doc.provenance.url == "https://host.example/start"
        assert doc.provenance.final_url == "https://host.example/final.pdf"
        assert doc.provenance.manifest_fields()["source_url"] == "https://host.example/final.pdf"

    def test_manifest_fields_carry_exactly_the_provenance_columns(self):
        fetcher, _ = make_fetcher()
        fields = fetcher.fetch_document("https://example.gov/doc.pdf").provenance.manifest_fields()
        assert set(fields) == {"source_url", "retrieved", "media_type", "bytes", "sha256"}

    def test_a_challenge_is_refused_rather_than_returned(self):
        session = FakeSession(
            document=RawResponse(
                status=403,
                headers={"cf-mitigated": "challenge", "content-type": HTML},
                body=CHALLENGE_BODY,
                url="https://ratchakitcha.soc.go.th/",
            )
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserRefusedError) as e:
            fetcher.fetch_document("https://ratchakitcha.soc.go.th/")
        assert "by hand" in str(e.value)
        assert e.value.provenance.status == 403
        assert e.value.provenance.sha256 == _sha(CHALLENGE_BODY)
        assert e.value.transient is False

    def test_a_refusal_keeps_the_body_on_the_error_for_diagnosis(self):
        session = FakeSession(
            document=RawResponse(
                status=403, headers={"cf-mitigated": "challenge"}, body=CHALLENGE_BODY,
                url="https://ratchakitcha.soc.go.th/",
            )
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserRefusedError) as e:
            fetcher.fetch_document("https://ratchakitcha.soc.go.th/")
        assert b"Just a moment" in e.value.body

    def test_a_server_error_is_transient(self):
        session = FakeSession(
            document=RawResponse(status=503, headers={}, body=b"oops", url="https://x.example/")
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserTransientError) as e:
            fetcher.fetch_document("https://x.example/")
        assert e.value.transient is True

    def test_a_404_is_permanent(self):
        session = FakeSession(
            document=RawResponse(status=404, headers={}, body=b"nope", url="https://x.example/")
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserError) as e:
            fetcher.fetch_document("https://x.example/")
        assert e.value.transient is False

    def test_an_empty_200_is_refused_rather_than_stored(self):
        session = FakeSession(
            document=RawResponse(
                status=200, headers={"content-type": "application/pdf"}, body=b"",
                url="https://x.example/",
            )
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserError) as e:
            fetcher.fetch_document("https://x.example/")
        assert "zero-byte" in str(e.value)

    def test_a_browser_exception_becomes_a_transient_error(self):
        session = FakeSession(document=RuntimeError("net::ERR_CONNECTION_TIMED_OUT"))
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserTransientError) as e:
            fetcher.fetch_document("https://peraturan.go.id/")
        assert e.value.transient is True
        assert "ERR_CONNECTION_TIMED_OUT" in str(e.value)

    def test_a_lawcorpus_error_from_the_session_is_not_rewrapped(self):
        session = FakeSession(document=BrowserUnavailableError("no browser"))
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserUnavailableError):
            fetcher.fetch_document("https://x.example/")

    def test_an_empty_url_is_refused_before_a_browser_starts(self):
        fetcher, factory = make_fetcher()
        with pytest.raises(BrowserConfigError):
            fetcher.fetch_document("   ")
        assert factory.calls == 0

    def test_a_non_http_url_is_refused(self):
        fetcher, factory = make_fetcher()
        with pytest.raises(BrowserConfigError) as e:
            fetcher.fetch_document("file:///etc/passwd")
        assert "http" in str(e.value)
        assert factory.calls == 0


class TestFetchRendered:
    def test_it_returns_the_dom_after_client_side_rendering(self):
        dom = b"<html><body>ThaID</body></html>"
        session = FakeSession(
            rendered=RawResponse(
                status=200, headers={"content-type": HTML}, body=dom,
                url="https://www.bora.dopa.go.th/home/",
            )
        )
        fetcher, _ = make_fetcher(session)
        doc = fetcher.fetch_rendered("https://www.bora.dopa.go.th/home/")
        assert doc.body == dom
        assert doc.text == dom.decode()
        assert doc.provenance.mode == MODE_RENDERED
        assert doc.provenance.sha256 == _sha(dom)

    def test_the_wait_conditions_reach_the_browser(self):
        fetcher, factory = make_fetcher(timeout_ms=1234)
        fetcher.fetch_rendered(
            "https://example.gov/page", wait_for_selector="#content", settle_ms=250,
            wait_until="load",
        )
        call = factory.session.calls[0]
        assert call[0] == "rendered"
        assert call[2] == 1234
        assert call[3] == "load"
        assert call[4] == "#content"
        assert call[5] == 250

    def test_a_challenge_in_the_rendered_dom_is_refused(self):
        session = FakeSession(
            rendered=RawResponse(
                status=403, headers={"cf-mitigated": "challenge"}, body=CHALLENGE_BODY,
                url="https://ratchakitcha.soc.go.th/",
            )
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserRefusedError):
            fetcher.fetch_rendered("https://ratchakitcha.soc.go.th/")

    def test_an_empty_dom_is_refused(self):
        session = FakeSession(
            rendered=RawResponse(status=200, headers={"content-type": HTML}, body=b"",
                                 url="https://x.example/")
        )
        fetcher, _ = make_fetcher(session)
        with pytest.raises(BrowserError):
            fetcher.fetch_rendered("https://x.example/")


class TestPoliteness:
    def test_the_first_fetch_does_not_wait(self):
        slept = []
        ticks = iter([100.0, 100.0, 100.0])
        fetcher, _ = make_fetcher(
            min_interval=2.0, sleeper=slept.append, clock=lambda: next(ticks)
        )
        fetcher.fetch_document("https://x.example/a")
        assert slept == []

    def test_a_second_fetch_waits_out_the_interval(self):
        slept = []
        ticks = iter([100.0, 100.0, 100.5, 102.5])
        fetcher, _ = make_fetcher(
            min_interval=2.0, sleeper=slept.append, clock=lambda: next(ticks)
        )
        fetcher.fetch_document("https://x.example/a")
        fetcher.fetch_document("https://x.example/b")
        assert slept == [pytest.approx(1.5)]

    def test_a_fetch_after_the_interval_has_passed_does_not_wait(self):
        slept = []
        ticks = iter([100.0, 100.0, 110.0, 110.0])
        fetcher, _ = make_fetcher(
            min_interval=2.0, sleeper=slept.append, clock=lambda: next(ticks)
        )
        fetcher.fetch_document("https://x.example/a")
        fetcher.fetch_document("https://x.example/b")
        assert slept == []

    def test_a_negative_interval_is_refused(self):
        with pytest.raises(BrowserConfigError):
            BrowserFetcher(session_factory=Factory(), min_interval=-1)

    def test_an_interval_that_is_not_a_number_is_refused(self):
        with pytest.raises(BrowserConfigError) as e:
            BrowserFetcher(session_factory=Factory(), min_interval="slowly")
        assert "seconds" in str(e.value)

    def test_the_default_interval_is_polite(self):
        assert BrowserFetcher(session_factory=Factory()).min_interval >= 1.0


class TestAccessWindowEnforcement:
    def test_a_closed_window_refuses_before_the_browser_starts(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        fetcher, factory = make_fetcher(access_window=window)  # frozen at 20:00 SGT
        with pytest.raises(WindowClosedError):
            fetcher.fetch_document("https://sso.agc.gov.sg/Act/ETA2010?ViewType=Pdf")
        assert factory.calls == 0

    def test_an_open_window_lets_the_fetch_through(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        fetcher, factory = make_fetcher(
            access_window=window,
            now=lambda: datetime(2026, 9, 16, 20, 0, tzinfo=timezone.utc),  # 04:00 SGT
        )
        fetcher.fetch_document("https://sso.agc.gov.sg/Act/ETA2010?ViewType=Pdf")
        assert factory.calls == 1

    def test_the_window_also_guards_rendered_fetches(self):
        window = AccessWindow(3, 7, "Asia/Singapore", source="SSO clause (13)(d)")
        fetcher, factory = make_fetcher(access_window=window)
        with pytest.raises(WindowClosedError):
            fetcher.fetch_rendered("https://sso.agc.gov.sg/Act/ETA2010")
        assert factory.calls == 0


class TestSessionLifecycle:
    def test_one_browser_serves_many_fetches(self):
        fetcher, factory = make_fetcher()
        fetcher.fetch_document("https://x.example/a")
        fetcher.fetch_document("https://x.example/b")
        assert factory.calls == 1

    def test_close_closes_the_browser(self):
        fetcher, factory = make_fetcher()
        fetcher.fetch_document("https://x.example/a")
        fetcher.close()
        assert factory.session.closed == 1

    def test_close_without_a_browser_is_a_no_op(self):
        fetcher, factory = make_fetcher()
        fetcher.close()
        assert factory.session.closed == 0

    def test_close_is_idempotent(self):
        fetcher, factory = make_fetcher()
        fetcher.fetch_document("https://x.example/a")
        fetcher.close()
        fetcher.close()
        assert factory.session.closed == 1

    def test_it_works_as_a_context_manager(self):
        factory = Factory()
        with BrowserFetcher(session_factory=factory, min_interval=0) as fetcher:
            fetcher.fetch_document("https://x.example/a")
        assert factory.session.closed == 1


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"ok", url="https://x.example/"):
        self.status = status
        self.headers = headers or {"Content-Type": "text/html"}
        self._body = body
        self.url = url

    def body(self):
        return self._body


class FakePage:
    def __init__(self, response, content=b"<html>rendered</html>", url=None):
        self._response = response
        self._content = content
        self.url = url or (response.url if response else "https://x.example/")
        self.waits = []
        self.closed = False

    def goto(self, url, *, wait_until, timeout):
        self.waits.append(("goto", url, wait_until, timeout))
        return self._response

    def wait_for_selector(self, selector, *, timeout):
        self.waits.append(("selector", selector, timeout))

    def wait_for_timeout(self, ms):
        self.waits.append(("settle", ms))

    def content(self):
        return self._content.decode()

    def close(self):
        self.closed = True


class FakeRequestContext:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FakeContext:
    def __init__(self, doc_response, page):
        self.request = FakeRequestContext(doc_response)
        self._page = page
        self.kwargs = None

    def new_page(self):
        return self._page


class FakeBrowser:
    def __init__(self, context):
        self._context = context
        self.closed = False

    def new_context(self, **kwargs):
        self._context.kwargs = kwargs
        return self._context

    def close(self):
        self.closed = True


class FakeBrowserType:
    def __init__(self, browser, error=None):
        self._browser = browser
        self._error = error
        self.launch_kwargs = None

    def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        if self._error:
            raise self._error
        return self._browser


class FakePlaywright:
    def __init__(self, browser_type):
        self.chromium = browser_type
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeSyncPlaywright:
    """What `playwright.sync_api.sync_playwright` returns: a context manager with `.start()`."""

    def __init__(self, playwright):
        self._playwright = playwright

    def start(self):
        return self._playwright


def make_playwright(doc_response=None, page=None, launch_error=None):
    page = page or FakePage(FakeResponse())
    context = FakeContext(doc_response or FakeResponse(), page)
    browser = FakeBrowser(context)
    btype = FakeBrowserType(browser, error=launch_error)
    pw = FakePlaywright(btype)
    return (lambda: FakeSyncPlaywright(pw)), pw, browser, context, page


class TestLoadSyncPlaywright:
    def test_it_returns_the_factory_when_the_extra_is_installed(self):
        sentinel = object()

        class Module:
            sync_playwright = sentinel

        assert load_sync_playwright(importer=lambda name: Module) is sentinel

    def test_a_missing_extra_names_the_install_command(self):
        def importer(name):
            raise ImportError(f"No module named {name!r}")

        with pytest.raises(BrowserUnavailableError) as e:
            load_sync_playwright(importer=importer)
        message = str(e.value)
        assert "lawcorpus[browser]" in message
        assert "playwright install" in message
        assert e.value.transient is False

    def test_the_default_importer_is_the_real_one(self):
        # Without the extra this raises; with it, it returns a callable. Either outcome proves
        # the default importer was consulted rather than a stub.
        try:
            assert callable(load_sync_playwright())
        except BrowserUnavailableError as e:
            assert "lawcorpus[browser]" in str(e)


class TestPlaywrightSession:
    def test_it_launches_the_named_browser_with_the_given_user_agent(self):
        factory, pw, browser, context, page = make_playwright()
        session = PlaywrightSession(factory, browser="chromium", user_agent="ua/1")
        assert pw.chromium.launch_kwargs == {"headless": True}
        assert context.kwargs["user_agent"] == "ua/1"
        session.close()
        assert browser.closed is True
        assert pw.stopped is True

    def test_headful_is_passed_through(self):
        factory, pw, _, _, _ = make_playwright()
        PlaywrightSession(factory, headless=False)
        assert pw.chromium.launch_kwargs == {"headless": False}

    def test_an_unknown_browser_name_is_a_config_error(self):
        factory, _, _, _, _ = make_playwright()
        with pytest.raises(BrowserConfigError) as e:
            PlaywrightSession(factory, browser="lynx")
        assert "lynx" in str(e.value)

    def test_a_missing_browser_binary_says_how_to_install_it(self):
        error = RuntimeError(
            "BrowserType.launch: Executable doesn't exist at /home/x/.cache/ms-playwright/..."
        )
        factory, _, _, _, _ = make_playwright(launch_error=error)
        with pytest.raises(BrowserUnavailableError) as e:
            PlaywrightSession(factory)
        assert "playwright install" in str(e.value)

    def test_any_other_launch_failure_is_reported_as_it_came(self):
        factory, _, _, _, _ = make_playwright(launch_error=RuntimeError("cgroup denied"))
        with pytest.raises(BrowserError) as e:
            PlaywrightSession(factory)
        assert "cgroup denied" in str(e.value)

    def test_document_mode_returns_status_headers_and_bytes(self):
        response = FakeResponse(
            status=200, headers={"Content-Type": "application/pdf"}, body=b"%PDF",
            url="https://x.example/final.pdf",
        )
        factory, _, _, context, _ = make_playwright(doc_response=response)
        session = PlaywrightSession(factory)
        raw = session.fetch_document("https://x.example/start", timeout_ms=1000)
        assert raw == RawResponse(
            status=200, headers={"content-type": "application/pdf"}, body=b"%PDF",
            url="https://x.example/final.pdf",
        )
        assert context.request.calls == [("https://x.example/start", 1000)]

    def test_rendered_mode_returns_the_serialised_dom(self):
        page = FakePage(
            FakeResponse(status=200, headers={"Content-Type": "text/html"}),
            content=b"<html>ThaID</html>",
            url="https://www.bora.dopa.go.th/home/",
        )
        factory, _, _, _, _ = make_playwright(page=page)
        session = PlaywrightSession(factory)
        raw = session.fetch_rendered(
            "https://www.bora.dopa.go.th/", timeout_ms=9000, wait_until="domcontentloaded",
            wait_for_selector=None, settle_ms=0,
        )
        assert raw.body == b"<html>ThaID</html>"
        assert raw.url == "https://www.bora.dopa.go.th/home/"  # after client-side redirect
        assert raw.status == 200
        assert page.closed is True

    def test_rendered_mode_honours_a_selector_and_a_settle_delay(self):
        page = FakePage(FakeResponse())
        factory, _, _, _, _ = make_playwright(page=page)
        session = PlaywrightSession(factory)
        session.fetch_rendered(
            "https://x.example/", timeout_ms=5000, wait_until="load",
            wait_for_selector="#main", settle_ms=300,
        )
        assert ("selector", "#main", 5000) in page.waits
        assert ("settle", 300) in page.waits

    def test_a_navigation_that_yields_no_response_is_an_error(self):
        page = FakePage(None)
        factory, _, _, _, _ = make_playwright(page=page)
        session = PlaywrightSession(factory)
        with pytest.raises(BrowserError) as e:
            session.fetch_rendered(
                "https://x.example/", timeout_ms=5000, wait_until="load",
                wait_for_selector=None, settle_ms=0,
            )
        assert "no response" in str(e.value)
        assert page.closed is True  # the page is closed even on the failing path

    def test_the_page_is_closed_when_navigation_raises(self):
        class Exploding(FakePage):
            def goto(self, url, *, wait_until, timeout):
                raise RuntimeError("net::ERR_ABORTED")

        page = Exploding(FakeResponse())
        factory, _, _, _, _ = make_playwright(page=page)
        session = PlaywrightSession(factory)
        with pytest.raises(RuntimeError):
            session.fetch_rendered(
                "https://x.example/", timeout_ms=5000, wait_until="load",
                wait_for_selector=None, settle_ms=0,
            )
        assert page.closed is True

    def test_close_is_idempotent(self):
        factory, pw, browser, _, _ = make_playwright()
        session = PlaywrightSession(factory)
        session.close()
        session.close()
        assert browser.closed is True


class TestDefaultSessionFactory:
    def test_a_fetcher_with_no_factory_builds_a_playwright_session(self, monkeypatch):
        factory, _, _, _, _ = make_playwright()
        monkeypatch.setattr(
            "lawcorpus.fetch.browser.load_sync_playwright", lambda: factory
        )
        fetcher = BrowserFetcher(min_interval=0)
        doc = fetcher.fetch_document("https://x.example/")
        assert doc.body == b"ok"
        fetcher.close()


@pytest.fixture(scope="module")
def live_fetcher():
    # Skipping here is safe only because these tests are network-marked and deselected by
    # default: every line of the module is covered by the mocked tests above, so a machine
    # without the extra still meets the coverage gate rather than quietly falling under it.
    pytest.importorskip("playwright", reason="the live canaries need `pip install .[browser]`")
    with BrowserFetcher(min_interval=2.0, timeout_ms=60000) as f:
        yield f


@pytest.mark.network
class TestLiveEndpoints:
    """Canaries against the real Phase 0 targets. Deselected by default; they need `.[browser]`.

    These assert the *shape* of what each host does, so a change of posture — the Gazette
    dropping its challenge, or raising one on the document path — shows up as a failure.
    """

    def test_the_royal_gazette_serves_document_bytes(self, live_fetcher):
        doc = live_fetcher.fetch_document("https://ratchakitcha.soc.go.th/documents/1517406.pdf")
        assert doc.body.startswith(b"%PDF")
        assert doc.provenance.media_type.startswith("application/pdf")
        assert doc.provenance.bytes > 100_000

    def test_the_royal_gazette_html_routes_still_refuse_automation(self, live_fetcher):
        with pytest.raises(BrowserRefusedError) as e:
            live_fetcher.fetch_rendered("https://ratchakitcha.soc.go.th/")
        assert "challenge" in str(e.value).lower()

    def test_bora_renders_client_side_and_names_thaid(self, live_fetcher):
        doc = live_fetcher.fetch_rendered("https://www.bora.dopa.go.th/home/", settle_ms=4000)
        assert len(doc.body) > 100_000
        assert "thaid" in doc.text.lower()
