"""
Service Layer for MIS Reports and Business Analytics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from src.db.connection import DatabaseManager, get_db_manager


class ReportService:
    """Business logic for MIS reports, product sales performance, customer balances, and statements."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()

    def get_sales_by_item(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Item-wise sales quantity and total turnover report."""
        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                c.category_name,
                m.manufacturer_name,
                u.symbol as unit_symbol,
                SUM(si.qty) as total_sold_qty,
                SUM(si.taxable_amount) as total_taxable,
                SUM(si.total_amount) as total_sales_amount
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN units u ON si.unit_id = u.unit_id
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY p.product_id
            ORDER BY total_sales_amount DESC;
        """
        rows = self.db.fetch_all(sql, (from_date, to_date))
        return [dict(r) for r in rows]

    def get_sales_by_manufacturer(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Manufacturer/Company-wise sales performance statement."""
        sql = """
            SELECT 
                COALESCE(m.manufacturer_name, 'Unknown / Unassigned') as company_name,
                COUNT(DISTINCT s.sale_id) as bills_count,
                SUM(si.taxable_amount) as total_taxable,
                SUM(si.total_amount) as total_sales_amount
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY m.manufacturer_id
            ORDER BY total_sales_amount DESC;
        """
        rows = self.db.fetch_all(sql, (from_date, to_date))
        return [dict(r) for r in rows]

    def get_outstanding_receivables(self) -> List[Dict[str, Any]]:
        """Customer ledger balance report with pending dues."""
        sql = """
            SELECT 
                customer_id,
                customer_name,
                mobile,
                village,
                current_balance,
                credit_limit
            FROM customers
            WHERE current_balance > 0
            ORDER BY current_balance DESC;
        """
        rows = self.db.fetch_all(sql)
        return [dict(r) for r in rows]

    def get_outstanding_payables(self) -> List[Dict[str, Any]]:
        """Supplier balance report with pending dues to pay."""
        sql = """
            SELECT 
                supplier_id,
                supplier_name,
                mobile,
                city,
                current_balance
            FROM suppliers
            WHERE current_balance > 0
            ORDER BY current_balance DESC;
        """
        rows = self.db.fetch_all(sql)
        return [dict(r) for r in rows]
