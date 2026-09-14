"""
Statutory Agricultural Department Registers & Compliance Service.
Generates inspection-ready registers for:
1. Fertilizer Stock & Sale Register (खत विक्री नोंदवही - FCO Compliance)
2. Insecticide & Pesticide Sale Register (कीटकनाशक विक्री नोंदवही - Insecticides Act)
3. Seed Sale Register (बियाणे विक्री नोंदवही - Seeds Act)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from src.db.connection import DatabaseManager, get_db_manager


class StatutoryService:
    """Service for statutory compliance registers audited by Agriculture Quality Control Officers."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()

    def get_fertilizer_register(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fertilizer Stock & Sale Register under Fertilizer Control Order (FCO).
        Includes Bill No, Date, Farmer Name, Aadhaar/Mobile, Village, Fertilizer Name, Batch, Qty, Rate, Total.
        """
        start = from_date or "2000-01-01"
        end = to_date or "2099-12-31"
        sql = """
            SELECT 
                s.sale_id,
                s.invoice_no,
                s.sale_date,
                c.customer_name as farmer_name,
                c.mobile as farmer_mobile,
                c.village as farmer_village,
                c.aadhar_no as farmer_aadhaar,
                p.product_name as fertilizer_name,
                m.manufacturer_name as company_name,
                sb.batch_no,
                sb.exp_date,
                si.qty,
                u.symbol as unit_symbol,
                si.sale_rate,
                si.taxable_amount,
                (si.cgst_amount + si.sgst_amount + si.igst_amount) as tax_amount,
                si.total_amount
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            JOIN customers c ON s.customer_id = c.customer_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN stock_batches sb ON si.batch_id = sb.batch_id
            LEFT JOIN units u ON p.unit_id = u.unit_id
            WHERE s.sale_date >= ? AND s.sale_date <= ?
              AND (cat.category_name LIKE '%Fertilizer%' OR cat.short_name = 'FERT' OR cat.category_id = 1)
            ORDER BY s.sale_date ASC, s.invoice_no ASC;
        """
        rows = self.db.fetch_all(sql, (start, end))
        return [dict(r) for r in rows]

    def get_pesticide_register(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Insecticides and Pesticides Sale Register under the Insecticides Act, 1968.
        Includes Technical Name, Batch No, Manufacturing Date, Expiry Date, Farmer Name, Target Crop, Qty.
        """
        start = from_date or "2000-01-01"
        end = to_date or "2099-12-31"
        sql = """
            SELECT 
                s.sale_id,
                s.invoice_no,
                s.sale_date,
                c.customer_name as farmer_name,
                c.mobile as farmer_mobile,
                c.village as farmer_village,
                p.product_name as pesticide_name,
                p.hsn_code,
                m.manufacturer_name as company_name,
                sb.batch_no,
                sb.mfg_date,
                sb.exp_date,
                si.qty,
                u.symbol as unit_symbol,
                si.sale_rate,
                si.total_amount
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            JOIN customers c ON s.customer_id = c.customer_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN stock_batches sb ON si.batch_id = sb.batch_id
            LEFT JOIN units u ON p.unit_id = u.unit_id
            WHERE s.sale_date >= ? AND s.sale_date <= ?
              AND (cat.category_name LIKE '%Pesticide%' OR cat.category_name LIKE '%Insecticide%' OR cat.category_name LIKE '%Fungicide%' OR cat.short_name IN ('PEST', 'FUNG') OR cat.category_id IN (3, 4, 5))
            ORDER BY s.sale_date ASC, s.invoice_no ASC;
        """
        rows = self.db.fetch_all(sql, (start, end))
        return [dict(r) for r in rows]

    def get_seed_register(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Certified / Hybrid Seed Sale Register under the Seeds Act, 1966.
        Includes Variety Name, Lot/Batch No, Germination %, Valid Upto, Farmer Name, Qty.
        """
        start = from_date or "2000-01-01"
        end = to_date or "2099-12-31"
        sql = """
            SELECT 
                s.sale_id,
                s.invoice_no,
                s.sale_date,
                c.customer_name as farmer_name,
                c.mobile as farmer_mobile,
                c.village as farmer_village,
                p.product_name as seed_variety,
                m.manufacturer_name as seed_company,
                sb.batch_no as lot_no,
                sb.exp_date as valid_upto,
                si.qty,
                u.symbol as unit_symbol,
                si.sale_rate,
                si.total_amount
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN products p ON si.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            JOIN customers c ON s.customer_id = c.customer_id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.manufacturer_id
            LEFT JOIN stock_batches sb ON si.batch_id = sb.batch_id
            LEFT JOIN units u ON p.unit_id = u.unit_id
            WHERE s.sale_date >= ? AND s.sale_date <= ?
              AND (cat.category_name LIKE '%Seed%' OR cat.short_name = 'SEED' OR cat.category_id = 2)
            ORDER BY s.sale_date ASC, s.invoice_no ASC;
        """
        rows = self.db.fetch_all(sql, (start, end))
        return [dict(r) for r in rows]
