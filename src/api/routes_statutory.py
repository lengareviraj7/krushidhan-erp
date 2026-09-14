"""
API Route Handlers for Statutory Agriculture Department Registers.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from src.db.connection import get_db_manager
from src.services.statutory_service import StatutoryService

router = APIRouter(prefix="/api/statutory", tags=["Statutory Agriculture Registers"])


@router.get("/fertilizer-register")
def get_fertilizer_register(from_date: Optional[str] = None, to_date: Optional[str] = None):
    """Monthly Fertilizer Stock & Sale Register for FCO Audits."""
    svc = StatutoryService(get_db_manager())
    return svc.get_fertilizer_register(from_date, to_date)


@router.get("/pesticide-register")
def get_pesticide_register(from_date: Optional[str] = None, to_date: Optional[str] = None):
    """Insecticides and Pesticides Sale Register."""
    svc = StatutoryService(get_db_manager())
    return svc.get_pesticide_register(from_date, to_date)


@router.get("/seed-register")
def get_seed_register(from_date: Optional[str] = None, to_date: Optional[str] = None):
    """Hybrid and Certified Seed Sale Register."""
    svc = StatutoryService(get_db_manager())
    return svc.get_seed_register(from_date, to_date)
