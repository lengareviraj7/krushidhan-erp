"""
Domain Data Models for System Users, Company Profile, and Audit Logs.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    user_id: Optional[int] = None
    username: str
    password_hash: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "OPERATOR"  # 'ADMIN', 'MANAGER', 'OPERATOR'
    is_active: int = 1
    created_at: Optional[str] = None


class CompanySettings(BaseModel):
    setting_id: Optional[int] = None
    company_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: str = "Maharashtra"
    pincode: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    dl_fertilizer: Optional[str] = None
    dl_pesticide: Optional[str] = None
    dl_seed: Optional[str] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    ifsc_code: Optional[str] = None
    invoice_terms: Optional[str] = None
    is_thermal_print: int = 0
    default_invoice_size: str = "A4"  # 'A4', 'A5', '3INCH_THERMAL'
    updated_at: Optional[str] = None


class AuditLogEntry(BaseModel):
    log_id: Optional[int] = None
    user_id: Optional[int] = None
    action_type: str  # 'INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'BACKUP'
    table_name: Optional[str] = None
    record_id: Optional[int] = None
    details: Optional[str] = None
    created_at: Optional[str] = None


class BackupLogEntry(BaseModel):
    backup_id: Optional[int] = None
    file_path: str
    backup_type: str  # 'MANUAL', 'SCHEDULED', 'BEFORE_UPGRADE'
    backup_size_bytes: Optional[int] = None
    status: str = "SUCCESS"
    created_at: Optional[str] = None
