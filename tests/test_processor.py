"""Tests for processor module."""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from claims_processor.model import Claim, ProcessedClaim
from claims_processor.enums import PlanType, Status
from claims_processor.processor import process_claim, _reject, MAX_PILLS_PER_DAY


class TestProcessClaim:
    """Test cases for process_claim function."""

    @patch("claims_processor.processor.calculate_copay")
    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_approved(self, mock_validate, mock_calculate_copay):
        """Test successful processing of a valid claim."""
        # Arrange
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
        mock_validate.return_value = []  # No validation errors
        mock_calculate_copay.return_value = Decimal("20.00")

        # Act
        result = process_claim(claim)

        # Assert
        assert result.claim_id == "CLM001"
        assert result.status == Status.APPROVED
        assert result.copay_amount == Decimal("20.00")
        assert result.rejection_reason is None
        assert isinstance(result.processed_at, datetime)
        mock_validate.assert_called_once_with(claim, validate_ndc_online=True, ndc_cache=None)
        mock_calculate_copay.assert_called_once_with(claim)

    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_rejected_validation_errors(self, mock_validate):
        """Test rejection when validation returns errors."""
        # Arrange
        claim = Claim(
            claim_id="CLM004",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        mock_validate.return_value = ["member_id must be exactly 10 digits", "ndc is not a valid FDA NDC"]

        # Act
        result = process_claim(claim)

        # Assert
        assert result.status == Status.REJECT
        assert result.copay_amount is None
        assert result.rejection_reason == "member_id must be exactly 10 digits; ndc is not a valid FDA NDC"
        assert isinstance(result.processed_at, datetime)

    @patch("claims_processor.processor.calculate_copay")
    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_rejected_too_many_pills_per_day(self, mock_validate, mock_calculate_copay):
        """Test rejection when pills per day is just over maximum."""
        # Arrange
        claim = Claim(
            claim_id="CLM008",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=91,  # 91 pills
            days_supply=30,  # 30 days = 3.033 pills/day > 3
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        mock_validate.return_value = []

        # Act
        result = process_claim(claim)

        # Assert
        assert result.status == Status.REJECT
        assert result.rejection_reason == "Too many pills per day"

    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_rejected_quantity_none(self, mock_validate):
        """Test rejection when quantity is None (defensive check)."""
        # Arrange
        claim = Claim(
            claim_id="CLM009",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=None,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        mock_validate.return_value = []

        # Act
        result = process_claim(claim)

        # Assert
        assert result.status == Status.REJECT
        assert result.rejection_reason == "quantity and days_supply are required"

    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_rejected_days_supply_none(self, mock_validate):
        """Test rejection when days_supply is None (defensive check)."""
        # Arrange
        claim = Claim(
            claim_id="CLM010",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=None,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        mock_validate.return_value = []

        # Act
        result = process_claim(claim)

        # Assert
        assert result.status == Status.REJECT
        assert result.rejection_reason == "quantity and days_supply are required"

    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_rejected_plan_type_none(self, mock_validate):
        """Test rejection when plan_type is None (defensive check)."""
        # Arrange
        claim = Claim(
            claim_id="CLM011",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=None,
        )
        mock_validate.return_value = []

        # Act
        result = process_claim(claim)

        # Assert
        assert result.status == Status.REJECT
        assert result.rejection_reason == "plan_type and drug_cost are required"

    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_rejected_drug_cost_none(self, mock_validate):
        """Test rejection when drug_cost is None (defensive check)."""
        # Arrange
        claim = Claim(
            claim_id="CLM012",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=None,
            plan_type=PlanType.COMMERCIAL,
        )
        mock_validate.return_value = []

        # Act
        result = process_claim(claim)

        # Assert
        assert result.status == Status.REJECT
        assert result.rejection_reason == "plan_type and drug_cost are required"

    @patch("claims_processor.processor.calculate_copay")
    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_processed_at_is_utc(self, mock_validate, mock_calculate_copay):
        """Test that processed_at timestamp is in UTC timezone."""
        # Arrange
        claim = Claim(
            claim_id="CLM013",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        mock_validate.return_value = []
        mock_calculate_copay.return_value = Decimal("20.00")

        # Act
        result = process_claim(claim)

        # Assert
        assert result.processed_at.tzinfo == timezone.utc

    @patch("claims_processor.processor.calculate_copay")
    @patch("claims_processor.processor.validate_claim")
    def test_process_claim_with_ndc_cache(self, mock_validate, mock_calculate_copay):
        """Test processing claim with NDC cache provided."""
        # Arrange
        claim = Claim(
            claim_id="CLM015",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        ndc_cache = {"12345678901": True}
        mock_validate.return_value = []  # No validation errors
        mock_calculate_copay.return_value = Decimal("20.00")

        # Act
        result = process_claim(claim, ndc_cache=ndc_cache)

        # Assert
        assert result.status == Status.APPROVED
        mock_validate.assert_called_once_with(claim, validate_ndc_online=True, ndc_cache=ndc_cache)
        mock_calculate_copay.assert_called_once_with(claim)

    def test_reject_creates_rejected_processed_claim(self):
        """Test that _reject creates a properly formatted rejected claim."""
        # Arrange
        claim = Claim(
            claim_id="CLM014",
            member_id="1234567890",
            ndc="12345678901",
            date_of_service=date.today() - timedelta(days=1),
            quantity=30,
            days_supply=30,
            drug_cost=Decimal("100.00"),
            plan_type=PlanType.COMMERCIAL,
        )
        reason = "Test rejection reason"

        # Act
        result = _reject(claim, reason)

        # Assert
        assert result.claim_id == "CLM014"
        assert result.status == Status.REJECT
        assert result.copay_amount is None
        assert result.rejection_reason == reason
        assert isinstance(result.processed_at, datetime)
        assert result.processed_at.tzinfo == timezone.utc
