"""Tests for io module."""

import json
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from claims_processor.enums import PlanType, Status
from claims_processor.io import (
    compute_processing_summary,
    read_claims_csv,
    serialize_processed_claim,
    serialize_processing_summary,
    write_processed_claims,
    write_processing_summary,
)
from claims_processor.model import Claim, ProcessedClaim, ProcessingSummary


class TestReadClaimsCsv:
    """Test cases for read_claims_csv function."""

    def test_read_valid_csv(self):
        """Test reading a valid CSV file with proper headers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(
                "claim_id,member_id,ndc,date_of_service,quantity,days_supply,drug_cost,plan_type\n"
            )
            f.write("CLM001,1234567890,08328600301,2025-10-15,30,30,150.00,commercial\n")
            f.write("CLM002,9876543210,12345678901,2025-10-20,60,30,200.00,medicare\n")
            temp_path = f.name

        try:
            claims = list(read_claims_csv(temp_path))
            assert len(claims) == 2
            assert claims[0].claim_id == "CLM001"
            assert claims[0].member_id == "1234567890"
            assert claims[0].ndc == "08328600301"
            assert claims[0].date_of_service == date(2025, 10, 15)
            assert claims[0].quantity == 30
            assert claims[0].days_supply == 30
            assert claims[0].drug_cost == Decimal("150.00")
            assert claims[0].plan_type == PlanType.COMMERCIAL

            assert claims[1].claim_id == "CLM002"
            assert claims[1].plan_type == PlanType.MEDICARE
        finally:
            Path(temp_path).unlink()

    def test_read_csv_with_missing_values(self):
        """Test reading CSV with missing optional values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(
                "claim_id,member_id,ndc,date_of_service,quantity,days_supply,drug_cost,plan_type\n"
            )
            f.write("CLM001,,08328600301,2025-10-15,30,30,150.00,commercial\n")
            f.write("CLM002,1234567890,,2025-10-20,60,30,200.00,medicare\n")
            temp_path = f.name

        try:
            claims = list(read_claims_csv(temp_path))
            assert len(claims) == 2
            assert claims[0].member_id is None
            assert claims[1].ndc is None
        finally:
            Path(temp_path).unlink()

    def test_read_csv_missing_required_columns(self):
        """Test that CSV with missing required columns raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("claim_id,member_id\n")
            f.write("CLM001,1234567890\n")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Missing required columns"):
                list(read_claims_csv(temp_path))
        finally:
            Path(temp_path).unlink()

    def test_read_csv_empty_file(self):
        """Test reading an empty CSV file (only headers)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(
                "claim_id,member_id,ndc,date_of_service,quantity,days_supply,drug_cost,plan_type\n"
            )
            temp_path = f.name

        try:
            claims = list(read_claims_csv(temp_path))
            assert len(claims) == 0
        finally:
            Path(temp_path).unlink()

    def test_read_csv_strips_whitespace(self):
        """Test that CSV reading strips leading and trailing whitespace from all fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(
                "claim_id,member_id,ndc,date_of_service,quantity,days_supply,drug_cost,plan_type\n"
            )
            f.write(" CLM001 , 1234567890 , 08328600301 , 2025-10-15 , 30 , 30 , 150.00 , commercial \n")
            temp_path = f.name

        try:
            claims = list(read_claims_csv(temp_path))
            assert len(claims) == 1
            # Verify all fields with whitespace are properly stripped
            assert claims[0].claim_id == "CLM001"
            assert claims[0].member_id == "1234567890"
            assert claims[0].ndc == "08328600301"
            assert claims[0].date_of_service == date(2025, 10, 15)
            assert claims[0].quantity == 30
            assert claims[0].days_supply == 30
            assert claims[0].drug_cost == Decimal("150.00")
            assert claims[0].plan_type == PlanType.COMMERCIAL
        finally:
            Path(temp_path).unlink()


class TestSerializeProcessedClaim:
    """Test cases for serialize_processed_claim function."""

    def test_serialize_approved_claim(self):
        """Test serializing an approved claim."""
        claim = ProcessedClaim(
            claim_id="CLM001",
            status=Status.APPROVED,
            copay_amount=Decimal("20.00"),
            rejection_reason=None,
            processed_at=datetime(2025, 10, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        result = serialize_processed_claim(claim)

        assert result == {
            "claim_id": "CLM001",
            "status": "APPROVED",
            "copay_amount": 20.0,
            "rejection_reason": None,
            "processed_at": "2025-10-15T12:00:00+00:00",
        }

    def test_serialize_rejected_claim(self):
        """Test serializing a rejected claim."""
        claim = ProcessedClaim(
            claim_id="CLM002",
            status=Status.REJECT,
            copay_amount=None,
            rejection_reason="member_id must be exactly 10 digits",
            processed_at=datetime(2025, 10, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        result = serialize_processed_claim(claim)

        assert result == {
            "claim_id": "CLM002",
            "status": "REJECT",
            "copay_amount": None,
            "rejection_reason": "member_id must be exactly 10 digits",
            "processed_at": "2025-10-15T12:00:00+00:00",
        }


class TestWriteProcessedClaims:
    """Test cases for write_processed_claims function."""

    def test_write_processed_claims(self):
        """Test writing processed claims to JSON file."""
        claims = [
            ProcessedClaim(
                claim_id="CLM001",
                status=Status.APPROVED,
                copay_amount=Decimal("20.00"),
                rejection_reason=None,
                processed_at=datetime(2025, 10, 15, 12, 0, 0, tzinfo=timezone.utc),
            ),
            ProcessedClaim(
                claim_id="CLM002",
                status=Status.REJECT,
                copay_amount=None,
                rejection_reason="Validation error",
                processed_at=datetime(2025, 10, 15, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            write_processed_claims(claims, temp_path)

            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 2
            assert data[0]["claim_id"] == "CLM001"
            assert data[0]["status"] == "APPROVED"
            assert data[0]["copay_amount"] == 20.0
            assert data[1]["claim_id"] == "CLM002"
            assert data[1]["status"] == "REJECT"
            assert data[1]["rejection_reason"] == "Validation error"
        finally:
            Path(temp_path).unlink()

    def test_write_empty_claims_list(self):
        """Test writing an empty list of claims."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            write_processed_claims([], temp_path)

            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data == []
        finally:
            Path(temp_path).unlink()


class TestComputeProcessingSummary:
    """Test cases for compute_processing_summary function."""

    def test_compute_summary(self):
        """Test computing summary with mixed approved and rejected claims."""
        claims = [
            ProcessedClaim(
                claim_id="CLM001",
                status=Status.APPROVED,
                copay_amount=Decimal("20.00"),
                rejection_reason=None,
                processed_at=datetime.now(timezone.utc),
            ),
            ProcessedClaim(
                claim_id="CLM002",
                status=Status.APPROVED,
                copay_amount=Decimal("15.00"),
                rejection_reason=None,
                processed_at=datetime.now(timezone.utc),
            ),
            ProcessedClaim(
                claim_id="CLM003",
                status=Status.REJECT,
                copay_amount=None,
                rejection_reason="Error",
                processed_at=datetime.now(timezone.utc),
            ),
        ]

        summary = compute_processing_summary(claims, 3.45)

        assert summary.total_rows_processed == 3
        assert summary.total_approved == 2
        assert summary.total_rejected == 1
        assert summary.percentage_approved == 66.67
        assert summary.percentage_rejected == 33.33
        assert summary.processing_time_seconds == 3.45

    def test_compute_summary_empty_list(self):
        """Test computing summary with empty claims list."""
        summary = compute_processing_summary([], 0.5)

        assert summary.total_rows_processed == 0
        assert summary.total_approved == 0
        assert summary.total_rejected == 0
        assert summary.percentage_approved == 0.0
        assert summary.percentage_rejected == 0.0
        assert summary.processing_time_seconds == 0.5

    def test_compute_summary_rounds_time(self):
        """Test that processing time is rounded to 2 decimal places."""
        claims = [
            ProcessedClaim(
                claim_id="CLM001",
                status=Status.APPROVED,
                copay_amount=Decimal("20.00"),
                rejection_reason=None,
                processed_at=datetime.now(timezone.utc),
            ),
        ]

        summary = compute_processing_summary(claims, 1.234567)

        assert summary.processing_time_seconds == 1.23

    def test_compute_summary_rounds_percentages(self):
        """Test that percentages are rounded to 2 decimal places."""
        claims = [
            ProcessedClaim(
                claim_id="CLM001",
                status=Status.APPROVED,
                copay_amount=Decimal("20.00"),
                rejection_reason=None,
                processed_at=datetime.now(timezone.utc),
            ),
            ProcessedClaim(
                claim_id="CLM002",
                status=Status.APPROVED,
                copay_amount=Decimal("15.00"),
                rejection_reason=None,
                processed_at=datetime.now(timezone.utc),
            ),
            ProcessedClaim(
                claim_id="CLM003",
                status=Status.REJECT,
                copay_amount=None,
                rejection_reason="Error",
                processed_at=datetime.now(timezone.utc),
            ),
        ]

        summary = compute_processing_summary(claims, 1.0)

        # 2/3 = 66.666... should round to 66.67
        assert summary.percentage_approved == 66.67
        # 1/3 = 33.333... should round to 33.33
        assert summary.percentage_rejected == 33.33


class TestSerializeProcessingSummary:
    """Test cases for serialize_processing_summary function."""

    def test_serialize_summary(self):
        """Test serializing a processing summary."""
        summary = ProcessingSummary(
            total_rows_processed=100,
            total_approved=75,
            total_rejected=25,
            percentage_approved=75.0,
            percentage_rejected=25.0,
            processing_time_seconds=5.5,
        )

        result = serialize_processing_summary(summary)

        assert result == {
            "total_rows_processed": 100,
            "total_approved": 75,
            "total_rejected": 25,
            "percentage_approved": 75.0,
            "percentage_rejected": 25.0,
            "processing_time_seconds": 5.5,
        }


class TestWriteProcessingSummary:
    """Test cases for write_processing_summary function."""

    def test_write_processing_summary(self):
        """Test writing processing summary to JSON file."""
        claims = [
            ProcessedClaim(
                claim_id="CLM001",
                status=Status.APPROVED,
                copay_amount=Decimal("20.00"),
                rejection_reason=None,
                processed_at=datetime.now(timezone.utc),
            ),
            ProcessedClaim(
                claim_id="CLM002",
                status=Status.REJECT,
                copay_amount=None,
                rejection_reason="Error",
                processed_at=datetime.now(timezone.utc),
            ),
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            write_processing_summary(claims, temp_path, 2.5)

            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["total_rows_processed"] == 2
            assert data["total_approved"] == 1
            assert data["total_rejected"] == 1
            assert data["percentage_approved"] == 50.0
            assert data["percentage_rejected"] == 50.0
            assert data["processing_time_seconds"] == 2.5
        finally:
            Path(temp_path).unlink()

    def test_write_summary_empty_claims(self):
        """Test writing summary with empty claims list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            write_processing_summary([], temp_path, 0.1)

            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["total_rows_processed"] == 0
            assert data["total_approved"] == 0
            assert data["total_rejected"] == 0
            assert data["percentage_approved"] == 0.0
            assert data["percentage_rejected"] == 0.0
            assert data["processing_time_seconds"] == 0.1
        finally:
            Path(temp_path).unlink()
