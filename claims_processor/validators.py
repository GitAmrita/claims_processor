from datetime import date, datetime
from typing import List
import logging
from functools import lru_cache
import requests

from .model import Claim

logger = logging.getLogger(__name__)

OPENFDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"
TIMEOUT_SECONDS = 5  # seconds


@lru_cache(maxsize=1024)
def is_valid_ndc_online(ndc: str) -> bool:
    params = {
        "search": f'product_ndc:"{ndc}"',
        "limit": 1,
    }

    try:
        response = requests.get(
            OPENFDA_NDC_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            return False

        response.raise_for_status()
        data = response.json()
        return bool(data.get("results"))

    except requests.exceptions.RequestException as exc:
        print(f"OpenFDA NDC validation failed for {ndc}: {exc}")
        return False


def validate_claim(claim: Claim, validate_ndc_online: bool =False) -> List[str]:
    
    """
    Validate a Claim object.
    Returns a list of error messages. Empty list = valid claim.
    """

    errors: List[str] = []

    # Check for required fields
    if not claim.member_id:
        errors.append("member_id is required")
    if not claim.ndc:
        errors.append("ndc is required")
    if not claim.date_of_service:
        errors.append("date_of_service is required")
    if claim.quantity is None:
        errors.append("quantity is required")
    if claim.days_supply is None:
        errors.append("days_supply is required")
    if claim.drug_cost is None:
        errors.append("drug_cost is required")
    if not claim.plan_type:
        errors.append("plan_type is required")

    # Only continue with format and value validations if fields are present
    if claim.member_id:
        if not claim.member_id.isdigit() or len(claim.member_id) != 10:
            errors.append("member_id must be exactly 10 digits")

    if claim.ndc:
        if not claim.ndc.isdigit() or len(claim.ndc) != 11:
            errors.append("ndc must be exactly 11 digits")
        elif validate_ndc_online and not is_valid_ndc_online(claim.ndc):
            errors.append("ndc is not a valid FDA NDC")

    if claim.date_of_service:
        if claim.date_of_service > date.today():
            errors.append("date_of_service cannot be in the future")

    if claim.quantity is not None and claim.quantity <= 0:
        errors.append("quantity must be positive")

    if claim.days_supply is not None and not (1 <= claim.days_supply <= 90):
        errors.append("days_supply must be between 1 and 90")

    if claim.drug_cost is not None and claim.drug_cost <= 0:
        errors.append("drug_cost must be positive")

    return errors
    """
    Validate a Claim object.
    Returns a list of error messages. Empty list = valid claim.
    """
    errors: List[str] = []

    # Validate member_id
    if not claim.member_id.isdigit() or len(claim.member_id) != 10:
        errors.append("member_id must be exactly 10 digits")

   # Validate NDC format (11 digits)
    if not claim.ndc.isdigit() or len(claim.ndc) != 11:
        errors.append("ndc must be exactly 11 digits")
    else:
        # Optional: validate against openFDA API
        if validate_ndc_online and not is_valid_ndc_online(claim.ndc):
            errors.append("ndc is not a valid FDA NDC")

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


    """
    Validate NDC using OpenFDA drug label API.
    Returns True if NDC exists, False otherwise.
    """
    params = {
        "search": f'openfda.product_ndc:"{ndc}"',
        "limit": 1,
    }

    try:
        response = requests.get(
            OPENFDA_LABEL_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code == 404:
            # No matching records
            return False

        response.raise_for_status()

        data = response.json()
        return "results" in data and len(data["results"]) > 0

    except requests.exceptions.RequestException as exc:
        # In real systems: log + allow fallback behavior
        print(f"Failed to validate NDC {ndc} against openFDA API: {exc}")
        return False