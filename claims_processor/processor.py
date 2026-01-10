from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from .model import Claim, ProcessedClaim
from .enums import Status
from .validators import validate_claim
from .copay import calculate_copay  # per plan type

MAX_PILLS_PER_DAY = 3  # business rule


def process_claim(claim: Claim) -> ProcessedClaim:
    """
    Process a single Claim:
    - Validate
    - Apply rejection rules
    - Calculate copay if approved
    """
    errors = validate_claim(claim)

    # Reject if validation fails
    if errors:
        return _reject(claim, "; ".join(errors))

    # Reject if too many pills per day
    if claim.quantity / claim.days_supply > MAX_PILLS_PER_DAY:
        return _reject(claim, "Too many pills per day")

    # Calculate copay
    copay: Optional[Decimal] = calculate_copay(claim)

    return ProcessedClaim(
        claim_id=claim.claim_id,
        status=Status.APPROVED,
        copay_amount=copay,
        rejection_reason=None,
        processed_at=datetime.now(timezone.utc),
    )


def _reject(claim: Claim, reason: str) -> ProcessedClaim:
    """
    Return a ProcessedClaim representing a rejected claim.
    """
    return ProcessedClaim(
        claim_id=claim.claim_id,
        status=Status.REJECT,
        copay_amount=None,
        rejection_reason=reason,
        processed_at=datetime.now(timezone.utc),
    )
