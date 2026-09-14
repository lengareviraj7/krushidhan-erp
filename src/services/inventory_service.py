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

    def add_direct_stock(
        self,
        product_id: int,
        qty: float,
        batch_no: Optional[str] = None,
        purchase_rate: Optional[float] = None,
        sale_rate: Optional[float] = None,
        mrp: Optional[float] = None,
        mfg_date: Optional[str] = None,
        exp_date: Optional[str] = None,
        remarks: Optional[str] = "Manual Stock Addition",
    ) -> Dict[str, Any]:
        """Directly add new or additional stock batch to inventory."""
        if qty <= 0:
            raise ValueError("Quantity to add must be greater than 0.")

        product = self.db.fetch_one("SELECT * FROM products WHERE product_id = ?;", (product_id,))
        if not product:
            raise ValueError(f"Product with ID {product_id} does not exist.")

        batch_code = (batch_no or "").strip()
        if not batch_code:
            today_str = datetime.now().strftime("%y%m%d")
            batch_code = f"STK-{today_str}-{product_id}"

        pur_rate = float(purchase_rate) if purchase_rate is not None and purchase_rate > 0 else float(product["default_purchase_rate"] or 0.0)
        s_rate = float(sale_rate) if sale_rate is not None and sale_rate > 0 else float(product["default_sale_rate"] or 0.0)
        m_rate = float(mrp) if mrp is not None and mrp > 0 else float(product["mrp"] or s_rate)

        with self.db.transaction() as conn:
            batch = StockBatch(
                product_id=product_id,
                batch_no=batch_code,
                mfg_date=mfg_date,
                exp_date=exp_date,
                purchase_rate=pur_rate,
                sale_rate=s_rate,
                mrp=m_rate,
                opening_qty=0.0,
                current_qty=qty,
            )
            batch_id = self.inv_repo.upsert_batch(batch, conn=conn)

            # Record stock ledger movement
            ledger_entry = StockLedgerEntry(
                product_id=product_id,
                batch_id=batch_id,
                transaction_type="PURCHASE",
                reference_type="MANUAL_STOCK_INWARD",
                reference_id=batch_id,
                qty_in=qty,
                qty_out=0.0,
                balance_qty=qty,
                rate=pur_rate,
                remarks=remarks or "Manual Stock Addition",
            )
            self.inv_repo.record_stock_movement(ledger_entry, conn=conn)

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product["product_name"],
            "batch_id": batch_id,
            "batch_no": batch_code,
            "added_qty": qty,
            "purchase_rate": pur_rate,
            "sale_rate": s_rate,
            "message": f"Successfully added {qty} stock for {product['product_name']}",
        }

