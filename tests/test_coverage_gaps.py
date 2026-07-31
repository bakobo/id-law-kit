"""Branches the main suites do not reach.

Kept separate so the behavioural suites read as documentation of intent rather than as a
coverage exercise.
"""

import io
import urllib.error

import pytest

from lawcorpus.fetch import eurlex
from lawcorpus.fetch.eurlex import EurLexError, EurLexFetcher
from lawcorpus.manifest import Manifest, ManifestItem
from lawcorpus.validity import AuthorityTier, Validity


def an_item(**over):
    base = dict(
        item_id="32016R0679",
        citation="Regulation (EU) 2016/679",
        title="GDPR",
        authority_tier="legislative",
        validity="in-force",
        validity_note="",
        version_id="",
        lang="eng",
        source_url="http://example.invalid/x",
        retrieved="2026-07-31",
        media_type="application/xml",
        bytes=1,
        sha256="a" * 64,
    )
    base.update(over)
    return ManifestItem(**base)


class TestManifestEdges:
    def test_accepts_already_parsed_enum_members(self):
        # _coerce's short-circuit: constructing from another item's fields must not re-parse.
        item = an_item(
            validity=Validity.IN_FORCE, authority_tier=AuthorityTier.LEGISLATIVE
        )
        assert item.validity is Validity.IN_FORCE
        assert item.authority_tier is AuthorityTier.LEGISLATIVE

    def test_manifest_is_not_equal_to_a_non_manifest(self):
        assert Manifest([an_item()]) != "not a manifest"

    def test_manifest_equality_ignores_order(self):
        a, b = an_item(), an_item(item_id="other")
        assert Manifest([a, b]) == Manifest([b, a])


class TestEurLexEdges:
    def test_429_is_transient_and_says_to_slow_down(self):
        def throttled(url, *, headers, timeout):
            return 429, b"", "text/html"

        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=throttled).fetch("32016R0679")
        assert e.value.transient is True
        assert "429" in str(e.value)

    def test_a_eurlex_error_from_the_transport_passes_through_unwrapped(self):
        # Otherwise a precise error would be reburied as a generic transient network failure.
        original = EurLexError("the transport already diagnosed this", transient=False)

        def already_diagnosed(url, *, headers, timeout):
            raise original

        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=already_diagnosed).fetch("32016R0679")
        assert e.value is original
        assert e.value.transient is False


class TestRealTransport:
    """`_urllib_transport` itself, with urllib stubbed — no network."""

    def test_returns_status_body_and_content_type(self, monkeypatch):
        class Resp:
            status = 200
            headers = {"Content-Type": "application/xml"}

            def read(self):
                return b"<x/>"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(eurlex.urllib.request, "urlopen", lambda req, timeout: Resp())
        status, body, ctype = eurlex._urllib_transport(
            "http://example.invalid", headers={}, timeout=5
        )
        assert (status, body, ctype) == (200, b"<x/>", "application/xml")

    def test_an_http_error_is_returned_as_a_status_not_raised(self, monkeypatch):
        # urllib raises on 4xx/5xx; the fetcher's own status handling must see the code instead,
        # so that a 404 and a 503 can be told apart and classified.
        def raise_404(req, timeout):
            raise urllib.error.HTTPError(
                "http://example.invalid",
                404,
                "Not Found",
                {"Content-Type": "text/html"},
                io.BytesIO(b"nope"),
            )

        monkeypatch.setattr(eurlex.urllib.request, "urlopen", raise_404)
        status, body, ctype = eurlex._urllib_transport(
            "http://example.invalid", headers={}, timeout=5
        )
        assert status == 404
        assert body == b"nope"
        assert ctype == "text/html"
