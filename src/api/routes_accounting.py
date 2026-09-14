"""
API Route Handlers for Double-Entry Accounts, Vouchers, Day Book, Supplier Khata, Expenses & Cash Drawer.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.db.connection import get_db_manager
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
    amount: float
    payment_date: Optional[str] = None
    payment_mode: str = "BANK_TRANSFER"
    reference_no: Optional[str] = None
    narration: Optional[str] = None


class RecordExpenseRequest(BaseModel):
    category_id: int
    amount: float
    expense_date: Optional[str] = None
    payment_mode: str = "CASH"
    reference_no: Optional[str] = None
    remarks: Optional[str] = None


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


@router.get("/suppliers")
def get_suppliers_balances():
    """Fetch all suppliers with outstanding payables and inward purchase totals."""
    svc = AccountingService(get_db_manager())
    return svc.get_suppliers_with_balances()


@router.get("/suppliers/{supplier_id}/statement")
def get_supplier_statement(supplier_id: int):
    """Fetch complete ledger statement for a supplier."""
    svc = AccountingService(get_db_manager())
    try:
        return svc.get_supplier_statement(supplier_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/supplier-payment")
def record_payment(req: SupplierPaymentRequest):
    """Record payment made to a supplier/distributor."""
    svc = AccountingService(get_db_manager())
    try:
        vch_id = svc.record_supplier_payment(
            supplier_id=req.supplier_id,
            amount=req.amount,
            payment_mode=req.payment_mode,
            payment_date=req.payment_date,
            reference_no=req.reference_no,
            narration=req.narration,
        )
        return {"success": True, "voucher_id": vch_id, "message": "Payment recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/expense-categories")
def get_expense_categories():
    """Fetch standard operational expense categories."""
    svc = AccountingService(get_db_manager())
    return svc.get_expense_categories()


@router.post("/expenses")
def record_expense(req: RecordExpenseRequest):
    """Record an operational shop expense (Rent, Labor/हमाली, Electricity, Freight)."""
    svc = AccountingService(get_db_manager())
    try:
        exp_id = svc.record_daily_expense(
            category_id=req.category_id,
            amount=req.amount,
            expense_date=req.expense_date,
            payment_mode=req.payment_mode,
            reference_no=req.reference_no,
            remarks=req.remarks,
        )
        return {"success": True, "expense_id": exp_id, "message": "Expense recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cash-closing-summary")
def get_cash_closing_summary(target_date: Optional[str] = None, date: Optional[str] = None):
    """Reconcile daily cash drawer: Sales + Receipts - Expenses - Payments = Expected Drawer Cash."""
    from datetime import date as dt_date
    actual_date = target_date or date or dt_date.today().isoformat()
    svc = AccountingService(get_db_manager())
    return svc.get_cash_drawer_reconciliation(actual_date)


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
