"""
Service Layer for Statutory GST Reports (GSTR-1, HSN Summary, Slab Summary).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from src.db.connection import DatabaseManager, get_db_manager


class GSTService:
    """Business logic for Indian GST statutory returns and invoice-level aggregation."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()

    def get_gstr1_b2b(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        GSTR-1 B2B: Invoices issued to registered taxable persons (customers with valid GSTIN).
        """
        sql = """
            SELECT 
                c.gstin as receiver_gstin,
                c.customer_name as receiver_name,
                s.invoice_no,
                s.sale_date as invoice_date,
                s.net_amount as invoice_value,
                s.total_taxable,
                s.total_cgst,
                s.total_sgst,
                s.total_igst,
                c.state as place_of_supply
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.sale_date BETWEEN ? AND ?
              AND c.gstin IS NOT NULL 
              AND c.gstin != ''
            ORDER BY s.sale_date ASC, s.invoice_no ASC;
        """
        rows = self.db.fetch_all(sql, (from_date, to_date))
        return [dict(r) for r in rows]

    def get_gstr1_b2c(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        GSTR-1 B2C Small: Intra-state sales to unregistered farmers / consumers, grouped by rate.
        """
        sql = """
            SELECT 
                (si.cgst_rate + si.sgst_rate + si.igst_rate) as gst_rate,
                SUM(si.taxable_amount) as total_taxable,
                SUM(si.cgst_amount) as total_cgst,
                SUM(si.sgst_amount) as total_sgst,
                SUM(si.igst_amount) as total_igst,
                SUM(si.total_amount) as total_invoice_value
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.sale_date BETWEEN ? AND ?
              AND (c.gstin IS NULL OR c.gstin = '')
            GROUP BY gst_rate
            ORDER BY gst_rate ASC;
        """
        rows = self.db.fetch_all(sql, (from_date, to_date))
        return [dict(r) for r in rows]

    def get_hsn_summary(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        GSTR-1 HSN Summary: Aggregated total quantity, taxable value, and tax by HSN Code.
        """
        sql = """
            SELECT 
                COALESCE(p.hsn_code, 'NA') as hsn_code,
                p.product_name,
                u.symbol as uqc,
                SUM(si.qty) as total_qty,
                SUM(si.taxable_amount) as total_taxable,
                SUM(si.cgst_amount) as total_cgst,
                SUM(si.sgst_amount) as total_sgst,
                SUM(si.igst_amount) as total_igst,
                SUM(si.total_amount) as total_amount
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN units u ON si.unit_id = u.unit_id
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY p.hsn_code, u.symbol
            ORDER BY p.hsn_code ASC;
        """
        rows = self.db.fetch_all(sql, (from_date, to_date))
        return [dict(r) for r in rows]

    def get_gst_rate_wise_summary(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Complete breakdown of sales and tax collected per GST tax slab."""
        sql = """
            SELECT 
                tg.tax_group_name,
                (si.cgst_rate + si.sgst_rate + si.igst_rate) as applied_rate,
                COUNT(DISTINCT s.sale_id) as total_invoices,
                SUM(si.taxable_amount) as total_taxable,
                SUM(si.cgst_amount) as total_cgst,
                SUM(si.sgst_amount) as total_sgst,
                SUM(si.igst_amount) as total_igst,
                SUM(si.total_amount) as total_gross
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN tax_groups tg ON p.tax_group_id = tg.tax_group_id
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY tg.tax_group_id, applied_rate
            ORDER BY applied_rate ASC;
        """
        rows = self.db.fetch_all(sql, (from_date, to_date))
        return [dict(r) for r in rows]
