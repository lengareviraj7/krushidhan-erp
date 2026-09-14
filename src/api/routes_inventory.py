"""
API Route Handlers for Inventory, Stock Batches, and Expiry Tracking.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from src.db.connection import get_db_manager
from src.repositories.inventory_repository import InventoryRepository
from src.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


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
