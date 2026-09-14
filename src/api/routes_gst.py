"""
API Route Handlers for Statutory GST Returns and HSN Analytics.
"""
from __future__ import annotations

from fastapi import APIRouter
from src.db.connection import get_db_manager
from src.services.gst_service import GSTService

router = APIRouter(prefix="/api/gst", tags=["GST"])


@router.get("/gstr1-b2b")
def get_gstr1_b2b(from_date: str, to_date: str):
    svc = GSTService(get_db_manager())
    return svc.get_gstr1_b2b(from_date, to_date)


@router.get("/gstr1-b2c")
def get_gstr1_b2c(from_date: str, to_date: str):
    svc = GSTService(get_db_manager())
    return svc.get_gstr1_b2c(from_date, to_date)


@router.get("/hsn-summary")
def get_hsn_summary(from_date: str, to_date: str):
    svc = GSTService(get_db_manager())
    return svc.get_hsn_summary(from_date, to_date)


@router.get("/rate-summary")
def get_rate_summary(from_date: str, to_date: str):
    svc = GSTService(get_db_manager())
    return svc.get_gst_rate_wise_summary(from_date, to_date)
