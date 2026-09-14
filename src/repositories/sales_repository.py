"""
Data Access Layer (Repository) for Sales Invoices and Sales Returns.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from src.models.sales import Sale, SaleItem, SalesReturn, SalesReturnItem
from src.repositories.base_repository import BaseRepository


class SalesRepository(BaseRepository):
    """Repository for managing sales billing, tax invoices, and sales returns."""

    def generate_next_invoice_no(self, prefix: str = "INV-") -> str:
        """Generate sequential invoice number (e.g., INV-00001, INV-00002)."""
        row = self.db.fetch_one("SELECT MAX(sale_id) as last_id FROM sales;")
        last_id = row["last_id"] if row and row["last_id"] else 0
        next_id = last_id + 1
        return f"{prefix}{next_id:05d}"

    def generate_next_return_no(self, prefix: str = "RET-") -> str:
        """Generate sequential sales return number."""
        row = self.db.fetch_one("SELECT MAX(return_id) as last_id FROM sales_returns;")
        last_id = row["last_id"] if row and row["last_id"] else 0
        next_id = last_id + 1
        return f"{prefix}{next_id:05d}"

    def create_sale(self, sale: Sale, conn: Optional[sqlite3.Connection] = None) -> int:
        """Persist sales invoice header and line items."""
        sql_head = """
            INSERT INTO sales (
                invoice_no, sale_date, customer_id, doctor_or_officer, payment_mode,
                total_taxable, total_cgst, total_sgst, total_igst, total_discount,
                extra_charges, round_off, net_amount, paid_amount, due_amount,
                print_count, remarks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        sql_item = """
            INSERT INTO sale_items (
                sale_id, product_id, batch_id, qty, unit_id,
                sale_rate, mrp, discount_percent, discount_amount, taxable_amount,
                cgst_rate, cgst_amount, sgst_rate, sgst_amount, igst_rate, igst_amount,
                total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        executor = conn if conn is not None else self.db.get_connection()
        try:
            cursor = executor.cursor()
            cursor.execute(
                sql_head,
                (
                    sale.invoice_no,
                    sale.sale_date,
                    sale.customer_id,
                    sale.doctor_or_officer,
                    sale.payment_mode,
                    sale.total_taxable,
                    sale.total_cgst,
                    sale.total_sgst,
                    sale.total_igst,
                    sale.total_discount,
                    sale.extra_charges,
                    sale.round_off,
                    sale.net_amount,
                    sale.paid_amount,
                    sale.due_amount,
                    sale.print_count,
                    sale.remarks,
                ),
            )
            sale_id = cursor.lastrowid

            for item in sale.items:
                cursor.execute(
                    sql_item,
                    (
                        sale_id,
                        item.product_id,
                        item.batch_id,
                        item.qty,
                        item.unit_id,
                        item.sale_rate,
                        item.mrp,
                        item.discount_percent,
                        item.discount_amount,
                        item.taxable_amount,
                        item.cgst_rate,
                        item.cgst_amount,
                        item.sgst_rate,
                        item.sgst_amount,
                        item.igst_rate,
                        item.igst_amount,
                        item.total_amount,
                    ),
                )

            if conn is None:
                executor.commit()
            return sale_id
        finally:
            if conn is None:
                executor.close()

    def get_sale_by_id(self, sale_id: int) -> Optional[Sale]:
        """Fetch complete sale invoice with customer details and line items."""
        sql_sale = """
            SELECT 
                s.*,
                c.customer_name,
                c.mobile as customer_mobile,
                c.village as customer_village,
                c.gstin as customer_gstin
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.sale_id = ?;
        """
        row = self.db.fetch_one(sql_sale, (sale_id,))
        if not row:
            return None

        sale_dict = dict(row)
        sql_items = """
            SELECT 
                si.*,
                p.product_name,
                p.hsn_code,
                sb.batch_no,
                sb.exp_date,
                u.symbol as unit_name
            FROM sale_items si
            JOIN products p ON si.product_id = p.product_id
            JOIN stock_batches sb ON si.batch_id = sb.batch_id
            LEFT JOIN units u ON si.unit_id = u.unit_id
            WHERE si.sale_id = ?
            ORDER BY si.sale_item_id ASC;
        """
        item_rows = self.db.fetch_all(sql_items, (sale_id,))
        sale_dict["items"] = [SaleItem(**dict(ir)) for ir in item_rows]
        return Sale(**sale_dict)

    def get_sales_list(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        customer_id: Optional[int] = None,
        payment_mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of sales invoices with customer summary."""
        sql = """
            SELECT 
                s.*,
                c.customer_name,
                c.village,
                c.mobile
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE (? IS NULL OR s.sale_date >= ?)
              AND (? IS NULL OR s.sale_date <= ?)
              AND (? IS NULL OR s.customer_id = ?)
              AND (? IS NULL OR s.payment_mode = ?)
            ORDER BY s.sale_date DESC, s.sale_id DESC;
        """
        rows = self.db.fetch_all(
            sql,
            (from_date, from_date, to_date, to_date, customer_id, customer_id, payment_mode, payment_mode),
        )
        return [dict(r) for r in rows]

    def increment_print_count(self, sale_id: int) -> None:
        """Increment reprint count."""
        with self.db.transaction() as conn:
            conn.execute("UPDATE sales SET print_count = print_count + 1 WHERE sale_id = ?;", (sale_id,))
