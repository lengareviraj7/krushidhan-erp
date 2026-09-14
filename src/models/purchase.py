"""
Domain Data Models for Inward Purchases and Purchase Returns.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class PurchaseItem(BaseModel):
    item_id: Optional[int] = None
    purchase_id: Optional[int] = None
    product_id: int
    batch_no: str
    mfg_date: Optional[str] = None
    exp_date: Optional[str] = None
    qty: float
    free_qty: float = 0.0
    unit_id: Optional[int] = None
    purchase_rate: float
    sale_rate: float
    mrp: float
    discount_percent: float = 0.0
    discount_amount: float = 0.0
    taxable_amount: float
    cgst_rate: float = 0.0
    cgst_amount: float = 0.0
    sgst_rate: float = 0.0
    sgst_amount: float = 0.0
    igst_rate: float = 0.0
    igst_amount: float = 0.0
    total_amount: float
    created_at: Optional[str] = None


class Purchase(BaseModel):
    purchase_id: Optional[int] = None
    invoice_no: str
    purchase_date: str
    supplier_id: int
    challan_no: Optional[str] = None
    payment_type: str = "CREDIT"  # 'CASH', 'CREDIT', 'BANK_TRANSFER'
    total_taxable: float = 0.0
    total_cgst: float = 0.0
    total_sgst: float = 0.0
    total_igst: float = 0.0
    extra_charges: float = 0.0
    round_off: float = 0.0
    net_amount: float
    paid_amount: float = 0.0
    due_amount: float = 0.0
    remarks: Optional[str] = None
    items: List[PurchaseItem] = Field(default_factory=list)
    created_at: Optional[str] = None


class PurchaseReturnItem(BaseModel):
    return_item_id: Optional[int] = None
    return_id: Optional[int] = None
    product_id: int
    batch_id: Optional[int] = None
    qty: float
    purchase_rate: float
    taxable_amount: float
    tax_amount: float = 0.0
    total_amount: float
    reason: Optional[str] = None


class PurchaseReturn(BaseModel):
    return_id: Optional[int] = None
    return_no: str
    return_date: str
    purchase_id: Optional[int] = None
    supplier_id: int
    total_taxable: float = 0.0
    total_tax: float = 0.0
    round_off: float = 0.0
    net_amount: float
    remarks: Optional[str] = None
    items: List[PurchaseReturnItem] = Field(default_factory=list)
    created_at: Optional[str] = None
