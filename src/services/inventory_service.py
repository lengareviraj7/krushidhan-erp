"""
Service Layer for Inventory Operations, FEFO Batch Allocation, and Expiry Alerts.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from src.db.connection import DatabaseManager, get_db_manager
from src.models.inventory import StockBatch, StockLedgerEntry
from src.repositories.inventory_repository import InventoryRepository


class InventoryService:
    """Business logic for inventory management, FEFO allocations, and stock valuation."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()
        self.inv_repo = InventoryRepository(self.db)

    def allocate_fefo_stock(self, product_id: int, requested_qty: float) -> List[Tuple[StockBatch, float]]:
        """
        Allocates stock automatically across batches based on FEFO (First Expired First Out).
        Returns a list of (StockBatch, allocated_qty).
        Raises ValueError if total stock is insufficient.
        """
        batches = self.inv_repo.get_available_batches_fefo(product_id)
        total_available = sum(b.current_qty for b in batches)

        if total_available < requested_qty:
            raise ValueError(
                f"Insufficient stock for product ID {product_id}. Requested: {requested_qty}, Available: {total_available}"
            )

        allocations: List[Tuple[StockBatch, float]] = []
        remaining = requested_qty

        for batch in batches:
            if remaining <= 0:
                break
            allocated = min(batch.current_qty, remaining)
            allocations.append((batch, allocated))
            remaining -= allocated

        return allocations

    def get_stock_statement(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get inventory valuation summary with item details."""
        return self.inv_repo.get_stock_inventory_summary(category_id)

    def get_expiry_reminders(self, days_threshold: int = 90) -> List[Dict[str, Any]]:
        """
        Find batches expiring within `days_threshold` days (default 90 days / 3 months).
        """
        threshold_date = (datetime.now() + timedelta(days=days_threshold)).strftime("%Y-%m-%d")
        today_date = datetime.now().strftime("%Y-%m-%d")

        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                c.category_name,
                m.manufacturer_name,
                u.symbol as unit_symbol,
                sb.batch_id,
                sb.batch_no,
                sb.exp_date,
                sb.current_qty,
                sb.purchase_rate,
                sb.sale_rate,
                (sb.current_qty * sb.purchase_rate) as total_value,
                CAST(julianday(sb.exp_date) - julianday(?) AS INTEGER) as days_to_expiry
            FROM stock_batches sb
            JOIN products p ON sb.product_id = p.product_id
            LEFT JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN units u ON p.unit_id = u.unit_id
            WHERE sb.current_qty > 0 
              AND sb.exp_date IS NOT NULL 
              AND sb.exp_date != ''
              AND sb.exp_date <= ?
            ORDER BY sb.exp_date ASC;
        """
        rows = self.db.fetch_all(sql, (today_date, threshold_date))
        return [dict(r) for r in rows]

    def get_low_stock_alerts(self) -> List[Dict[str, Any]]:
        """Get products whose total stock has fallen below their configured min_stock_alert."""
        sql = """
            SELECT 
                p.product_id,
                p.product_name,
                p.min_stock_alert,
                c.category_name,
                m.manufacturer_name,
                u.symbol as unit_symbol,
                COALESCE(SUM(sb.current_qty), 0) as current_total_stock
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN units u ON p.unit_id = u.unit_id
            LEFT JOIN stock_batches sb ON p.product_id = sb.product_id
            WHERE p.is_active = 1 AND p.min_stock_alert > 0
            GROUP BY p.product_id
            HAVING current_total_stock <= p.min_stock_alert
            ORDER BY current_total_stock ASC;
        """
        rows = self.db.fetch_all(sql)
        return [dict(r) for r in rows]
