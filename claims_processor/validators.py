from datetime import date, datetime
from typing import List
import logging
from functools import lru_cache
import requests

from .model import Claim

logger = logging.getLogger(__name__)

OPENFDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"
TIMEOUT_SECONDS = 5  # seconds

def normalize_11_to_fda_product_ndc(ndc_11: str) -> str:

    """
    Normalize an 11-digit pharmacy claim NDC to the FDA `product_ndc` format
    (labeler-product).

    Assumption / Simplification (Intentional for this implementation):
    -------------------------------------------------
    This logic assumes the incoming NDC is already in the standardized
    5-4-2 claims format where ONLY the labeler segment is left-padded
    with a leading zero.
        Example handled here:
            08328600301  →  83286-003
    Under this assumption, we detect and remove a single leading zero
    from the full NDC string and then slice fixed positions.

    Real-world Note:
    ----------------
    In real pharmacy data, 11-digit NDCs may originate from multiple
    FDA formats (4-4-2, 5-3-2, or 5-4-1) and be padded at different
    segment levels (labeler, product, or package).

    A fully robust implementation would:
      • Identify which segment is padded
      • Preserve fixed 5-4-2 positional slicing
      • Normalize each segment independently
    """

    # labeler padded , remove leading 0
    if ndc_11.startswith("0"):
        ndc = ndc_11[1:]
    else:
        ndc = ndc_11
    # no need to test for length, slicing is forgiving
    labeler = ndc[:5]
    product = ndc[5:8]

    return f"{labeler}-{product}"


@lru_cache(maxsize=1024)
def is_valid_ndc_online(ndc: str) -> bool:
    normalized_ndc = normalize_11_to_fda_product_ndc(ndc)
    # https://api.fda.gov/drug/ndc.json?search=product_ndc:"83286-003"
    params = {
        "search": f'product_ndc:"{normalized_ndc}"',
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


def _validate_required_fields(claim: Claim) -> List[str]:
    """
    Validate that all required fields are present.
    Returns a list of error messages for missing fields.
    """
    errors: List[str] = []

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

    return errors


def _validate_format_and_values(claim: Claim, validate_ndc_online: bool) -> List[str]:
    """
    Validate format and values of claim fields.
    Returns a list of error messages for format/value violations.
    """
    errors: List[str] = []

    # Only validate format and values if fields are present
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


def validate_claim(claim: Claim, validate_ndc_online: bool = True) -> List[str]:
    """
    Validate a Claim object.
    Returns a list of error messages. Empty list = valid claim.
    """
    errors: List[str] = []
    errors.extend(_validate_required_fields(claim))
    errors.extend(_validate_format_and_values(claim, validate_ndc_online))
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