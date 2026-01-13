"""Tests for copay module."""

from decimal import Decimal
from datetime import date

import pytest

from claims_processor.model import Claim
from claims_processor.enums import PlanType
from claims_processor.copay import (
    calculate_copay,
    COMMERCIAL_MIN,
    COMMERCIAL_MAX,
    COMMERCIAL_RATE,
    MEDICARE_GENERIC,
    MEDICARE_BRAND,
)


class TestCalculateCopay:
    """Test cases for calculate_copay function."""

    def test_commercial_plan_below_minimum(self):
        """Test commercial plan with drug cost below minimum threshold."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("20.00"),  # 20% = $4.00, should be capped at $10.00
            plan_type=PlanType.COMMERCIAL,
        )
        copay = calculate_copay(claim)
        assert copay == COMMERCIAL_MIN

    def test_commercial_plan_above_maximum(self):
        """Test commercial plan with drug cost above maximum threshold."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("1000.00"),  # 20% = $200.00, should be capped at $100.00
            plan_type=PlanType.COMMERCIAL,
        )
        copay = calculate_copay(claim)
        assert copay == COMMERCIAL_MAX

    def test_commercial_plan_within_range(self):
        """Test commercial plan with drug cost within range."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),  # 20% = $20.00
            plan_type=PlanType.COMMERCIAL,
        )
        copay = calculate_copay(claim)
        expected = (Decimal("100.00") * COMMERCIAL_RATE).quantize(Decimal("0.01"))
        assert copay == expected
        assert copay == Decimal("20.00")

    def test_commercial_plan_at_minimum_threshold(self):
        """Test commercial plan at minimum threshold boundary."""
        # Drug cost where 20% equals minimum
        min_drug_cost = COMMERCIAL_MIN / COMMERCIAL_RATE  # $50.00
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=min_drug_cost,
            plan_type=PlanType.COMMERCIAL,
        )
        copay = calculate_copay(claim)
        assert copay == COMMERCIAL_MIN

    def test_commercial_plan_rounding(self):
        """Test commercial plan copay calculation with rounding."""
        # Test rounding up (third decimal >= 5)
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("51.33"),  # 20% = $10.266, should round up to $10.27
            plan_type=PlanType.COMMERCIAL,
        )
        copay = calculate_copay(claim)
        assert copay == Decimal("10.27")
        
        # Test rounding down (third decimal < 5)
        claim = Claim(
            claim_id="CLM002",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("55.32"),  # 20% = $11.064, should round down to $10.26
            plan_type=PlanType.COMMERCIAL,
        )
        copay = calculate_copay(claim)
        assert copay == Decimal("11.06")

    def test_medicare_plan_brand_name_drug(self):
        """Test Medicare plan with brand name drug (NDC starts with '0')."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="00234567890",  # Starts with '0' = brand name
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.MEDICARE,
        )
        copay = calculate_copay(claim)
        assert copay == MEDICARE_BRAND

    def test_medicare_plan_generic_drug(self):
        """Test Medicare plan with generic drug (NDC doesn't start with '0')."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="10345678901",  # Doesn't start with '0' = generic
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.MEDICARE,
        )
        copay = calculate_copay(claim)
        assert copay == MEDICARE_GENERIC

    def test_medicaid_plan_zero_copay(self):
        """Test Medicaid plan always returns zero copay."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.MEDICAID,
        )
        copay = calculate_copay(claim)
        assert copay == Decimal("0.00")


        """Test that Medicaid copay is zero regardless of NDC."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="01234567890",  # Brand name, but should still be $0
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.MEDICAID,
        )
        copay = calculate_copay(claim)
        assert copay == Decimal("0.00")

    def test_unknown_plan_type_raises_error(self):
        """Test that None plan type raises ValueError."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=None,  # None should trigger ValueError
        )
        with pytest.raises(ValueError, match="Unknown plan_type"):
            calculate_copay(claim)


        """Test Medicare plan correctly identifies generic by non-zero start."""
        # Test various NDC formats that don't start with '0'
        test_cases = [
            "12345678901",
            "91234567890",
            "55555555555",
        ]
        for ndc in test_cases:
            claim = Claim(
                claim_id="CLM001",
                member_id="1234567890",
                ndc=ndc,
                date_of_service=date.today(),
                quantity=30,
                days_supply=30,
                drug_cost=Decimal("100.00"),
                plan_type=PlanType.MEDICARE,
            )
            copay = calculate_copay(claim)
            assert copay == MEDICARE_GENERIC, f"NDC {ndc} should be treated as generic"
