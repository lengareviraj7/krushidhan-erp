"""
API Route Handlers for Inward Purchases and Supplier Invoices.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from src.db.connection import get_db_manager
from src.models.purchase import Purchase
from src.repositories.purchase_repository import PurchaseRepository
from src.services.purchase_service import PurchaseService

router = APIRouter(prefix="/api/purchase", tags=["Purchase"])


@router.post("/create")
def create_purchase_invoice(purchase: Purchase):
    svc = PurchaseService(get_db_manager())
    try:
        purchase_id = svc.process_inward_purchase(purchase)
        return {"success": True, "purchase_id": purchase_id, "invoice_no": purchase.invoice_no}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
def list_purchases(from_date: Optional[str] = None, to_date: Optional[str] = None, supplier_id: Optional[int] = None):
    repo = PurchaseRepository(get_db_manager())
    return repo.get_purchases_list(from_date=from_date, to_date=to_date, supplier_id=supplier_id)


@router.get("/{purchase_id}")
def get_purchase_detail(purchase_id: int):
    repo = PurchaseRepository(get_db_manager())
    pur = repo.get_purchase_by_id(purchase_id)
    if not pur:
        raise HTTPException(status_code=404, detail="Purchase invoice not found")
    return pur
