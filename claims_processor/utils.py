"""Utility functions for parsing and converting values."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .enums import PlanType


def parse_date(value: str) -> Optional[date]:
    """Parse a date string, returning None if empty or invalid."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_int(value: str) -> Optional[int]:
    """Parse an integer string, returning None if empty or invalid."""
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_decimal(value: str) -> Optional[Decimal]:
    """Parse a decimal string, returning None if empty or invalid."""
    if not value:
        return None
    try:
        return Decimal(value)
    except (ValueError, TypeError):
        return None


def parse_plan_type(value: str) -> Optional[PlanType]:
    """Parse a plan type string, returning None if empty or invalid."""
    if not value:
        return None
    try:
        return PlanType(value.lower().strip())
    except ValueError:
        return None
