from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict

from .model import Claim, ProcessedClaim
from .enums import Status
from .validators import validate_claim
from .copay import calculate_copay  # per plan type

MAX_PILLS_PER_DAY = 3  # business rule


def process_claim(claim: Claim, ndc_cache: Optional[Dict[str, bool]] = None) -> ProcessedClaim:
    """
    Process a single Claim:
    - Validate
    - Apply rejection rules
    - Calculate copay if approved
    
    Args:
        claim: Claim to process
        ndc_cache: Optional dict mapping NDC -> bool for cached validation results
    """
    errors = validate_claim(claim, validate_ndc_online=True, ndc_cache=ndc_cache)

    # Reject if validation fails
    if errors:
        return _reject(claim, "; ".join(errors))

    # Additional defensive checks to help type checker with static validations(validation should have caught these)
    if claim.quantity is None or claim.days_supply is None:
        return _reject(claim, "quantity and days_supply are required")

    # Reject if too many pills per day
    if claim.quantity / claim.days_supply > MAX_PILLS_PER_DAY:
        return _reject(claim, "Too many pills per day")

    # Additional defensive checks to help type checker with static validations(validation should have caught these)
    if claim.plan_type is None or claim.drug_cost is None:
        return _reject(claim, "plan_type and drug_cost are required")
    
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
