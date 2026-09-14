"""
API Route Handlers for Double-Entry Accounts, Vouchers, Day Book, and P&L.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.db.connection import get_db_manager
from src.models.accounting import Expense
from src.services.accounting_service import AccountingService

router = APIRouter(prefix="/api/accounting", tags=["Accounting"])


class CustomerReceiptRequest(BaseModel):
    customer_id: int
    receipt_date: str
    amount: float
    payment_mode: str = "CASH"
    narration: Optional[str] = None


class SupplierPaymentRequest(BaseModel):
    supplier_id: int
    payment_date: str
    amount: float
    payment_mode: str = "BANK_TRANSFER"
    narration: Optional[str] = None


@router.post("/customer-receipt")
def record_receipt(req: CustomerReceiptRequest):
    svc = AccountingService(get_db_manager())
    try:
        vch_id = svc.record_customer_receipt(
            customer_id=req.customer_id,
            receipt_date=req.receipt_date,
            amount=req.amount,
            payment_mode=req.payment_mode,
            narration=req.narration,
        )
        return {"success": True, "voucher_id": vch_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/supplier-payment")
def record_payment(req: SupplierPaymentRequest):
    svc = AccountingService(get_db_manager())
    try:
        vch_id = svc.record_supplier_payment(
            supplier_id=req.supplier_id,
            payment_date=req.payment_date,
            amount=req.amount,
            payment_mode=req.payment_mode,
            narration=req.narration,
        )
        return {"success": True, "voucher_id": vch_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/expense")
def record_expense(expense: Expense):
    svc = AccountingService(get_db_manager())
    try:
        expense_id = svc.record_shop_expense(expense)
        return {"success": True, "expense_id": expense_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/day-book")
def get_day_book(date: str):
    svc = AccountingService(get_db_manager())
    return svc.get_day_book(date)


@router.get("/profit-and-loss")
def get_profit_and_loss(from_date: str, to_date: str):
    svc = AccountingService(get_db_manager())
    return svc.get_profit_and_loss(from_date, to_date)


@router.get("/profit-and-loss/products")
def get_product_profitability(from_date: str, to_date: str, query: str = ""):
    svc = AccountingService(get_db_manager())
    return svc.get_product_profitability(from_date, to_date, query=query)
