import csv
from datetime import datetime, date
from decimal import Decimal
from typing import Iterator, List, Optional

from .model import Claim, ProcessedClaim
from .enums import PlanType


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
            try:
                yield _parse_row(row)
            except Exception as exc:
                raise ValueError(
                    f"Error parsing row {row_number}: {exc}"
                ) from exc

def _parse_row(row: dict) -> Claim:
    return Claim(
        claim_id=row["claim_id"].strip(),
        member_id=row["member_id"].strip(),
        ndc=row["ndc"].strip(),
        date_of_service=_parse_date(row["date_of_service"]),
        quantity=int(row["quantity"]),
        days_supply=int(row["days_supply"]),
        drug_cost=Decimal(row["drug_cost"]),
        plan_type=PlanType(row["plan_type"].lower()),
    )

def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


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

