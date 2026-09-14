"""
API Route Handlers for Inventory, Stock Batches, and Expiry Tracking.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.db.connection import get_db_manager
from src.repositories.inventory_repository import InventoryRepository
from src.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


class DirectAddStockRequest(BaseModel):
    product_id: int
    qty: float
    batch_no: Optional[str] = None
    purchase_rate: Optional[float] = None
    sale_rate: Optional[float] = None
    mrp: Optional[float] = None
    mfg_date: Optional[str] = None
    exp_date: Optional[str] = None
    remarks: Optional[str] = "Manual Stock Addition"


@router.get("/stock-summary")
def get_stock_summary(category_id: Optional[int] = None):
    svc = InventoryService(get_db_manager())
    return svc.get_stock_statement(category_id)


@router.get("/batches/{product_id}")
def get_product_batches(product_id: int):
    repo = InventoryRepository(get_db_manager())
    batches = repo.get_available_batches_fefo(product_id)
    return batches


@router.get("/expiry-alerts")
def get_expiry_alerts(days: int = 90):
    svc = InventoryService(get_db_manager())
    return svc.get_expiry_reminders(days_threshold=days)


@router.get("/low-stock-alerts")
def get_low_stock_alerts():
    svc = InventoryService(get_db_manager())
    return svc.get_low_stock_alerts()


@router.post("/add-stock")
def add_direct_stock(payload: DirectAddStockRequest):
    """Directly add stock/batch to inventory from stock section."""
    svc = InventoryService(get_db_manager())
    try:
        res = svc.add_direct_stock(
            product_id=payload.product_id,
            qty=payload.qty,
            batch_no=payload.batch_no,
            purchase_rate=payload.purchase_rate,
            sale_rate=payload.sale_rate,
            mrp=payload.mrp,
            mfg_date=payload.mfg_date,
            exp_date=payload.exp_date,
            remarks=payload.remarks,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
