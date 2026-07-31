"""The EUR-Lex / Cellar fetcher.

Shared by `eu-data-law` and `eidas-eudi` — the second consumer existing on day one is what
justified extracting this kit at all (this.i @s62c4j).

Network is injected, so these tests are hermetic. The one test that really talks to Brussels is
marked `network` and is deselected by default.
"""

import pytest

from lawcorpus.fetch.eurlex import (
    ACCEPT_FORMEX_ZIP,
    ACCEPT_NOTICE_BRANCH,
    ACCEPT_NOTICE_OBJECT,
    CELEX_RE,
    EurLexError,
    EurLexFetcher,
    celex_for_consolidation,
    is_consolidated,
    parse_celex,
)


class FakeTransport:
    """Records requests and replays canned responses."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []
        self.default = (200, b"<akn>text</akn>", "application/xml;notice=branch")

    def __call__(self, url, *, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.responses.get(url, self.default)


@pytest.fixture
def transport():
    return FakeTransport()


@pytest.fixture
def fetcher(transport):
    return EurLexFetcher(transport=transport)


class TestParseCelex:
    def test_accepts_a_regulation(self):
        assert parse_celex("32016R0679") == "32016R0679"

    def test_accepts_a_consolidated_text(self):
        assert parse_celex("02016R0679-20160504") == "02016R0679-20160504"

    def test_accepts_a_court_judgment(self):
        assert parse_celex("62018CJ0311") == "62018CJ0311"  # Schrems II

    def test_uppercases_and_strips(self):
        assert parse_celex("  32016r0679 ") == "32016R0679"

    def test_rejects_prose(self):
        with pytest.raises(EurLexError) as e:
            parse_celex("the GDPR")
        assert "CELEX" in str(e.value)

    def test_rejects_empty(self):
        with pytest.raises(EurLexError):
            parse_celex("")

    def test_regex_is_exported_for_callers_that_validate_lists(self):
        assert CELEX_RE.match("32016R0679")
        assert not CELEX_RE.match("nonsense")


class TestConsolidation:
    def test_recognises_a_consolidated_celex(self):
        assert is_consolidated("02016R0679-20160504") is True

    def test_recognises_an_original_celex(self):
        assert is_consolidated("32016R0679") is False

    def test_builds_a_consolidated_celex_from_an_original(self):
        assert celex_for_consolidation("32016R0679", "2016-05-04") == "02016R0679-20160504"

    def test_rejects_a_non_iso_date(self):
        with pytest.raises(EurLexError) as e:
            celex_for_consolidation("32016R0679", "4 May 2016")
        assert "YYYY-MM-DD" in str(e.value)

    def test_refuses_to_consolidate_an_already_consolidated_celex(self):
        with pytest.raises(EurLexError):
            celex_for_consolidation("02016R0679-20160504", "2018-01-01")


class TestFetchDocument:
    def test_requests_the_cellar_celex_url(self, fetcher, transport):
        fetcher.fetch("32016R0679")
        assert transport.calls[0]["url"].endswith("/resource/celex/32016R0679")

    def test_defaults_to_the_full_branch_notice(self, fetcher, transport):
        fetcher.fetch("32016R0679")
        assert transport.calls[0]["headers"]["Accept"] == ACCEPT_NOTICE_BRANCH

    def test_asks_for_english_by_default(self, fetcher, transport):
        # English-only is a declared scope decision, not an accident. See kit this.i @om6zsj.
        fetcher.fetch("32016R0679")
        assert transport.calls[0]["headers"]["Accept-Language"] == "eng"

    def test_can_ask_for_the_metadata_notice(self, fetcher, transport):
        fetcher.fetch("32016R0679", accept=ACCEPT_NOTICE_OBJECT)
        assert transport.calls[0]["headers"]["Accept"] == ACCEPT_NOTICE_OBJECT

    def test_can_ask_for_formex(self, fetcher, transport):
        fetcher.fetch("32016R0679", accept=ACCEPT_FORMEX_ZIP)
        assert transport.calls[0]["headers"]["Accept"] == ACCEPT_FORMEX_ZIP

    def test_returns_body_and_media_type(self, fetcher):
        doc = fetcher.fetch("32016R0679")
        assert doc.body == b"<akn>text</akn>"
        assert doc.media_type == "application/xml;notice=branch"
        assert doc.celex == "32016R0679"

    def test_records_the_url_it_used_for_the_manifest(self, fetcher):
        assert fetcher.fetch("32016R0679").url.endswith("/resource/celex/32016R0679")

    def test_normalises_the_celex_before_requesting(self, fetcher, transport):
        fetcher.fetch("  32016r0679 ")
        assert transport.calls[0]["url"].endswith("32016R0679")


class TestFetchFailures:
    def test_404_is_permanent_and_names_the_celex(self, transport):
        transport.default = (404, b"", "text/html")
        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=transport).fetch("32016R9999")
        assert e.value.transient is False
        assert "32016R9999" in str(e.value)

    def test_404_suggests_the_likely_cause(self, transport):
        transport.default = (404, b"", "text/html")
        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=transport).fetch("32016R9999")
        # text/html 404s on this host are the documented behaviour for a wrong Accept, not
        # only for a wrong CELEX — say so rather than sending the reader down one path.
        assert "Accept" in str(e.value)

    def test_500_is_transient(self, transport):
        transport.default = (500, b"", "text/html")
        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=transport).fetch("32016R0679")
        assert e.value.transient is True

    def test_503_is_transient(self, transport):
        transport.default = (503, b"", "text/html")
        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=transport).fetch("32016R0679")
        assert e.value.transient is True

    def test_empty_body_with_200_is_refused(self, transport):
        transport.default = (200, b"", "application/xml")
        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=transport).fetch("32016R0679")
        assert "empty" in str(e.value).lower()

    def test_a_transport_exception_is_wrapped_as_transient(self, transport):
        def boom(url, *, headers, timeout):
            raise OSError("connection reset")

        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=boom).fetch("32016R0679")
        assert e.value.transient is True
        assert "connection reset" in str(e.value)


class TestSparql:
    def test_posts_the_query_to_the_cellar_endpoint(self, transport):
        transport.default = (200, b'{"results":{"bindings":[]}}', "application/sparql-results+json")
        EurLexFetcher(transport=transport).sparql("SELECT ?s WHERE {?s ?p ?o} LIMIT 1")
        assert "sparql" in transport.calls[0]["url"]

    def test_asks_for_json(self, transport):
        transport.default = (200, b'{"results":{"bindings":[]}}', "application/sparql-results+json")
        EurLexFetcher(transport=transport).sparql("SELECT ?s WHERE {?s ?p ?o}")
        assert transport.calls[0]["headers"]["Accept"] == "application/sparql-results+json"

    def test_returns_the_bindings(self, transport):
        transport.default = (
            200,
            b'{"results":{"bindings":[{"s":{"value":"http://x"}}]}}',
            "application/sparql-results+json",
        )
        rows = EurLexFetcher(transport=transport).sparql("SELECT ?s WHERE {?s ?p ?o}")
        assert rows == [{"s": "http://x"}]

    def test_malformed_json_is_a_permanent_error(self, transport):
        transport.default = (200, b"not json", "application/sparql-results+json")
        with pytest.raises(EurLexError) as e:
            EurLexFetcher(transport=transport).sparql("SELECT ?s WHERE {?s ?p ?o}")
        assert e.value.transient is False


@pytest.mark.network
class TestAgainstTheRealCellar:
    def test_gdpr_comes_back_as_xml(self):
        doc = EurLexFetcher().fetch("32016R0679")
        assert doc.body.startswith(b"<")
        assert len(doc.body) > 100_000
