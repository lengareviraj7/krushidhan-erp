"""
Data Access Layer (Repository) for Chart of Accounts, Vouchers, and Expenses.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from src.models.accounting import Expense, ExpenseCategory, LedgerAccount, LedgerEntry, Voucher
from src.repositories.base_repository import BaseRepository


class AccountingRepository(BaseRepository):
    """Repository for double-entry financial accounts, vouchers, and expenses."""

    # ---------------- Chart of Accounts ----------------
    def create_account(self, account: LedgerAccount) -> int:
        sql = "INSERT INTO ledger_accounts (account_name, account_group, opening_balance, current_balance, is_system) VALUES (?, ?, ?, ?, ?);"
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    account.account_name,
                    account.account_group,
                    account.opening_balance,
                    account.opening_balance,
                    account.is_system,
                ),
            )
            return cursor.lastrowid

    def get_all_accounts(self) -> List[LedgerAccount]:
        rows = self.db.fetch_all("SELECT * FROM ledger_accounts ORDER BY account_name ASC;")
        return [LedgerAccount(**dict(r)) for r in rows]

    def get_account_by_name(self, name: str) -> Optional[LedgerAccount]:
        row = self.db.fetch_one("SELECT * FROM ledger_accounts WHERE account_name = ?;", (name,))
        return LedgerAccount(**dict(row)) if row else None

    def get_account_by_id(self, account_id: int) -> Optional[LedgerAccount]:
        row = self.db.fetch_one("SELECT * FROM ledger_accounts WHERE account_id = ?;", (account_id,))
        return LedgerAccount(**dict(row)) if row else None

    def update_account_balance(
        self, account_id: int, debit: float, credit: float, conn: Optional[sqlite3.Connection] = None
    ) -> None:
        """
        Update account balance based on account normal balance rules:
        Assets / Expenses: Normal Debit (Increase with Debit, Decrease with Credit)
        Liabilities / Income / Equity: Normal Credit (Increase with Credit, Decrease with Debit)
        """
        executor = conn if conn is not None else self.db.get_connection()
        try:
            cursor = executor.cursor()
            cursor.execute("SELECT account_group FROM ledger_accounts WHERE account_id = ?;", (account_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Account ID {account_id} not found!")

            group = row["account_group"]
            if group in ("ASSETS", "EXPENSE", "BANK_ACCOUNTS", "CASH"):
                delta = debit - credit
            else:
                delta = credit - debit

            cursor.execute(
                "UPDATE ledger_accounts SET current_balance = current_balance + ? WHERE account_id = ?;",
                (delta, account_id),
            )
            if conn is None:
                executor.commit()
        finally:
            if conn is None:
                executor.close()

    # ---------------- Vouchers & Double Entry Posting ----------------
    def generate_next_voucher_no(self, voucher_type: str) -> str:
        """Generate voucher number like RCP-0001, PAY-0001, JRN-0001."""
        prefix_map = {
            "RECEIPT": "RCP-",
            "PAYMENT": "PAY-",
            "CONTRA": "CTR-",
            "JOURNAL": "JRN-",
            "DEBIT_NOTE": "DN-",
            "CREDIT_NOTE": "CN-",
        }
        prefix = prefix_map.get(voucher_type, "VCH-")
        row = self.db.fetch_one("SELECT MAX(voucher_id) as last_id FROM vouchers;")
        last_id = row["last_id"] if row and row["last_id"] else 0
        return f"{prefix}{last_id + 1:05d}"

    def create_voucher(self, voucher: Voucher, conn: Optional[sqlite3.Connection] = None) -> int:
        """Persist an accounting voucher and post all balanced ledger debit/credit entries."""
        # Validate that total debits == total credits
        total_debit = sum(e.debit_amount for e in voucher.entries)
        total_credit = sum(e.credit_amount for e in voucher.entries)
        if round(total_debit, 2) != round(total_credit, 2):
            raise ValueError(
                f"Unbalanced voucher entries: Total Debit ({total_debit}) != Total Credit ({total_credit})"
            )

        sql_vch = """
            INSERT INTO vouchers (
                voucher_no, voucher_date, voucher_type, total_amount, narration, reference_type, reference_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        sql_entry = """
            INSERT INTO ledger_entries (
                voucher_id, account_id, debit_amount, credit_amount, particulars
            ) VALUES (?, ?, ?, ?, ?);
        """

        executor = conn if conn is not None else self.db.get_connection()
        try:
            cursor = executor.cursor()
            cursor.execute(
                sql_vch,
                (
                    voucher.voucher_no,
                    voucher.voucher_date,
                    voucher.voucher_type,
                    voucher.total_amount,
                    voucher.narration,
                    voucher.reference_type,
                    voucher.reference_id,
                ),
            )
            voucher_id = cursor.lastrowid

            for entry in voucher.entries:
                cursor.execute(
                    sql_entry,
                    (
                        voucher_id,
                        entry.account_id,
                        entry.debit_amount,
                        entry.credit_amount,
                        entry.particulars,
                    ),
                )
                # Update ledger account current balance
                self.update_account_balance(
                    account_id=entry.account_id,
                    debit=entry.debit_amount,
                    credit=entry.credit_amount,
                    conn=executor,
                )

            if conn is None:
                executor.commit()
            return voucher_id
        finally:
            if conn is None:
                executor.close()

    def get_account_ledger_statement(
        self, account_id: int, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch chronological ledger entries for a specific account."""
        sql = """
            SELECT 
                le.entry_id,
                v.voucher_no,
                v.voucher_date,
                v.voucher_type,
                le.particulars,
                le.debit_amount,
                le.credit_amount
            FROM ledger_entries le
            JOIN vouchers v ON le.voucher_id = v.voucher_id
            WHERE le.account_id = ?
              AND (? IS NULL OR v.voucher_date >= ?)
              AND (? IS NULL OR v.voucher_date <= ?)
            ORDER BY v.voucher_date ASC, v.voucher_id ASC;
        """
        rows = self.db.fetch_all(sql, (account_id, from_date, from_date, to_date, to_date))
        return [dict(r) for r in rows]

    # ---------------- Expenses ----------------
    def create_expense(self, expense: Expense) -> int:
        sql = """
            INSERT INTO expenses (
                category_id, expense_date, amount, payment_account_id, reference_no, remarks
            ) VALUES (?, ?, ?, ?, ?, ?);
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    expense.category_id,
                    expense.expense_date,
                    expense.amount,
                    expense.payment_account_id,
                    expense.reference_no,
                    expense.remarks,
                ),
            )
            return cursor.lastrowid

    def get_expenses_list(
        self, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT 
                e.*,
                ec.category_name,
                la.account_name as payment_account_name
            FROM expenses e
            JOIN expense_categories ec ON e.category_id = ec.category_id
            LEFT JOIN ledger_accounts la ON e.payment_account_id = la.account_id
            WHERE (? IS NULL OR e.expense_date >= ?)
              AND (? IS NULL OR e.expense_date <= ?)
            ORDER BY e.expense_date DESC, e.expense_id DESC;
        """
        rows = self.db.fetch_all(sql, (from_date, from_date, to_date, to_date))
        return [dict(r) for r in rows]
