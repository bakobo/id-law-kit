"""Every code this package raises, checked against `dev/standards/error-codes.md`.

The standard's value is that a caller can prefix-match a branch of meaning, and a single code in
the wrong shape is enough to hide a whole leaf from the pattern that should have caught it. That
is not something a reader reliably notices, so it is checked here: the grammar, the closed set of
first descriptors, the reserved disposition tokens, and the rule that a code's last token agrees
with what the error says about retrying.

The nine flat `BK_*` codes are frozen below rather than excluded by a pattern. They were published
before the standard existed and a shipped code's identity does not change, so they stay until
tick ~6fpq retires each one with a named successor — but nothing new joins them, and this list is
what makes that enforceable rather than a thing a reviewer must remember (this.i @sqxhmdkt).
"""

import importlib
import pkgutil
import re

import lawcorpus
from lawcorpus.errors import LawcorpusError

# `error-codes.md` § The taxonomy. The set is closed: adding one is a change to the standard.
FIRST_DESCRIPTORS = frozenset(
    {"input", "id", "grant", "feature", "proof", "party", "state", "env", "self", "rule"}
)

PUBLISHED_FLAT_CODES = frozenset(
    {
        "BK_LAWCORPUS_ERROR",
        "BK_VALIDITY_UNKNOWN",
        "BK_MANIFEST_INVALID",
        "BK_CORPUS_STORE",
        "BK_PDF_EXTRACT",
        "BK_CITE_UNRESOLVED",
        "BK_FORMEX_PARSE",
        "BK_CAML_PARSE",
        "BK_EURLEX_FETCH",
    }
)

_TOKEN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _error_classes():
    """Every `LawcorpusError` subclass in the package, with every module imported first."""
    for module in pkgutil.walk_packages(lawcorpus.__path__, prefix="lawcorpus."):
        importlib.import_module(module.name)

    seen = {}

    def walk(cls):
        seen[cls.__qualname__] = cls
        for sub in cls.__subclasses__():
            walk(sub)

    walk(LawcorpusError)
    return sorted(seen.values(), key=lambda c: (c.__module__, c.__qualname__))


def _dotted():
    return [cls for cls in _error_classes() if "." in cls.code]


class TestTheGrammar:
    def test_every_code_is_either_dotted_or_one_of_the_nine_published_flat_ones(self):
        flat = {cls.code for cls in _error_classes() if "." not in cls.code}
        assert flat == PUBLISHED_FLAT_CODES

    def test_the_package_really_does_raise_dotted_codes(self):
        assert len(_dotted()) >= 12  # a guard against the walk silently finding nothing

    def test_every_dotted_code_parses_as_the_standard_specifies(self):
        for cls in _dotted():
            tokens = cls.code.split(".")
            assert tokens[0] in ("e", "w"), cls.code
            assert tokens[-1] in ("f", "r"), cls.code
            # sorter, first descriptor, at least one sub-descriptor, disposition
            assert len(tokens) >= 4, cls.code

    def test_every_first_descriptor_is_in_the_closed_set(self):
        for cls in _dotted():
            assert cls.code.split(".")[1] in FIRST_DESCRIPTORS, cls.code

    def test_f_and_r_are_reserved_for_the_disposition(self):
        for cls in _dotted():
            assert "f" not in cls.code.split(".")[:-1], cls.code
            assert "r" not in cls.code.split(".")[:-1], cls.code

    def test_every_descriptor_is_lower_kebab_case(self):
        for cls in _dotted():
            for token in cls.code.split(".")[1:-1]:
                assert _TOKEN.match(token), cls.code

    def test_the_standard_sub_descriptors_of_input_are_not_bypassed(self):
        """`input` has a standard second level; a repo's own leaves go below it, not beside it."""
        for cls in _dotted():
            tokens = cls.code.split(".")
            if tokens[1] == "input":
                assert tokens[2] in ("missing", "format", "range", "multi"), cls.code


class TestDispositionIsTheTruth:
    """`f`/`r` is part of the identity, so the retry verdict is read off it rather than repeated."""

    def test_a_final_code_says_retrying_will_not_help(self):
        for cls in _dotted():
            if cls.code.endswith(".f"):
                assert cls("why").transient is False, cls.code

    def test_a_retryable_code_says_retrying_may_help(self):
        for cls in _dotted():
            if cls.code.endswith(".r"):
                assert cls("why").transient is True, cls.code

    def test_a_flat_code_keeps_the_old_default(self):
        assert LawcorpusError("why").transient is False

    def test_an_explicit_flag_still_wins(self):
        assert LawcorpusError("why", transient=True).transient is True
