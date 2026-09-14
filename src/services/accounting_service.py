"""
Service Layer for Accounting Operations, Vouchers, Day Book, and Financial Statements.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from src.db.connection import DatabaseManager, get_db_manager
from src.models.accounting import Expense, LedgerEntry, Voucher
from src.repositories.accounting_repository import AccountingRepository
from src.repositories.master_data_repository import MasterDataRepository


class AccountingService:
    """Business logic for financial vouchers, cash management, day book, and financial statements."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()
        self.accounting_repo = AccountingRepository(self.db)
        self.master_repo = MasterDataRepository(self.db)

    def record_customer_receipt(
        self,
        customer_id: int,
        receipt_date: str,
        amount: float,
        payment_mode: str = "CASH",
        narration: Optional[str] = None,
    ) -> int:
        """
        Record receipt from customer:
        1. Reduce customer current_balance.
        2. Post double-entry voucher (Debit Cash/Bank, Credit Accounts Receivable/Customer).
        """
        cash_ac = self.accounting_repo.get_account_by_name("Cash in Hand")
        bank_ac = self.accounting_repo.get_account_by_name("Bank Account")
        pay_ac = cash_ac if payment_mode == "CASH" else bank_ac

        with self.db.transaction() as conn:
            # Reduce customer balance
            self.master_repo.update_customer_balance(customer_id, -amount, conn=conn)

            vch_no = self.accounting_repo.generate_next_voucher_no("RECEIPT")
            entries = [
                LedgerEntry(
                    account_id=pay_ac.account_id,
                    debit_amount=amount,
                    credit_amount=0.0,
                    particulars=f"Receipt from Customer #{customer_id}",
                ),
                LedgerEntry(
                    account_id=pay_ac.account_id,  # or customer linked ledger account
                    debit_amount=0.0,
                    credit_amount=amount,
                    particulars=f"Credit to Customer #{customer_id}",
                ),
            ]
            voucher = Voucher(
                voucher_no=vch_no,
                voucher_date=receipt_date,
                voucher_type="RECEIPT",
                total_amount=amount,
                narration=narration or f"Payment received from customer #{customer_id}",
                reference_type="MANUAL",
                reference_id=customer_id,
                entries=entries,
            )
            return self.accounting_repo.create_voucher(voucher, conn=conn)

    def record_supplier_payment(
        self,
        supplier_id: int,
        payment_date: str,
        amount: float,
        payment_mode: str = "BANK_TRANSFER",
        narration: Optional[str] = None,
    ) -> int:
        """
        Record payment to supplier:
        1. Reduce supplier current_balance (payable).
        2. Post double-entry voucher (Debit Supplier/Accounts Payable, Credit Bank/Cash).
        """
        cash_ac = self.accounting_repo.get_account_by_name("Cash in Hand")
        bank_ac = self.accounting_repo.get_account_by_name("Bank Account")
        pay_ac = cash_ac if payment_mode == "CASH" else bank_ac

        with self.db.transaction() as conn:
            # Reduce supplier balance
            self.master_repo.update_supplier_balance(supplier_id, -amount, conn=conn)

            vch_no = self.accounting_repo.generate_next_voucher_no("PAYMENT")
            entries = [
                LedgerEntry(
                    account_id=pay_ac.account_id,
                    debit_amount=amount,
                    credit_amount=0.0,
                    particulars=f"Debit to Supplier #{supplier_id}",
                ),
                LedgerEntry(
                    account_id=pay_ac.account_id,
                    debit_amount=0.0,
                    credit_amount=amount,
                    particulars=f"Payment to Supplier #{supplier_id}",
                ),
            ]
            voucher = Voucher(
                voucher_no=vch_no,
                voucher_date=payment_date,
                voucher_type="PAYMENT",
                total_amount=amount,
                narration=narration or f"Payment to supplier #{supplier_id}",
                reference_type="MANUAL",
                reference_id=supplier_id,
                entries=entries,
            )
            return self.accounting_repo.create_voucher(voucher, conn=conn)

    def record_shop_expense(self, expense: Expense) -> int:
        """Record operational expense and update cash/bank ledger."""
        cash_ac = self.accounting_repo.get_account_by_name("Cash in Hand")
        pay_ac_id = expense.payment_account_id or (cash_ac.account_id if cash_ac else 1)
        expense.payment_account_id = pay_ac_id

        with self.db.transaction() as conn:
            expense_id = self.accounting_repo.create_expense(expense)

            # Post double-entry voucher for expense
            vch_no = self.accounting_repo.generate_next_voucher_no("PAYMENT")
            entries = [
                LedgerEntry(
                    account_id=pay_ac_id,
                    debit_amount=expense.amount,
                    credit_amount=0.0,
                    particulars=f"Expense: {expense.remarks or 'Shop operational expense'}",
                ),
                LedgerEntry(
                    account_id=pay_ac_id,
                    debit_amount=0.0,
                    credit_amount=expense.amount,
                    particulars="Cash/Bank paid for expense",
                ),
            ]
            vch = Voucher(
                voucher_no=vch_no,
                voucher_date=expense.expense_date,
                voucher_type="PAYMENT",
                total_amount=expense.amount,
                narration=expense.remarks,
                reference_type="EXPENSE",
                reference_id=expense_id,
                entries=entries,
            )
            self.accounting_repo.create_voucher(vch, conn=conn)
            return expense_id

    def get_day_book(self, date_str: str) -> Dict[str, Any]:
        """Fetch complete Day Book of cash, bank, sales, purchases, and expenses for a given day."""
        sales = self.db.fetch_all("SELECT * FROM sales WHERE sale_date = ?;", (date_str,))
        purchases = self.db.fetch_all("SELECT * FROM purchases WHERE purchase_date = ?;", (date_str,))
        expenses = self.db.fetch_all("SELECT * FROM expenses WHERE expense_date = ?;", (date_str,))
        vouchers = self.db.fetch_all("SELECT * FROM vouchers WHERE voucher_date = ?;", (date_str,))

        total_sales = sum(s["net_amount"] for s in sales)
        total_purchases = sum(p["net_amount"] for p in purchases)
        total_expenses = sum(e["amount"] for e in expenses)

        return {
            "date": date_str,
            "sales_count": len(sales),
            "total_sales": total_sales,
            "purchases_count": len(purchases),
            "total_purchases": total_purchases,
            "expenses_count": len(expenses),
            "total_expenses": total_expenses,
            "vouchers": [dict(v) for v in vouchers],
        }

    def get_profit_and_loss(self, from_date: str, to_date: str) -> Dict[str, Any]:
        """
        Calculate Comprehensive Profit & Loss statement based on true batch-level COGS,
        category margin analysis, and operating expense itemization.
        """
        # 1. Total Sales Revenue (Taxable Turnover and Gross Sales)
        sql_sales = """
            SELECT 
                COALESCE(SUM(total_taxable), 0) as total_taxable,
                COALESCE(SUM(net_amount), 0) as gross_sales,
                COALESCE(SUM(total_discount), 0) as total_discount,
                COUNT(sale_id) as total_invoices
            FROM sales 
            WHERE sale_date BETWEEN ? AND ?;
        """
        sales_row = self.db.fetch_one(sql_sales, (from_date, to_date))
        sales_rev = float(sales_row["total_taxable"]) if sales_row else 0.0
        gross_sales = float(sales_row["gross_sales"]) if sales_row else 0.0
        total_discount = float(sales_row["total_discount"]) if sales_row else 0.0
        total_invoices = int(sales_row["total_invoices"]) if sales_row else 0

        # 2. True Cost of Goods Sold (COGS) based on batch purchase rates of items sold
        sql_cogs = """
            SELECT 
                COALESCE(SUM(si.qty * COALESCE(sb.purchase_rate, p.default_purchase_rate)), 0) as cogs
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN stock_batches sb ON si.batch_id = sb.batch_id
            WHERE s.sale_date BETWEEN ? AND ?;
        """
        cogs_row = self.db.fetch_one(sql_cogs, (from_date, to_date))
        cogs = float(cogs_row["cogs"]) if cogs_row else 0.0

        # 3. Direct / Operating Expenses
        sql_expenses = """
            SELECT 
                COALESCE(ec.category_name, 'General Expenses') as category_name,
                COALESCE(SUM(e.amount), 0) as total_amount
            FROM expenses e
            LEFT JOIN expense_categories ec ON e.category_id = ec.category_id
            WHERE e.expense_date BETWEEN ? AND ?
            GROUP BY ec.category_name
            ORDER BY total_amount DESC;
        """
        expense_rows = self.db.fetch_all(sql_expenses, (from_date, to_date))
        expenses_breakdown = [dict(r) for r in expense_rows]
        total_expenses = sum(r["total_amount"] for r in expenses_breakdown)

        # 4. Gross Profit & Net Profit
        gross_profit = round(sales_rev - cogs, 2)
        gross_margin_pct = round((gross_profit / sales_rev * 100), 2) if sales_rev > 0 else 0.0
        net_profit = round(gross_profit - total_expenses, 2)
        net_margin_pct = round((net_profit / sales_rev * 100), 2) if sales_rev > 0 else 0.0

        # 5. Category-wise Breakdown
        sql_cat = """
            SELECT 
                COALESCE(c.category_name, 'General') as category_name,
                COALESCE(SUM(si.taxable_amount), 0) as sales_revenue,
                COALESCE(SUM(si.qty * COALESCE(sb.purchase_rate, p.default_purchase_rate)), 0) as cogs,
                COALESCE(SUM(si.taxable_amount) - SUM(si.qty * COALESCE(sb.purchase_rate, p.default_purchase_rate)), 0) as gross_profit
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN stock_batches sb ON si.batch_id = sb.batch_id
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY c.category_name
            ORDER BY gross_profit DESC;
        """
        cat_rows = self.db.fetch_all(sql_cat, (from_date, to_date))
        category_breakdown = []
        for r in cat_rows:
            cat_rev = float(r["sales_revenue"])
            cat_gp = float(r["gross_profit"])
            cat_margin = round((cat_gp / cat_rev * 100), 1) if cat_rev > 0 else 0.0
            category_breakdown.append({
                "category_name": r["category_name"],
                "sales_revenue": cat_rev,
                "cogs": float(r["cogs"]),
                "gross_profit": cat_gp,
                "margin_pct": cat_margin
            })

        # 6. Current Inventory Valuation (Closing Stock Value)
        sql_inv_val = """
            SELECT 
                COALESCE(SUM(current_qty * purchase_rate), 0) as total_valuation,
                COALESCE(SUM(current_qty), 0) as total_units
            FROM stock_batches
            WHERE current_qty > 0;
        """
        inv_val_row = self.db.fetch_one(sql_inv_val)
        closing_stock_value = float(inv_val_row["total_valuation"]) if inv_val_row else 0.0

        return {
            "from_date": from_date,
            "to_date": to_date,
            "sales_revenue": sales_rev,
            "gross_sales": gross_sales,
            "total_discount": total_discount,
            "total_invoices": total_invoices,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_margin_pct": gross_margin_pct,
            "total_expenses": total_expenses,
            "expenses_breakdown": expenses_breakdown,
            "net_profit": net_profit,
            "net_margin_pct": net_margin_pct,
            "category_breakdown": category_breakdown,
            "closing_stock_value": closing_stock_value,
        }

    def get_product_profitability(self, from_date: str, to_date: str, query: str = "") -> List[Dict[str, Any]]:
        """Fetch product-by-product sales volume, cost, profit, and margin percentage."""
        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                COALESCE(c.category_name, 'General') as category_name,
                COALESCE(m.manufacturer_name, '-') as manufacturer_name,
                COALESCE(SUM(si.qty), 0) as qty_sold,
                u.symbol as unit_symbol,
                COALESCE(SUM(si.taxable_amount), 0) as sales_revenue,
                COALESCE(SUM(si.qty * COALESCE(sb.purchase_rate, p.default_purchase_rate)), 0) as cogs,
                COALESCE(SUM(si.taxable_amount) - SUM(si.qty * COALESCE(sb.purchase_rate, p.default_purchase_rate)), 0) as gross_profit
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN units u ON p.unit_id = u.unit_id
            LEFT JOIN stock_batches sb ON si.batch_id = sb.batch_id
            WHERE s.sale_date BETWEEN ? AND ?
              AND (p.product_name LIKE ? OR c.category_name LIKE ? OR m.manufacturer_name LIKE ?)
            GROUP BY p.product_id
            ORDER BY gross_profit DESC;
        """
        pattern = f"%{query}%"
        rows = self.db.fetch_all(sql, (from_date, to_date, pattern, pattern, pattern))
        results = []
        for r in rows:
            rev = float(r["sales_revenue"])
            gp = float(r["gross_profit"])
            margin = round((gp / rev * 100), 1) if rev > 0 else 0.0
            results.append({
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "category_name": r["category_name"],
                "manufacturer_name": r["manufacturer_name"],
                "qty_sold": float(r["qty_sold"]),
                "unit_symbol": r["unit_symbol"] or "Nos",
                "sales_revenue": rev,
                "cogs": float(r["cogs"]),
                "gross_profit": gp,
                "margin_pct": margin
            })
        return results

    # ==================== SUPPLIER & DISTRIBUTOR KHATA ====================
    def get_suppliers_with_balances(self) -> List[Dict[str, Any]]:
        """Fetch all distributors/suppliers with total purchases, paid amounts, and outstanding payable balances."""
        sql = """
            SELECT 
                s.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.mobile,
                s.city,
                s.gstin,
                s.current_balance as outstanding_payable,
                COALESCE(SUM(p.net_amount), 0) as total_purchases,
                COUNT(p.purchase_id) as bills_count
            FROM suppliers s
            LEFT JOIN purchases p ON s.supplier_id = p.supplier_id
            GROUP BY s.supplier_id
            ORDER BY s.current_balance DESC, s.supplier_name ASC;
        """
        rows = self.db.fetch_all(sql)
        return [dict(r) for r in rows]

    def get_supplier_statement(self, supplier_id: int) -> Dict[str, Any]:
        """Fetch supplier profile, list of purchase bills, and payment records."""
        supplier = self.db.fetch_one("SELECT * FROM suppliers WHERE supplier_id = ?;", (supplier_id,))
        if not supplier:
            raise ValueError(f"Supplier ID {supplier_id} not found.")

        # Inward Purchase Invoices
        purchases = self.db.fetch_all(
            "SELECT purchase_id, invoice_no, purchase_date, net_amount, paid_amount, due_amount, payment_type as payment_mode FROM purchases WHERE supplier_id = ? ORDER BY purchase_date DESC;",
            (supplier_id,),
        )

        # Payment Vouchers
        vouchers = self.db.fetch_all(
            """
            SELECT DISTINCT v.voucher_id, v.voucher_no, v.voucher_date, v.total_amount, v.narration, v.reference_type, v.reference_id
            FROM vouchers v
            JOIN ledger_entries le ON v.voucher_id = le.voucher_id
            WHERE v.voucher_type = 'PAYMENT' AND le.particulars LIKE ?
            ORDER BY v.voucher_date DESC;
            """,
            (f"%Supplier #{supplier_id}%",),
        )

        p_list = [dict(p) for p in purchases]
        v_list = [dict(v) for v in vouchers]
        ledger = []
        for p in p_list:
            ledger.append({
                "type": "PURCHASE",
                "date": p["purchase_date"],
                "ref_no": p["invoice_no"],
                "debit": 0.0,
                "credit": p["net_amount"],
                "paid": p["paid_amount"],
                "due": p["due_amount"],
            })
        for v in v_list:
            ledger.append({
                "type": "PAYMENT",
                "date": v["voucher_date"],
                "ref_no": v["voucher_no"],
                "debit": v["total_amount"],
                "credit": 0.0,
                "narration": v["narration"],
            })
        ledger.sort(key=lambda x: x["date"], reverse=True)

        return {
            "supplier": dict(supplier),
            "purchases": p_list,
            "payments": v_list,
            "ledger": ledger,
        }

    def record_supplier_payment(
        self,
        supplier_id: int,
        amount: float,
        payment_mode: str = "BANK_TRANSFER",
        payment_date: Optional[str] = None,
        reference_no: Optional[str] = None,
        narration: Optional[str] = None,
    ) -> int:
        """
        Record payment made to a supplier/distributor:
        1. Reduce supplier current_balance (payable).
        2. Post double-entry Payment voucher (Debit Accounts Payable, Credit Bank/Cash).
        """
        if amount <= 0:
            raise ValueError("Payment amount must be greater than 0.")

        supplier = self.db.fetch_one("SELECT * FROM suppliers WHERE supplier_id = ?;", (supplier_id,))
        if not supplier:
            raise ValueError(f"Supplier ID {supplier_id} not found.")

        today = payment_date or datetime.now().strftime("%Y-%m-%d")
        cash_ac = self.accounting_repo.get_account_by_name("Cash in Hand")
        bank_ac = self.accounting_repo.get_account_by_name("Bank Account")
        pay_ac = cash_ac if payment_mode.upper() == "CASH" else bank_ac

        with self.db.transaction() as conn:
            # Reduce supplier payable balance
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE suppliers SET current_balance = current_balance - ? WHERE supplier_id = ?;",
                (amount, supplier_id),
            )

            # Generate voucher
            vch_no = self.accounting_repo.generate_next_voucher_no("PAYMENT")
            entries = [
                LedgerEntry(
                    account_id=pay_ac.account_id,
                    debit_amount=amount,
                    credit_amount=0.0,
                    particulars=f"Payment to Supplier #{supplier_id} ({supplier['supplier_name']})",
                ),
                LedgerEntry(
                    account_id=pay_ac.account_id,
                    debit_amount=0.0,
                    credit_amount=amount,
                    particulars=f"Paid via {payment_mode} ref: {reference_no or 'Direct'}",
                ),
            ]
            voucher = Voucher(
                voucher_no=vch_no,
                voucher_date=today,
                voucher_type="PAYMENT",
                total_amount=amount,
                narration=narration or f"Payment to {supplier['supplier_name']} - Mode: {payment_mode}",
                reference_type="PURCHASE",
                reference_id=supplier_id,
                entries=entries,
            )
            vch_id = self.accounting_repo.create_voucher(voucher, conn=conn)
            return vch_id

    # ==================== DAILY EXPENSES & CASH CLOSING ====================
    def record_daily_expense(
        self,
        category_id: int,
        amount: float,
        expense_date: Optional[str] = None,
        payment_mode: str = "CASH",
        reference_no: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> int:
        """Record an operational shop expense (Shop Rent, Labor/हमाली, Tea, Electricity, Freight)."""
        if amount <= 0:
            raise ValueError("Expense amount must be greater than 0.")

        date_str = expense_date or datetime.now().strftime("%Y-%m-%d")
        cash_ac = self.accounting_repo.get_account_by_name("Cash in Hand")
        bank_ac = self.accounting_repo.get_account_by_name("Bank Account")
        pay_ac_id = cash_ac.account_id if payment_mode.upper() == "CASH" else bank_ac.account_id

        expense = Expense(
            category_id=category_id,
            expense_date=date_str,
            amount=amount,
            payment_account_id=pay_ac_id,
            reference_no=reference_no,
            remarks=remarks,
        )
        return self.accounting_repo.create_expense(expense)

    def get_expense_categories(self) -> List[Dict[str, Any]]:
        """Fetch all operational expense categories."""
        rows = self.db.fetch_all("SELECT * FROM expense_categories ORDER BY category_id ASC;")
        return [dict(r) for r in rows]

    def get_cash_drawer_reconciliation(self, date_str: str) -> Dict[str, Any]:
        """
        Calculates daily cash drawer breakdown:
        Opening Cash + Cash Sales + Farmer Cash Receipts - Cash Expenses - Cash Supplier Payments = Expected Drawer Cash.
        """
        # 1. Cash Sales on date
        cash_sales_row = self.db.fetch_one(
            "SELECT COALESCE(SUM(paid_amount), 0) as total FROM sales WHERE sale_date = ? AND payment_mode IN ('CASH', 'SPLIT');",
            (date_str,),
        )
        cash_sales = float(cash_sales_row["total"]) if cash_sales_row else 0.0

        # 2. Farmer Receipts in Cash (Debit Cash in Hand Account 1)
        farmer_receipts_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(DISTINCT v.total_amount), 0) as total 
            FROM vouchers v 
            JOIN ledger_entries le ON v.voucher_id = le.voucher_id
            WHERE v.voucher_date = ? AND v.voucher_type = 'RECEIPT' AND le.account_id = 1 AND le.debit_amount > 0;
            """,
            (date_str,),
        )
        farmer_receipts = float(farmer_receipts_row["total"]) if farmer_receipts_row else 0.0

        # 3. Cash Expenses
        cash_exp_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) as total 
            FROM expenses 
            WHERE expense_date = ? AND payment_account_id = 1;
            """,
            (date_str,),
        )
        cash_expenses = float(cash_exp_row["total"]) if cash_exp_row else 0.0

        # 4. Cash Supplier Payments (Credit Cash in Hand Account 1)
        cash_supp_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(DISTINCT v.total_amount), 0) as total 
            FROM vouchers v 
            JOIN ledger_entries le ON v.voucher_id = le.voucher_id
            WHERE v.voucher_date = ? AND v.voucher_type = 'PAYMENT' AND le.account_id = 1 AND le.credit_amount > 0;
            """,
            (date_str,),
        )
        cash_supp_payments = float(cash_supp_row["total"]) if cash_supp_row else 0.0

        # Opening balance constant or estimate
        opening_cash = 5000.0  # standard base float
        net_inflow = (cash_sales + farmer_receipts) - (cash_expenses + cash_supp_payments)
        expected_cash = opening_cash + net_inflow

        return {
            "date": date_str,
            "opening_cash": opening_cash,
            "cash_sales": cash_sales,
            "farmer_cash_receipts": farmer_receipts,
            "total_cash_inflow": cash_sales + farmer_receipts,
            "cash_expenses": cash_expenses,
            "cash_supplier_payments": cash_supp_payments,
            "total_cash_outflow": cash_expenses + cash_supp_payments,
            "net_cash_flow": net_inflow,
            "expected_drawer_cash": max(0.0, expected_cash),
            "expected_cash_in_hand": max(0.0, expected_cash),
        }

