"""Base error type for lawcorpus.

Every failure carries a stable symbolic code so a caller can branch on the kind without
string-matching the prose, and states whether retrying could help. See
`dev/standards/error-handling.md`.

Two code styles coexist here, and that is a known debt rather than a design. The `BK_`-prefixed
codes predate `dev/standards/error-codes.md`, whose grammar is
`<sorter>.<descriptor>[.<sub>].<disposition>` — `e.input.format.f` — and which is what everything
added since uses, so that a caller can prefix-match a branch of meaning. Converting the older
codes is a change of published identity for each one, so it is recorded rather than done in
passing. ~6fpq
"""

from __future__ import annotations


class LawcorpusError(Exception):
    """A lawcorpus failure with a stable symbolic code and a retry verdict.

    Subclasses set ``code``. ``transient`` defaults to False because most of this package is
    pure, deterministic code: the same input fails the same way every time, so a retry is
    pointless and the message should say so. Fetchers, which touch the network, raise with
    ``transient=True`` where a retry genuinely could succeed.
    """

    code = "BK_LAWCORPUS_ERROR"

    def __init__(self, message: str, *, transient: bool = False):
        self.transient = transient
        self.message = message
        super().__init__(f"[{self.code}] {message}")

    def __str__(self) -> str:
        tail = (
            " Retrying may succeed."
            if self.transient
            else " Retrying will not change this; change the input instead."
        )
        return f"[{self.code}] {self.message}{tail}"
