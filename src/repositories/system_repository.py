"""
Data Access Layer (Repository) for System Users, Company Profile, and Audit Trails.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from src.models.system import AuditLogEntry, BackupLogEntry, CompanySettings, User
from src.repositories.base_repository import BaseRepository


class SystemRepository(BaseRepository):
    """Repository for system authentication, company profile, and audit logs."""

    # ---------------- Users & Auth ----------------
    def create_user(self, user: User) -> int:
        sql = "INSERT INTO users (username, password_hash, full_name, role, is_active) VALUES (?, ?, ?, ?, ?);"
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user.username, user.password_hash, user.full_name, user.role, user.is_active))
            return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[User]:
        row = self.db.fetch_one("SELECT * FROM users WHERE username = ?;", (username,))
        return User(**dict(row)) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        row = self.db.fetch_one("SELECT * FROM users WHERE user_id = ?;", (user_id,))
        return User(**dict(row)) if row else None

    def list_users(self) -> List[User]:
        rows = self.db.fetch_all("SELECT user_id, username, full_name, role, is_active, created_at FROM users;")
        return [User(**dict(r)) for r in rows]

    # ---------------- Company Profile ----------------
    def get_company_settings(self) -> CompanySettings:
        row = self.db.fetch_one("SELECT * FROM company_settings WHERE setting_id = 1;")
        if row:
            return CompanySettings(**dict(row))
        return CompanySettings(company_name="Krishi Agri Shop")

    def update_company_settings(self, settings: CompanySettings) -> None:
        sql = """
            INSERT INTO company_settings (
                setting_id, company_name, address, city, state, pincode, mobile, email,
                gstin, dl_fertilizer, dl_pesticide, dl_seed, bank_name, account_no, ifsc_code,
                invoice_terms, is_thermal_print, default_invoice_size, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_id) DO UPDATE SET
                company_name = excluded.company_name,
                address = excluded.address,
                city = excluded.city,
                state = excluded.state,
                pincode = excluded.pincode,
                mobile = excluded.mobile,
                email = excluded.email,
                gstin = excluded.gstin,
                dl_fertilizer = excluded.dl_fertilizer,
                dl_pesticide = excluded.dl_pesticide,
                dl_seed = excluded.dl_seed,
                bank_name = excluded.bank_name,
                account_no = excluded.account_no,
                ifsc_code = excluded.ifsc_code,
                invoice_terms = excluded.invoice_terms,
                is_thermal_print = excluded.is_thermal_print,
                default_invoice_size = excluded.default_invoice_size,
                updated_at = CURRENT_TIMESTAMP;
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    settings.company_name,
                    settings.address,
                    settings.city,
                    settings.state,
                    settings.pincode,
                    settings.mobile,
                    settings.email,
                    settings.gstin,
                    settings.dl_fertilizer,
                    settings.dl_pesticide,
                    settings.dl_seed,
                    settings.bank_name,
                    settings.account_no,
                    settings.ifsc_code,
                    settings.invoice_terms,
                    settings.is_thermal_print,
                    settings.default_invoice_size,
                ),
            )

    # ---------------- Audit Trail ----------------
    def log_action(self, entry: AuditLogEntry) -> int:
        sql = "INSERT INTO audit_log (user_id, action_type, table_name, record_id, details) VALUES (?, ?, ?, ?, ?);"
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (entry.user_id, entry.action_type, entry.table_name, entry.record_id, entry.details),
            )
            return cursor.lastrowid

    # ---------------- Backup Log ----------------
    def record_backup(self, entry: BackupLogEntry) -> int:
        sql = "INSERT INTO backup_log (file_path, backup_type, backup_size_bytes, status) VALUES (?, ?, ?, ?);"
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (entry.file_path, entry.backup_type, entry.backup_size_bytes, entry.status),
            )
            return cursor.lastrowid
