"""Base error type for lawcorpus.

Every failure carries a stable symbolic code so a caller can branch on the kind without
string-matching the prose, and states whether retrying could help. See
`dev/standards/error-handling.md`.

Two code styles coexist here, and only one of them is still being written. Everything new carries
the grammar of `dev/standards/error-codes.md` — `<sorter>.<descriptor>[.<sub>].<disposition>`, as
in `e.input.format.f` — so that a caller can prefix-match a branch of meaning. The nine
`BK_`-prefixed codes predate that standard and keep their identity, because a shipped code's
meaning never changes and converting one is a deprecation owed to every corpus repo that catches
it; tick ~6fpq is where that migration lives. No tenth flat code is minted, and
`tests/test_error_codes.py` is what enforces it (this.i @sqxhmdkt).

A dotted code's last token is the retry verdict, so `transient` is read off the code rather than
restated at each raise site (this.i @3tkymxtr).
"""

from __future__ import annotations


class LawcorpusError(Exception):
    """A lawcorpus failure with a stable symbolic code and a retry verdict.

    Subclasses set ``code``. ``transient`` defaults to whatever the code's disposition token says
    — ``.r`` means a retry may succeed, anything else means it will not — so a class cannot
    promise one thing in its identity and another in its message. The flat `BK_` codes carry no
    disposition and therefore default to False, which is the right answer for most of this
    package: it is pure, deterministic code, and the same input fails the same way every time.
    Fetchers, which touch the network, pass ``transient=True`` explicitly where a flat code is
    involved.
    """

    code = "BK_LAWCORPUS_ERROR"

    def __init__(self, message: str, *, transient: bool = None):
        if transient is None:
            transient = self.code.endswith(".r")
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
