"""Claim data model."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .enums import PlanType, Status


@dataclass(frozen=True)
class Claim:


    """Data class representing a raw claim."""
    
    claim_id: str  # Unique identifier
    member_id: str  # 10 digits
    ndc: str  # 11-digit National Drug Code
    date_of_service: date  # YYYY-MM-DD
    quantity: int  # Pills dispensed
    days_supply: int  # Days medication should last
    drug_cost: Decimal  # Wholesale cost
    plan_type: PlanType  # Plan type enum
    

@dataclass(frozen=True)
class ProcessedClaim:

    """Data class representing a processed claim."""
    
    claim_id: str
    status: Status
    copay_amount: Optional[Decimal]
    rejection_reason: Optional[str]
    processed_at: datetime