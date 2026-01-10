from datetime import date, datetime
from typing import List

from .model import Claim


def validate_claim(claim: Claim) -> List[str]:
    """
    Validate a Claim object.
    Returns a list of error messages. Empty list = valid claim.
    """
    errors: List[str] = []

    # Validate member_id
    if not claim.member_id.isdigit() or len(claim.member_id) != 10:
        errors.append("member_id must be exactly 10 digits")

    # Validate NDC
    if not claim.ndc.isdigit() or len(claim.ndc) != 11:
        errors.append("ndc must be exactly 11 digits")

    # Validate date_of_service is not future-dated
    if claim.date_of_service > date.today():
        errors.append("date_of_service cannot be in the future")

    # Validate quantity
    if claim.quantity <= 0:
        errors.append("quantity must be positive")

    # Validate days_supply
    if not (1 <= claim.days_supply <= 90):
        errors.append("days_supply must be between 1 and 90")

    # Validate drug_cost
    if claim.drug_cost <= 0:
        errors.append("drug_cost must be positive")

    return errors
