"""EUR-Lex / Cellar fetcher.

The EU publishes its law through a content-negotiated resource API that needs no registration —
a far better position than `utah-id-law`, which had to recover its endpoints by reading a React
bundle. Verified working 2026-07-31:

    curl -H 'Accept: application/xml;notice=branch' -H 'Accept-Language: eng' \\
         http://publications.europa.eu/resource/celex/32016R0679      # 1.8 MB, the full text
    curl -H 'Accept: application/zip;mtype=fmx4' ...                  # 90 KB, Formex source
    curl -H 'Accept: application/xml;notice=object' ...               # 7 KB, metadata only

Two traps worth knowing before you use this:

1. **`Accept: text/html` returns 404 on this host.** The HTML rendering lives on
   `eur-lex.europa.eu/legal-content/...` instead. A 404 here usually means a wrong Accept header,
   not a wrong CELEX — which is why the error says both.
2. **Original vs. consolidated text.** `32016R0679` is the GDPR *as published in 2016*;
   `02016R0679-20160504` is a consolidated version incorporating later amendments. For an
   instrument amended more than once, quoting the original is simply wrong. The corpus therefore
   pins a consolidation, not just a CELEX — the analogue of `utah-id-law`'s version stamps.
   See `eu-data-law` this.i @bqbgl6.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from ..errors import LawcorpusError

CELLAR_BASE = "http://publications.europa.eu/resource/celex/"
SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"

ACCEPT_NOTICE_BRANCH = "application/xml;notice=branch"
ACCEPT_NOTICE_OBJECT = "application/xml;notice=object"
ACCEPT_FORMEX_ZIP = "application/zip;mtype=fmx4"

# Sector digit, year, descriptor letter(s), number — optionally a consolidation date suffix.
CELEX_RE = re.compile(r"^[0-9]{5}[A-Z]{1,2}[0-9]{4}(?:\([0-9]{2}\))?(?:-[0-9]{8})?$")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

USER_AGENT = "bakobo-id-law-kit/0.1 (+https://github.com/bakobo/id-law-kit)"


class EurLexError(LawcorpusError):
    """A CELEX that will not parse, or a Cellar request that did not come back usable."""

    code = "BK_EURLEX_FETCH"


def parse_celex(raw) -> str:
    """Normalise and validate a CELEX number, refusing anything that is not one."""
    text = ("" if raw is None else str(raw)).strip().upper()
    if not text:
        raise EurLexError(
            "No CELEX number was given. A CELEX looks like '32016R0679' (the GDPR) or "
            "'02016R0679-20160504' (a consolidated version of it)."
        )
    if not CELEX_RE.match(text):
        raise EurLexError(
            f"'{text[:40]}' is not a CELEX number. Expected the form sector+year+type+number, "
            f"such as '32016R0679' for a regulation or '62018CJ0311' for a Court judgment. Look "
            f"the number up on eur-lex.europa.eu rather than guessing it."
        )
    return text


def is_consolidated(celex) -> bool:
    """Does this CELEX name a consolidated text rather than the original publication?"""
    return "-" in parse_celex(celex)


def celex_for_consolidation(celex, date: str) -> str:
    """Build the consolidated CELEX for `celex` as at `date` (YYYY-MM-DD).

    Consolidated texts swap the leading sector digit for 0 and append the date.
    """
    celex = parse_celex(celex)
    if is_consolidated(celex):
        raise EurLexError(
            f"'{celex}' already names a consolidated text, so it cannot be consolidated again. "
            f"Start from the original CELEX (leading digit 3 for secondary legislation)."
        )
    m = _ISO_DATE.match(str(date).strip())
    if not m:
        raise EurLexError(
            f"The consolidation date '{str(date)[:20]}' is not an ISO date. Use YYYY-MM-DD."
        )
    return f"0{celex[1:]}-{m.group(1)}{m.group(2)}{m.group(3)}"


@dataclass(frozen=True)
class EurLexDocument:
    """One retrieved body, with the provenance a manifest row needs."""

    celex: str
    url: str
    body: bytes
    media_type: str


def _urllib_transport(url, *, headers, timeout):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "")


class EurLexFetcher:
    """Retrieve documents and run enumeration queries against Cellar.

    `transport` is injected so the fetcher can be tested without touching the network. It takes
    `(url, headers=..., timeout=...)` and returns `(status, body, content_type)`.
    """

    def __init__(self, transport=None, timeout: int = 60):
        self._transport = transport or _urllib_transport
        self.timeout = timeout

    def _request(self, url, accept, extra_headers=None):
        headers = {"Accept": accept, "User-Agent": USER_AGENT}
        headers.update(extra_headers or {})
        try:
            status, body, content_type = self._transport(
                url, headers=headers, timeout=self.timeout
            )
        except EurLexError:
            raise
        except Exception as e:
            raise EurLexError(
                f"The request to {url} did not complete: {e}. This is usually a network or "
                f"proxy problem rather than a bad request.",
                transient=True,
            ) from e

        if status >= 500:
            raise EurLexError(
                f"Cellar answered {status} for {url}. The service is failing or overloaded, not "
                f"rejecting the request.",
                transient=True,
            )
        if status == 429:
            raise EurLexError(
                f"Cellar answered 429 for {url} — the fetch is going too fast. Slow the loop down "
                f"and resume.",
                transient=True,
            )
        if status != 200:
            raise EurLexError(
                f"Cellar answered {status} for {url}. Check the CELEX number, and check the "
                f"Accept header: this host returns 404 for 'Accept: text/html', so a 404 here "
                f"often means the wrong content type rather than a missing document. Use "
                f"eur-lex.europa.eu/legal-content/ for HTML."
            )
        return body, content_type

    def fetch(self, celex, accept: str = ACCEPT_NOTICE_BRANCH) -> EurLexDocument:
        """Retrieve one document by CELEX number."""
        celex = parse_celex(celex)
        url = CELLAR_BASE + celex
        body, content_type = self._request(url, accept, {"Accept-Language": "eng"})
        if not body:
            raise EurLexError(
                f"Cellar returned 200 with an empty body for {celex}. Treat this as a failed "
                f"retrieval — storing it would put a zero-byte entry in the corpus that reads "
                f"like a successful fetch."
            )
        return EurLexDocument(celex=celex, url=url, body=body, media_type=content_type)

    def sparql(self, query: str) -> list:
        """Run a SPARQL query against Cellar and return the bindings as flat dicts.

        This is the enumeration mechanism — how you build a CELEX work-list without hand-listing
        it: every consolidation of an instrument, every judgment citing an article, every
        instrument in a subject domain.
        """
        url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
        body, _ = self._request(url, "application/sparql-results+json")
        try:
            payload = json.loads(body.decode("utf-8", "replace"))
            bindings = payload["results"]["bindings"]
        except (ValueError, KeyError, TypeError) as e:
            raise EurLexError(
                f"The SPARQL endpoint returned a body that is not SPARQL JSON results: {e}. The "
                f"query itself is the thing to check — a syntax error comes back as a page, not "
                f"as an error object."
            ) from e
        return [{k: v.get("value") for k, v in row.items()} for row in bindings]
