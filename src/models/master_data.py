"""
Domain Data Models for Master Data Entities.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class Category(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    short_name: Optional[str] = None
    is_hardware_category: int = 0
    created_at: Optional[str] = None


class Manufacturer(BaseModel):
    manufacturer_id: Optional[int] = None
    manufacturer_name: str
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[str] = None


class Unit(BaseModel):
    unit_id: Optional[int] = None
    unit_name: str
    symbol: Optional[str] = None
    created_at: Optional[str] = None


class UnitConversion(BaseModel):
    conversion_id: Optional[int] = None
    from_unit_id: int
    to_unit_id: int
    conversion_factor: float
    created_at: Optional[str] = None


class TaxGroup(BaseModel):
    tax_group_id: Optional[int] = None
    tax_group_name: str
    cgst_rate: float = 0.0
    sgst_rate: float = 0.0
    igst_rate: float = 0.0
    is_active: int = 1
    created_at: Optional[str] = None

    @property
    def total_tax_rate(self) -> float:
        return self.cgst_rate + self.sgst_rate or self.igst_rate


class Crop(BaseModel):
    crop_id: Optional[int] = None
    crop_name: str
    description: Optional[str] = None
    created_at: Optional[str] = None


class Product(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    category_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    hsn_code: Optional[str] = None
    unit_id: Optional[int] = None
    tax_group_id: Optional[int] = None
    default_purchase_rate: float = 0.0
    default_sale_rate: float = 0.0
    default_mrp: float = 0.0
    min_stock_alert: float = 0.0
    crop_id: Optional[int] = None
    is_active: int = 1
    created_at: Optional[str] = None


class CustomerGroup(BaseModel):
    group_id: Optional[int] = None
    group_name: str
    discount_percent: float = 0.0
    created_at: Optional[str] = None


class Customer(BaseModel):
    customer_id: Optional[int] = None
    customer_name: str
    mobile: Optional[str] = None
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    state: str = "Maharashtra"
    aadhar_no: Optional[str] = None
    gstin: Optional[str] = None
    group_id: Optional[int] = None
    opening_balance: float = 0.0
    current_balance: float = 0.0
    credit_limit: float = 0.0
    is_active: int = 1
    created_at: Optional[str] = None


class Supplier(BaseModel):
    supplier_id: Optional[int] = None
    supplier_name: str
    contact_person: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: str = "Maharashtra"
    gstin: Optional[str] = None
    pan: Optional[str] = None
    dl_number: Optional[str] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    ifsc_code: Optional[str] = None
    opening_balance: float = 0.0
    current_balance: float = 0.0
    is_active: int = 1
    created_at: Optional[str] = None


class ExtraCharge(BaseModel):
    charge_id: Optional[int] = None
    charge_name: str
    tax_group_id: Optional[int] = None
    default_amount: float = 0.0
    is_active: int = 1
    created_at: Optional[str] = None
