from decimal import Decimal
from .model import Claim
from .enums import PlanType

# Copay thresholds
COMMERCIAL_MIN = Decimal("10.00")
COMMERCIAL_MAX = Decimal("100.00")
COMMERCIAL_RATE = Decimal("0.20") # 20% of drug_cost

MEDICARE_GENERIC = Decimal("5.00")
MEDICARE_BRAND = Decimal("15.00")


def calculate_copay(claim: Claim) -> Decimal:
    """
    Calculate copay for a claim based on plan type.
    Returns Decimal copay.
    """
    if claim.plan_type == PlanType.COMMERCIAL:
        return _calculate_commercial_copay(claim.drug_cost)

    elif claim.plan_type == PlanType.MEDICARE:
        return _calculate_medicare_copay(claim)

    elif claim.plan_type == PlanType.MEDICAID:
        return Decimal("0.00")

    else:
        raise ValueError(f"Unknown plan_type: {claim.plan_type}")


def _calculate_commercial_copay(drug_cost: Decimal) -> Decimal:
    copay = (drug_cost * COMMERCIAL_RATE).quantize(Decimal("0.01"))
    if copay < COMMERCIAL_MIN:
        copay = COMMERCIAL_MIN
    elif copay > COMMERCIAL_MAX:
        copay = COMMERCIAL_MAX
    return copay


def _calculate_medicare_copay(claim: Claim) -> Decimal:
    """
    Medicare rules:
    - $5 flat copay for generic
    - $15 for brand (if NDC starts with '0')
    """
    if claim.ndc.startswith("0"):
        return MEDICARE_BRAND
    else:
        return MEDICARE_GENERIC
