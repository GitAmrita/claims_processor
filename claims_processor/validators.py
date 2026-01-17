from datetime import date, datetime
from typing import List, Dict, Set
import logging
import asyncio
import aiohttp

from .config import VALIDATE_NDC_ONLINE

from .model import Claim

logger = logging.getLogger(__name__)

OPENFDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"
TIMEOUT_SECONDS = 5  # seconds
MAX_CONCURRENT_NDC_REQUESTS = 200  # Maximum concurrent NDC API calls rate limited

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


def _validate_format_and_values(claim: Claim, validate_ndc_online: bool, ndc_cache: Dict[str, bool] = None) -> List[str]:
    """
    Validate format and values of claim fields.
    Returns a list of error messages for format/value violations.
    
    Args:
        claim: Claim to validate
        validate_ndc_online: Whether to validate NDC online
        ndc_cache: Optional dict mapping NDC -> bool for cached validation results
    """
    errors: List[str] = []

    # Only validate format and values if fields are present
    if claim.member_id:
        if not claim.member_id.isdigit() or len(claim.member_id) != 10:
            errors.append("member_id must be exactly 10 digits")

    if claim.ndc:
        if not claim.ndc.isdigit() or len(claim.ndc) != 11:
            errors.append("ndc must be exactly 11 digits")
        elif validate_ndc_online:
            # Use cache if provided (parallel processing always provides cache)
            if ndc_cache is not None:
                if claim.ndc not in ndc_cache:
                    # Should not happen if cache is properly populated
                    errors.append("ndc validation not found in cache")
                elif not ndc_cache[claim.ndc]:
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


def validate_claim(claim: Claim, validate_ndc_online: bool = VALIDATE_NDC_ONLINE, ndc_cache: Dict[str, bool] = None) -> List[str]:
    """
    Validate a Claim object.
    Returns a list of error messages. Empty list = valid claim.
    
    Args:
        claim: Claim to validate
        validate_ndc_online: Whether to validate NDC online (defaults to config value)
        ndc_cache: Optional dict mapping NDC -> bool for cached validation results
    """
    errors: List[str] = []
    errors.extend(_validate_required_fields(claim))
    errors.extend(_validate_format_and_values(claim, validate_ndc_online, ndc_cache))
    return errors


async def _validate_single_ndc_async(session: aiohttp.ClientSession, ndc: str, semaphore: asyncio.Semaphore) -> bool:
    """Validate a single NDC asynchronously with semaphore-controlled concurrency."""
    # https://api.fda.gov/drug/ndc.json?search=product_ndc:"83286-003"
    normalized_ndc = normalize_11_to_fda_product_ndc(ndc)
    params = {
        "search": f'product_ndc:"{normalized_ndc}"',
        "limit": 1,
    }

    
    # Acquire semaphore to limit concurrent requests
    async with semaphore:
        try:
            async with session.get(
                OPENFDA_NDC_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as response:
                if response.status == 404:
                    return False
                response.raise_for_status()
                data = await response.json()
                return bool(data.get("results"))
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning(f"OpenFDA NDC validation failed for {ndc}: {exc}")
            return False


async def validate_ndcs_batch_async(ndcs: Set[str]) -> Dict[str, bool]:
    """
    Validate multiple NDCs concurrently using async HTTP requests.
    
    Args:
        ndcs: Set of NDC strings to validate
        
    Returns:
        Dict mapping NDC -> bool (True if valid, False otherwise)
    """
    if not ndcs:
        return {}
    
    # Use cached results for NDCs we've already validated
    results = {}
    uncached_ndcs = set()
    
    for ndc in ndcs:
        if ndc in _ndc_cache:
            results[ndc] = _ndc_cache[ndc]
        else:
            uncached_ndcs.add(ndc)
    #  NDCs are already cached, return the results
    if not uncached_ndcs:
        return results
    
    # Validate uncached NDCs concurrently (limited by semaphore)
    # Create semaphore within the async context (each worker process has its own event loop)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_NDC_REQUESTS)
    
    async with aiohttp.ClientSession() as session:
        tasks = [_validate_single_ndc_async(session, ndc, semaphore) for ndc in uncached_ndcs]
        validation_results = await asyncio.gather(*tasks)
        
        # Update cache and results
        for ndc, is_valid in zip(uncached_ndcs, validation_results):
            _ndc_cache[ndc] = is_valid
            results[ndc] = is_valid
    
    return results


# In-memory cache for NDC validation results (per-process, not shared across workers)
# Each worker process created by ProcessPoolExecutor has its own copy of this cache
_ndc_cache: Dict[str, bool] = {}
