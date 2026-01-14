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
    member_id: Optional[str] = None  # 10 digits
    ndc: Optional[str] = None  # 11-digit National Drug Code
    date_of_service: Optional[date] = None  # YYYY-MM-DD
    quantity: Optional[int] = None  # Pills dispensed
    days_supply: Optional[int] = None  # Days medication should last
    drug_cost: Optional[Decimal] = None  # Wholesale cost
    plan_type: Optional[PlanType] = None  # Plan type enum
    

@dataclass(frozen=True)
class ProcessedClaim:
    """Data class representing a processed claim."""
    
    claim_id: str
    status: Status
    copay_amount: Optional[Decimal]
    rejection_reason: Optional[str]
    processed_at: datetime


@dataclass(frozen=True)
class ProcessingSummary:
    """Data class representing processing summary statistics."""
    
    total_rows_processed: int
    total_approved: int
    total_rejected: int
    percentage_approved: float
    percentage_rejected: float
    processing_time_seconds: float
