"""Is this text *law*, how binding is it, and is it the text that binds?

Quote-or-drop — the rule inherited from `utah-id-law` — guarantees that a quoted passage was
genuinely *published*. It does not guarantee the passage is *in force*. Section 57 of India's
Aadhaar Act was struck down by the Supreme Court in 2018, yet the Act PDF that UIDAI publishes
today still carries the text. An agent following quote-or-drop over that PDF produces a confidently
false claim — precisely the failure quote-or-drop exists to prevent.

So validity is a required field on every corpus item, with no default, and every quote this package
emits is preceded by a banner. See `this.i` @oxu7ik and @xrfhyv.

`translation_status` closes the analogous hole one layer down, and it is the Asian half of this
programme's version of the same trap. Quote-or-drop over an English rendering of a Japanese Act
proves only that somebody translated it. Japan says so about its own translation service —
「法令翻訳は、正文ではなく…法的効力を有するのは日本語の法令自体」, 正文 being the technical term for
authentic text — and Korea's KLRI says its translations are "neither official nor legally
effective". Same shape as validity, so the same treatment: a required field with no default, and a
banner on every quote that is not authentic text. See `this.i` @elsvh64d.

The hazard is provenance, not language. Singapore is natively English and the Singapore Statutes
Online terms declare their own text unofficial; that belongs to `authority_tier`, and recording it
here would be a category error.
"""

from __future__ import annotations

from enum import Enum

from .errors import LawcorpusError


class ValidityError(LawcorpusError):
    """A validity or authority token that is not in the vocabulary."""

    code = "BK_VALIDITY_UNKNOWN"


class TranslationStatusError(LawcorpusError):
    """A translation_status that is missing, or not in the vocabulary.

    A code of its own, in the grammar of `dev/standards/error-codes.md`, so a harvester can tell
    a translation-provenance refusal from a validity refusal without reading the prose. The older
    `BK_`-style codes on the classes around it predate that standard.
    """

    code = "e.input.translation-status.f"


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

class TranslationStatus(Enum):
    """Is this the text that binds, or a rendering of it?

    `authoritative` is not a synonym for "published by the government". The EU's 24 language
    versions are each authentic, so each is `authoritative`; Japan's and Korea's official English
    translations are published by the state and disclaim authority in their own words, which is
    what `official-non-authoritative` names.
    """

    AUTHORITATIVE = "authoritative"
    OFFICIAL_NON_AUTHORITATIVE = "official-non-authoritative"
    UNOFFICIAL = "unofficial"
    MACHINE = "machine"

    def banner(self, original: str = "") -> str:
        """The translation line printed above a quote, or "" when the text is authentic.

        `original` names the corpus item this renders, so a reader can go to the text that binds
        rather than having to find it. Authentic text stays quiet: a banner on all 24 EU language
        versions would be noise, and noise is what stops banners being read.
        """
        text = _TRANSLATION_BANNERS[self]
        if text and original:
            text = f"{text[:-1]} — of {original}]"
        return text


_TRANSLATION_BANNERS = {
    TranslationStatus.AUTHORITATIVE: "",
    TranslationStatus.OFFICIAL_NON_AUTHORITATIVE: (
        "[TRANSLATION, official but NOT authentic text: the original governs]"
    ),
    TranslationStatus.UNOFFICIAL: (
        "[UNOFFICIAL TRANSLATION: not published by the enacting authority; the original governs]"
    ),
    TranslationStatus.MACHINE: (
        "[MACHINE TRANSLATION: a reading aid, NEVER evidence — do not quote this text]"
    ),
}

_QUOTABLE_AS_CURRENT = frozenset({Validity.IN_FORCE})
_NOT_EVIDENCE = frozenset({TranslationStatus.MACHINE})


def _parse(enum_cls, raw, field: str, error_cls=ValidityError):
    if raw is None or not str(raw).strip():
        legal = ", ".join(m.value for m in enum_cls)
        raise error_cls(
            f"The {field} field is empty, and it has no default. Every corpus item must state "
            f"one of: {legal}. An unrecorded {field} is the defect this field exists to prevent — "
            f"published text is not necessarily current law."
        )
    token = str(raw).strip().lower()
    for member in enum_cls:
        if member.value == token:
            return member
    legal = ", ".join(m.value for m in enum_cls)
    raise error_cls(
        f"'{token[:60]}' is not a recognised {field}. It must be one of: {legal}."
    )


def parse_validity(raw) -> Validity:
    """Turn a manifest token into a `Validity`, refusing to guess."""
    return _parse(Validity, raw, "validity")


def parse_authority_tier(raw) -> AuthorityTier:
    """Turn a manifest token into an `AuthorityTier`, refusing to guess."""
    return _parse(AuthorityTier, raw, "authority_tier")


def parse_translation_status(raw) -> TranslationStatus:
    """Turn a manifest token into a `TranslationStatus`, refusing to guess."""
    return _parse(TranslationStatus, raw, "translation_status", TranslationStatusError)


def quotable_as_current_law(validity) -> bool:
    """May this text be quoted as a statement of what the law *is* today?

    False does not mean the text is useless — a struck provision is still evidence of what a
    legislature once enacted. It means a finding may not present it as current law.
    """
    if not isinstance(validity, Validity):
        validity = parse_validity(validity)
    return validity in _QUOTABLE_AS_CURRENT


def quotable_as_evidence(translation_status) -> bool:
    """May this rendering be quoted at all?

    False only for `machine`. An official-but-non-authoritative translation is wrong at the
    margin, and its banner says so; machine output can invert a negation with no signal at all, so
    it is a reading aid for deciding which provision to have rendered properly, never evidence.
    """
    if not isinstance(translation_status, TranslationStatus):
        translation_status = parse_translation_status(translation_status)
    return translation_status not in _NOT_EVIDENCE
