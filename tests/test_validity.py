"""The validity and authority vocabularies.

These exist because of the Aadhaar §57 trap: the Act PDF published by UIDAI still carries text
the Supreme Court struck down in 2018. A corpus that records only "we fetched this on date D"
lets a quote-or-drop rule manufacture a false claim. See this.i @oxu7ik.
"""

import pytest

from lawcorpus.validity import (
    AuthorityTier,
    TranslationStatus,
    TranslationStatusError,
    Validity,
    ValidityError,
    parse_authority_tier,
    parse_translation_status,
    parse_validity,
    quotable_as_current_law,
    quotable_as_evidence,
)


class TestParseValidity:
    def test_accepts_every_member_of_the_vocabulary(self):
        for token in (
            "in-force",
            "amended",
            "struck-down",
            "read-down",
            "not-yet-applicable",
            "repealed",
        ):
            assert parse_validity(token).value == token

    def test_is_case_and_whitespace_insensitive(self):
        assert parse_validity("  In-Force ") is Validity.IN_FORCE

    def test_rejects_an_unknown_token(self):
        with pytest.raises(ValidityError) as e:
            parse_validity("probably-fine")
        assert "probably-fine" in str(e.value)
        assert "in-force" in str(e.value)  # the error lists the legal values

    def test_rejects_an_empty_value_rather_than_defaulting(self):
        # No default. An unset validity is the bug this field exists to prevent.
        with pytest.raises(ValidityError):
            parse_validity("")

    def test_rejects_none(self):
        with pytest.raises(ValidityError):
            parse_validity(None)


class TestParseAuthorityTier:
    def test_accepts_the_ladder(self):
        for token in (
            "constitutional",
            "legislative",
            "delegated",
            "judicial",
            "regulatory-guidance",
            "commentary",
        ):
            assert parse_authority_tier(token).value == token

    def test_rejects_an_unknown_tier(self):
        with pytest.raises(ValidityError):
            parse_authority_tier("blog-post")

    def test_tiers_order_by_authority(self):
        # Lower rank == higher authority, so sorting a mixed list puts the binding text first.
        assert AuthorityTier.CONSTITUTIONAL.rank < AuthorityTier.LEGISLATIVE.rank
        assert AuthorityTier.LEGISLATIVE.rank < AuthorityTier.DELEGATED.rank
        assert AuthorityTier.DELEGATED.rank < AuthorityTier.JUDICIAL.rank
        assert AuthorityTier.JUDICIAL.rank < AuthorityTier.REGULATORY_GUIDANCE.rank
        assert AuthorityTier.REGULATORY_GUIDANCE.rank < AuthorityTier.COMMENTARY.rank

    def test_ranks_are_unique(self):
        ranks = [t.rank for t in AuthorityTier]
        assert len(ranks) == len(set(ranks))


class TestQuotableAsCurrentLaw:
    def test_in_force_text_is_quotable(self):
        assert quotable_as_current_law(Validity.IN_FORCE) is True

    @pytest.mark.parametrize(
        "validity",
        [
            Validity.STRUCK_DOWN,
            Validity.READ_DOWN,
            Validity.REPEALED,
            Validity.NOT_YET_APPLICABLE,
            Validity.AMENDED,
        ],
    )
    def test_everything_else_is_not(self, validity):
        # Not "unquotable" — quotable *as current law*. A struck provision is still evidence of
        # what the legislature once enacted; it is just not the law now.
        assert quotable_as_current_law(validity) is False

    def test_accepts_a_raw_token_too(self):
        assert quotable_as_current_law("in-force") is True
        assert quotable_as_current_law("struck-down") is False


class TestParseTranslationStatus:
    def test_accepts_every_member_of_the_vocabulary(self):
        for token in ("authoritative", "official-non-authoritative", "unofficial", "machine"):
            assert parse_translation_status(token).value == token

    def test_is_case_and_whitespace_insensitive(self):
        assert parse_translation_status(" Machine ") is TranslationStatus.MACHINE

    def test_rejects_an_unknown_token(self):
        with pytest.raises(TranslationStatusError) as e:
            parse_translation_status("pretty-good")
        assert "pretty-good" in str(e.value)
        assert "official-non-authoritative" in str(e.value)  # the error lists the legal values

    def test_rejects_an_empty_value_rather_than_defaulting_to_authoritative(self):
        # Defaulting would make every EU item silently right and every Asian item silently wrong.
        with pytest.raises(TranslationStatusError):
            parse_translation_status("")

    def test_rejects_none(self):
        with pytest.raises(TranslationStatusError):
            parse_translation_status(None)

    def test_its_error_code_is_its_own(self):
        # A caller branching on translation provenance must not have to catch a validity error.
        with pytest.raises(TranslationStatusError) as e:
            parse_translation_status("")
        assert e.value.code != ValidityError.code
        assert e.value.transient is False


class TestQuotableAsEvidence:
    @pytest.mark.parametrize(
        "status",
        [
            TranslationStatus.AUTHORITATIVE,
            TranslationStatus.OFFICIAL_NON_AUTHORITATIVE,
            TranslationStatus.UNOFFICIAL,
        ],
    )
    def test_human_translations_are_evidence_even_when_not_authentic(self, status):
        # Japan's and Korea's official translations disclaim authority; they remain quotable, with
        # a banner, because a human rendered them and the original is named.
        assert quotable_as_evidence(status) is True

    def test_machine_translation_is_never_evidence(self):
        assert quotable_as_evidence(TranslationStatus.MACHINE) is False

    def test_accepts_a_raw_token_too(self):
        assert quotable_as_evidence("machine") is False
        assert quotable_as_evidence("authoritative") is True


class TestTranslationBanner:
    def test_authoritative_text_carries_no_translation_banner(self):
        # The EU's 24 language versions are each authentic. A banner there would be noise, and
        # noise is what stops banners being read.
        assert TranslationStatus.AUTHORITATIVE.banner() == ""

    def test_an_official_translation_says_the_original_governs(self):
        banner = TranslationStatus.OFFICIAL_NON_AUTHORITATIVE.banner()
        assert "TRANSLATION" in banner
        assert "original governs" in banner

    def test_an_unofficial_translation_says_who_did_not_publish_it(self):
        assert "UNOFFICIAL" in TranslationStatus.UNOFFICIAL.banner()

    def test_the_machine_banner_forbids_quotation_outright(self):
        banner = TranslationStatus.MACHINE.banner()
        assert "MACHINE TRANSLATION" in banner
        assert "NEVER evidence" in banner

    def test_the_banner_names_the_original_item(self):
        banner = TranslationStatus.UNOFFICIAL.banner("425AC0000000027")
        assert "425AC0000000027" in banner

    def test_an_authoritative_item_stays_quiet_even_with_an_original_named(self):
        assert TranslationStatus.AUTHORITATIVE.banner("425AC0000000027") == ""


class TestBanner:
    def test_in_force_banner_is_quiet(self):
        assert Validity.IN_FORCE.banner() == "[in force]"

    def test_struck_down_banner_shouts(self):
        banner = Validity.STRUCK_DOWN.banner()
        assert "STRUCK DOWN" in banner
        assert "NOT current law" in banner

    def test_banner_names_the_instrument_that_changed_it(self):
        banner = Validity.STRUCK_DOWN.banner("Puttaswamy (2018) 1 SCC 1")
        assert "Puttaswamy (2018) 1 SCC 1" in banner
        assert "STRUCK DOWN" in banner

    def test_read_down_banner_warns_without_claiming_invalidity(self):
        banner = Validity.READ_DOWN.banner()
        assert "READ DOWN" in banner
        assert "STRUCK" not in banner
