import csv
import json
from typing import Iterator, List, Optional

from .model import Claim, ProcessedClaim, ProcessingSummary
from .enums import Status
from .utils import parse_date, parse_int, parse_decimal, parse_plan_type


REQUIRED_COLUMNS = {
    "claim_id",
    "member_id",
    "ndc",
    "date_of_service",
    "quantity",
    "days_supply",
    "drug_cost",
    "plan_type",
}


def read_claims_csv(file_path: str) -> Iterator[Claim]:
    """
    Memory-safe CSV reader.
    Streams claims one row at a time without loading the full file into memory.
    """
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        _validate_headers(reader.fieldnames)

        for row_number, row in enumerate(reader, start=2):
            yield _parse_row(row)

def _parse_row(row: dict) -> Claim:
    """Parse a CSV row into a Claim object, handling missing values gracefully."""
    # Get values with defaults for missing keys, strip whitespace
    claim_id = row.get("claim_id", "").strip()
    member_id = row.get("member_id", "").strip() or None
    ndc = row.get("ndc", "").strip() or None
    date_of_service = parse_date(row.get("date_of_service", "").strip())
    quantity = parse_int(row.get("quantity", "").strip())
    days_supply = parse_int(row.get("days_supply", "").strip())
    drug_cost = parse_decimal(row.get("drug_cost", "").strip())
    plan_type = parse_plan_type(row.get("plan_type", "").strip())
    
    return Claim(
        claim_id=claim_id,
        member_id=member_id,
        ndc=ndc,
        date_of_service=date_of_service,
        quantity=quantity,
        days_supply=days_supply,
        drug_cost=drug_cost,
        plan_type=plan_type,
    )

def _validate_headers(headers: Optional[List[str]]) -> None:
    if not headers:
        raise ValueError("CSV file is missing headers")

    missing = REQUIRED_COLUMNS - set(headers)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

def serialize_processed_claim(claim: ProcessedClaim) -> dict:
    """
    Convert ProcessedClaim domain object to JSON-serializable dict.
    """
    return {
        "claim_id": claim.claim_id,
        "status": claim.status.value,
        "copay_amount": (
            float(claim.copay_amount)
            if claim.copay_amount is not None
            else None
        ),
        "rejection_reason": claim.rejection_reason,
        "processed_at": claim.processed_at.isoformat(),
    }

def write_processed_claims(
    claims: List[ProcessedClaim],
    output_path: str,
) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [serialize_processed_claim(c) for c in claims],
            f,
            indent=2,
        )


def compute_processing_summary(
    claims: List[ProcessedClaim],
    processing_time_seconds: float,
) -> ProcessingSummary:
    """
    Compute processing summary statistics from processed claims.
    
    Args:
        claims: List of processed claims
        processing_time_seconds: Time taken to process all claims
    
    Returns:
        ProcessingSummary object with computed statistics
    """
    total_processed = len(claims)
    total_approved = sum(1 for claim in claims if claim.status == Status.APPROVED)
    total_rejected = sum(1 for claim in claims if claim.status == Status.REJECT)

    # Calculate percentages, handling division by zero
    percentage_approved = (
        round((total_approved / total_processed * 100), 2) if total_processed > 0 else 0.0
    )
    percentage_rejected = (
        round((total_rejected / total_processed * 100), 2) if total_processed > 0 else 0.0
    )

    return ProcessingSummary(
        total_rows_processed=total_processed,
        total_approved=total_approved,
        total_rejected=total_rejected,
        percentage_approved=percentage_approved,
        percentage_rejected=percentage_rejected,
        processing_time_seconds=round(processing_time_seconds, 2),
    )


def serialize_processing_summary(summary: ProcessingSummary) -> dict:
    """
    Convert ProcessingSummary domain object to JSON-serializable dict.
    """
    return {
        "total_rows_processed": summary.total_rows_processed,
        "total_approved": summary.total_approved,
        "total_rejected": summary.total_rejected,
        "percentage_approved": summary.percentage_approved,
        "percentage_rejected": summary.percentage_rejected,
        "processing_time_seconds": summary.processing_time_seconds,
    }


def write_processing_summary(
    claims: List[ProcessedClaim],
    summary_path: str,
    processing_time_seconds: float,
) -> None:
    """
    Compute and write processing summary statistics to a JSON file.
    
    Args:
        claims: List of processed claims
        summary_path: Path to write the summary JSON file
        processing_time_seconds: Time taken to process all claims
    """
    summary = compute_processing_summary(claims, processing_time_seconds)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(serialize_processing_summary(summary), f, indent=2)

