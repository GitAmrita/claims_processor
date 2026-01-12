"""Tests for validators module."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from claims_processor.model import Claim
from claims_processor.enums import PlanType
from claims_processor.validators import _validate_format_and_values, _validate_required_fields, validate_claim, normalize_11_to_fda_product_ndc


class TestValidate:
    """Test cases for _validate_format_and_values function."""

    def test_valid_claim_no_errors(self):
        """Test that a valid claim returns no errors."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert errors == []

    def test_member_id_too_short(self):
        """Test that member_id with less than 10 digits returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="123456789",  # 9 digits
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "member_id must be exactly 10 digits" in errors

    def test_member_id_too_long(self):
        """Test that member_id with more than 10 digits returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="12345678901",  # 11 digits
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "member_id must be exactly 10 digits" in errors

    def test_member_id_non_digit(self):
        """Test that member_id with non-digit characters returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="123456789a",  # contains letter
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "member_id must be exactly 10 digits" in errors

    def test_member_id_none(self):
        """Test that None member_id doesn't trigger format validation."""
        claim = Claim(
            claim_id="CLM001",
            member_id=None,
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_required_fields(claim)
        assert "member_id is required" in errors

    def test_ndc_too_short(self):
        """Test that NDC with less than 11 digits returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="1234567890",  # 10 digits
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "ndc must be exactly 11 digits" in errors

    def test_ndc_too_long(self):
        """Test that NDC with more than 11 digits returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="123456789012",  # 12 digits
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "ndc must be exactly 11 digits" in errors

    def test_ndc_non_digit(self):
        """Test that NDC with non-digit characters returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="1234567890a",  # contains letter
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "ndc must be exactly 11 digits" in errors
    
    def test_ndc_none(self):
        """Test that None member_id doesn't trigger format validation."""
        claim = Claim(
            claim_id="CLM001",
            member_id=1234567890,
            ndc="",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_required_fields(claim)
        assert "ndc is required" in errors

    @patch("claims_processor.validators.is_valid_ndc_online")
    def test_ndc_online_validation_valid(self, mock_is_valid):
        """Test that valid NDC passes online validation when enabled."""
        mock_is_valid.return_value = True
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=True)
        assert "ndc is not a valid FDA NDC" not in errors
        mock_is_valid.assert_called_once_with("12345678901")

    @patch("claims_processor.validators.is_valid_ndc_online")
    def test_ndc_online_validation_invalid(self, mock_is_valid):
        """Test that invalid NDC fails online validation when enabled."""
        mock_is_valid.return_value = False
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=True)
        assert "ndc is not a valid FDA NDC" in errors
        mock_is_valid.assert_called_once_with("12345678901")

    @patch("claims_processor.validators.is_valid_ndc_online")
    def test_ndc_online_validation_disabled(self, mock_is_valid):
        """Test that online validation is skipped when disabled."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "ndc is not a valid FDA NDC" not in errors
        mock_is_valid.assert_not_called()

    def test_date_of_service_future(self):
        """Test that future date_of_service returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() + timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "date_of_service cannot be in the future" in errors

    def test_date_of_service_today(self):
        """Test that today's date is valid."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today(),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "date_of_service cannot be in the future" not in errors

    def test_date_of_service_past(self):
        """Test that past date_of_service is valid."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "date_of_service cannot be in the future" not in errors

    def test_date_of_service_none(self):
        """Test that None date_of_service doesn't trigger validation."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=None,
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors =  _validate_required_fields(claim)
        assert "date_of_service is required" in errors

    def test_quantity_zero(self):
        """Test that quantity of 0 returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=0,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "quantity must be positive" in errors

    def test_quantity_negative(self):
        """Test that negative quantity returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=-10,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "quantity must be positive" in errors

    def test_quantity_positive(self):
        """Test that positive quantity is valid."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "quantity must be positive" not in errors

    def test_quantity_none(self):
        """Test that None quantity doesn't trigger validation."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=None,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors =  _validate_required_fields(claim)
        assert "quantity is required" in errors

    def test_days_supply_too_low(self):
        """Test that days_supply less than 1 returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=0,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "days_supply must be between 1 and 90" in errors

    def test_days_supply_too_high(self):
        """Test that days_supply greater than 90 returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=91,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "days_supply must be between 1 and 90" in errors

    def test_days_supply_valid_range(self):
        """Test that days_supply between 1 and 90 is valid."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "days_supply must be between 1 and 90" not in errors


        """Test that days_supply of 90 is valid."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=90,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "days_supply must be between 1 and 90" not in errors

    def test_days_supply_none(self):
        """Test that None days_supply doesn't trigger validation."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=None,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors =  _validate_required_fields(claim)
        assert "days_supply is required" in errors

    def test_drug_cost_zero(self):
        """Test that drug_cost of 0 returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("0.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "drug_cost must be positive" in errors

    def test_drug_cost_negative(self):
        """Test that negative drug_cost returns error."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("-10.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "drug_cost must be positive" in errors

    def test_drug_cost_positive(self):
        """Test that positive drug_cost is valid."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert "drug_cost must be positive" not in errors

    def test_drug_cost_none(self):
        """Test that None drug_cost doesn't trigger validation."""
        claim = Claim(
            claim_id="CLM001",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=None,
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_required_fields(claim)
        assert "drug_cost is required" in errors

    def test_multiple_errors(self):
        """Test that multiple validation errors are all returned."""
        claim = Claim(
            claim_id="CLM001",
            member_id="12345",  # too short
            ndc="1234567890",  # too short
            date_of_service=date.today() + timedelta(days=1),  # future
            quantity=0,  # invalid
            days_supply=100,  # too high
            drug_cost=Decimal("0.00"),  # invalid
            plan_type=PlanType.COMMERCIAL,
        )
        errors = _validate_format_and_values(claim, validate_ndc_online=False)
        assert len(errors) >= 6
        assert "member_id must be exactly 10 digits" in errors
        assert "ndc must be exactly 11 digits" in errors
        assert "date_of_service cannot be in the future" in errors
        assert "quantity must be positive" in errors
        assert "days_supply must be between 1 and 90" in errors
        assert "drug_cost must be positive" in errors

    def test_validate_claim(self):
        # Arrange
        fake_claim = object()

        required_field_errors = [
            "member_id is required",
            "ndc is required",
        ]
        format_value_errors = [
            "ndc format is invalid",
        ]
        with patch(
            "claims_processor.validators._validate_required_fields",
            return_value=required_field_errors,
        ) as mock_required, patch(
            "claims_processor.validators._validate_format_and_values",
            return_value=format_value_errors,
        ) as mock_format:

            # Act
            errors = validate_claim(fake_claim, validate_ndc_online=True)

            # Assert
            assert len(errors) == 3
            assert errors == required_field_errors + format_value_errors

            mock_required.assert_called_once_with(fake_claim)
            mock_format.assert_called_once_with(fake_claim, True)

    def test_normalize_11_to_fda_product_ndc_strips_leading_zero(self):
        ndc_11 = "01234567890"
        result = normalize_11_to_fda_product_ndc(ndc_11)
        assert result == "12345-678"
    
    def test_normalize_11_to_fda_product_ndc_without_leading_zero(self):
        ndc_11 = "12345678901"
        result = normalize_11_to_fda_product_ndc(ndc_11)
        assert result == "12345-678"

    def test_normalize_11_to_fda_product_ndc_multiple_leading_zeros(self):
        ndc_11 = "0008328600301"
        result = normalize_11_to_fda_product_ndc(ndc_11)
        assert result == "00832-860"

    def test_normalize_11_to_fda_product_ndc_shorter_length(self):
        ndc_11 = "123"
        result = normalize_11_to_fda_product_ndc(ndc_11)
        assert result == "123-"

    def test_normalize_11_to_fda_product_ndc_non_digit_input(self):
        ndc_11 = ""
        result = normalize_11_to_fda_product_ndc(ndc_11)
        assert result == "-"