"""
Data Access Layer (Repository) for Inward Purchases and Purchase Returns.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from src.models.purchase import Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
from src.repositories.base_repository import BaseRepository


class PurchaseRepository(BaseRepository):
    """Repository for managing purchase transactions and purchase returns."""

    def create_purchase(self, purchase: Purchase, conn: Optional[sqlite3.Connection] = None) -> int:
        """Persist purchase invoice header and all line items."""
        sql_head = """
            INSERT INTO purchases (
                invoice_no, purchase_date, supplier_id, challan_no, payment_type,
                total_taxable, total_cgst, total_sgst, total_igst, extra_charges,
                round_off, net_amount, paid_amount, due_amount, remarks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        sql_item = """
            INSERT INTO purchase_items (
                purchase_id, product_id, batch_no, mfg_date, exp_date,
                qty, free_qty, unit_id, purchase_rate, sale_rate, mrp,
                discount_percent, discount_amount, taxable_amount,
                cgst_rate, cgst_amount, sgst_rate, sgst_amount, igst_rate, igst_amount,
                total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        executor = conn if conn is not None else self.db.get_connection()
        try:
            cursor = executor.cursor()
            cursor.execute(
                sql_head,
                (
                    purchase.invoice_no,
                    purchase.purchase_date,
                    purchase.supplier_id,
                    purchase.challan_no,
                    purchase.payment_type,
                    purchase.total_taxable,
                    purchase.total_cgst,
                    purchase.total_sgst,
                    purchase.total_igst,
                    purchase.extra_charges,
                    purchase.round_off,
                    purchase.net_amount,
                    purchase.paid_amount,
                    purchase.due_amount,
                    purchase.remarks,
                ),
            )
            purchase_id = cursor.lastrowid

            for item in purchase.items:
                cursor.execute(
                    sql_item,
                    (
                        purchase_id,
                        item.product_id,
                        item.batch_no,
                        item.mfg_date,
                        item.exp_date,
                        item.qty,
                        item.free_qty,
                        item.unit_id,
                        item.purchase_rate,
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
            return purchase_id
        finally:
            if conn is None:
                executor.close()

    def get_purchase_by_id(self, purchase_id: int) -> Optional[Purchase]:
        """Fetch a purchase invoice and all its line items."""
        row = self.db.fetch_one("SELECT * FROM purchases WHERE purchase_id = ?;", (purchase_id,))
        if not row:
            return None

        purchase_dict = dict(row)
        item_rows = self.db.fetch_all(
            "SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY item_id ASC;",
            (purchase_id,),
        )
        purchase_dict["items"] = [PurchaseItem(**dict(ir)) for ir in item_rows]
        return Purchase(**purchase_dict)

    def get_purchases_list(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        supplier_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of purchase invoices with supplier names for reporting/dashboard."""
        sql = """
            SELECT 
                p.*,
                s.supplier_name,
                s.gstin as supplier_gstin
            FROM purchases p
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            WHERE (? IS NULL OR p.purchase_date >= ?)
              AND (? IS NULL OR p.purchase_date <= ?)
              AND (? IS NULL OR p.supplier_id = ?)
            ORDER BY p.purchase_date DESC, p.purchase_id DESC;
        """
        rows = self.db.fetch_all(sql, (from_date, from_date, to_date, to_date, supplier_id, supplier_id))
        return [dict(r) for r in rows]
