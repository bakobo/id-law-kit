"""Base error type for lawcorpus.

Every failure carries a stable symbolic code so a caller can branch on the kind without
string-matching the prose, and states whether retrying could help. See
`dev/standards/error-handling.md`.
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
