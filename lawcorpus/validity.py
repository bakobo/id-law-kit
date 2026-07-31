"""Is this text *law*, and how binding is it?

Quote-or-drop — the rule inherited from `utah-id-law` — guarantees that a quoted passage was
genuinely *published*. It does not guarantee the passage is *in force*. Section 57 of India's
Aadhaar Act was struck down by the Supreme Court in 2018, yet the Act PDF that UIDAI publishes
today still carries the text. An agent following quote-or-drop over that PDF produces a confidently
false claim — precisely the failure quote-or-drop exists to prevent.

So validity is a required field on every corpus item, with no default, and every quote this package
emits is preceded by a banner. See `this.i` @oxu7ik and @xrfhyv.
"""

from __future__ import annotations

from enum import Enum

from .errors import LawcorpusError


class ValidityError(LawcorpusError):
    """A validity or authority token that is not in the vocabulary."""

    code = "BK_VALIDITY_UNKNOWN"


class Validity(Enum):
    """What has happened to this text since it was enacted."""

    IN_FORCE = "in-force"
    AMENDED = "amended"
    STRUCK_DOWN = "struck-down"
    READ_DOWN = "read-down"
    NOT_YET_APPLICABLE = "not-yet-applicable"
    REPEALED = "repealed"

    def banner(self, note: str = "") -> str:
        """The line printed above any quote of this text.

        `note` names the instrument responsible — the amending act, the judgment, the repeal —
        and is appended when known.
        """
        text = _BANNERS[self]
        if note:
            text = f"{text[:-1]} — {note}]" if text.endswith("]") else f"{text} — {note}"
        return text


_BANNERS = {
    Validity.IN_FORCE: "[in force]",
    Validity.AMENDED: "[AMENDED since enactment: quote the consolidated version, not this one]",
    Validity.STRUCK_DOWN: "[STRUCK DOWN: this text is NOT current law]",
    Validity.READ_DOWN: "[READ DOWN by a court: the text as written overstates what it now means]",
    Validity.NOT_YET_APPLICABLE: "[NOT YET APPLICABLE: enacted but not yet in application]",
    Validity.REPEALED: "[REPEALED: this text is NOT current law]",
}


class AuthorityTier(Enum):
    """How much weight this text carries when two sources conflict.

    `sources/registry.md` in `utah-id-law` states a trust order in prose ("statute and CFR text >
    official agency publication > case law > commentary"). This makes it machine-readable, so a
    conflict surfaces in the citation rather than being resolved silently by whichever text a
    search happened to hit first.
    """

    CONSTITUTIONAL = "constitutional"
    LEGISLATIVE = "legislative"
    DELEGATED = "delegated"
    JUDICIAL = "judicial"
    REGULATORY_GUIDANCE = "regulatory-guidance"
    COMMENTARY = "commentary"

    @property
    def rank(self) -> int:
        """Lower is more authoritative, so sorting puts binding text first."""
        return _RANKS[self]


_RANKS = {
    AuthorityTier.CONSTITUTIONAL: 0,
    AuthorityTier.LEGISLATIVE: 1,
    AuthorityTier.DELEGATED: 2,
    AuthorityTier.JUDICIAL: 3,
    AuthorityTier.REGULATORY_GUIDANCE: 4,
    AuthorityTier.COMMENTARY: 5,
}

_QUOTABLE_AS_CURRENT = frozenset({Validity.IN_FORCE})


def _parse(enum_cls, raw, field: str):
    if raw is None or not str(raw).strip():
        legal = ", ".join(m.value for m in enum_cls)
        raise ValidityError(
            f"The {field} field is empty, and it has no default. Every corpus item must state "
            f"one of: {legal}. An unrecorded {field} is the defect this field exists to prevent — "
            f"published text is not necessarily current law."
        )
    token = str(raw).strip().lower()
    for member in enum_cls:
        if member.value == token:
            return member
    legal = ", ".join(m.value for m in enum_cls)
    raise ValidityError(
        f"'{token[:60]}' is not a recognised {field}. It must be one of: {legal}."
    )


def parse_validity(raw) -> Validity:
    """Turn a manifest token into a `Validity`, refusing to guess."""
    return _parse(Validity, raw, "validity")


def parse_authority_tier(raw) -> AuthorityTier:
    """Turn a manifest token into an `AuthorityTier`, refusing to guess."""
    return _parse(AuthorityTier, raw, "authority_tier")


def quotable_as_current_law(validity) -> bool:
    """May this text be quoted as a statement of what the law *is* today?

    False does not mean the text is useless — a struck provision is still evidence of what a
    legislature once enacted. It means a finding may not present it as current law.
    """
    if not isinstance(validity, Validity):
        validity = parse_validity(validity)
    return validity in _QUOTABLE_AS_CURRENT
