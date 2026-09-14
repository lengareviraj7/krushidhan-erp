"""
Domain Data Models for Batch-Wise Inventory and Stock Ledger.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class StockBatch(BaseModel):
    batch_id: Optional[int] = None
    product_id: int
    batch_no: str
    mfg_date: Optional[str] = None
    exp_date: Optional[str] = None
    purchase_rate: float = 0.0
    sale_rate: float = 0.0
    mrp: float = 0.0
    opening_qty: float = 0.0
    current_qty: float = 0.0
    barcode: Optional[str] = None
    created_at: Optional[str] = None


class StockLedgerEntry(BaseModel):
    ledger_id: Optional[int] = None
    product_id: int
    batch_id: Optional[int] = None
    transaction_type: str  # 'PURCHASE', 'PURCHASE_RETURN', 'SALE', 'SALE_RETURN', 'ADJUSTMENT'
    reference_type: str    # 'INVOICE', 'CHALLAN', 'MANUAL_ADJUSTMENT'
    reference_id: int
    movement_date: Optional[str] = None
    qty_in: float = 0.0
    qty_out: float = 0.0
    balance_qty: float = 0.0
    rate: Optional[float] = None
    remarks: Optional[str] = None
    created_at: Optional[str] = None
