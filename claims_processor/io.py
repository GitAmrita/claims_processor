import csv
from typing import Iterator, List, Optional

from .model import Claim, ProcessedClaim
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
    import json

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [serialize_processed_claim(c) for c in claims],
            f,
            indent=2,
        )

