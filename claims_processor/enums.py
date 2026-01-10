"""Enumerations for claims processor."""

from enum import Enum


class PlanType(Enum):
    """Plan type enumeration."""
    
    COMMERCIAL = "commercial"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"


class Status(Enum):
    """Claim processing status enumeration."""
    
    APPROVED = "APPROVED"
    REJECT = "REJECT"
