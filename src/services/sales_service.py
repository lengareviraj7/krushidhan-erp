"""
Service Layer for Sales Invoicing, Tax Calculations, Stock Deductions, and Customer Accounting.
"""
from __future__ import annotations

from typing import List, Optional
from src.db.connection import DatabaseManager, get_db_manager
from src.models.accounting import LedgerEntry, Voucher
from src.models.inventory import StockLedgerEntry
from src.models.sales import Sale, SaleItem
from src.repositories.accounting_repository import AccountingRepository
from src.repositories.inventory_repository import InventoryRepository
from src.repositories.master_data_repository import MasterDataRepository
from src.repositories.sales_repository import SalesRepository


class SalesService:
    """Business logic for sales billing, tax calculations, FEFO batch deduction, and accounting."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()
        self.sales_repo = SalesRepository(self.db)
        self.inventory_repo = InventoryRepository(self.db)
        self.master_repo = MasterDataRepository(self.db)
        self.accounting_repo = AccountingRepository(self.db)

    def calculate_item_tax(
        self,
        qty: float,
        rate: float,
        discount_percent: float,
        cgst_rate: float,
        sgst_rate: float,
        igst_rate: float,
        is_rate_tax_inclusive: bool = True,
    ) -> dict:
        """
        Calculate taxable amount and GST breakdown for a line item.
        In Agri retail, rates quoted to farmers are typically GST-inclusive.
        """
        gross_amount = qty * rate
        discount_amount = round(gross_amount * (discount_percent / 100.0), 2)
        net_after_discount = gross_amount - discount_amount

        total_tax_rate = (cgst_rate + sgst_rate) if (cgst_rate + sgst_rate) > 0 else igst_rate

        if is_rate_tax_inclusive:
            if total_tax_rate > 0:
                taxable_amount = round(net_after_discount / (1.0 + (total_tax_rate / 100.0)), 2)
                total_tax = round(net_after_discount - taxable_amount, 2)
            else:
                taxable_amount = round(net_after_discount, 2)
                total_tax = 0.0

            if igst_rate > 0:
                igst_amount = total_tax
                cgst_amount = 0.0
                sgst_amount = 0.0
            else:
                cgst_amount = round(taxable_amount * (cgst_rate / 100.0), 2)
                sgst_amount = round(taxable_amount * (sgst_rate / 100.0), 2)
                igst_amount = 0.0

            total_line_amount = round(taxable_amount + cgst_amount + sgst_amount + igst_amount, 2)
        else:
            taxable_amount = round(net_after_discount, 2)
            cgst_amount = round(taxable_amount * (cgst_rate / 100.0), 2)
            sgst_amount = round(taxable_amount * (sgst_rate / 100.0), 2)
            igst_amount = round(taxable_amount * (igst_rate / 100.0), 2)
            total_line_amount = round(taxable_amount + cgst_amount + sgst_amount + igst_amount, 2)

        return {
            "discount_amount": discount_amount,
            "taxable_amount": taxable_amount,
            "cgst_amount": cgst_amount,
            "sgst_amount": sgst_amount,
            "igst_amount": igst_amount,
            "total_amount": total_line_amount,
        }

    def process_sales_invoice(self, sale: Sale) -> int:
        """
        Process and persist sales invoice atomically:
        1. Validate stock availability for each batch.
        2. Deduct batch current_qty.
        3. Insert sale header and line items.
        4. Record stock movement in stock_ledger.
        5. Update customer balance for any due credit amount.
        6. Post double-entry accounting voucher.
        """
        with self.db.transaction() as conn:
            # 1 & 2. Validate and deduct batch stock
            for item in sale.items:
                batch = self.inventory_repo.get_or_create_batch_for_sale(
                    product_id=item.product_id,
                    batch_id=item.batch_id,
                    batch_no=item.batch_no,
                    sale_qty=item.qty,
                    sale_rate=item.sale_rate,
                    conn=conn,
                )
                item.batch_id = batch.batch_id
                item.batch_no = batch.batch_no
                if not item.exp_date and batch.exp_date:
                    item.exp_date = batch.exp_date

                # Deduct batch stock
                self.inventory_repo.deduct_batch_stock(batch.batch_id, item.qty, conn=conn)

            # 3. Create sales record
            sale_id = self.sales_repo.create_sale(sale, conn=conn)

            # 4. Record stock movements
            for item in sale.items:
                curr_stock = self.inventory_repo.get_product_total_stock(item.product_id)
                self.inventory_repo.record_stock_movement(
                    StockLedgerEntry(
                        product_id=item.product_id,
                        batch_id=item.batch_id,
                        transaction_type="SALE",
                        reference_type="INVOICE",
                        reference_id=sale_id,
                        qty_in=0.0,
                        qty_out=item.qty,
                        balance_qty=curr_stock,
                        rate=item.sale_rate,
                        remarks=f"Sale Invoice: {sale.invoice_no}",
                    ),
                    conn=conn,
                )

            # 5. Update Customer Balance if credit sale
            unpaid_due = sale.net_amount - sale.paid_amount
            if unpaid_due > 0:
                self.master_repo.update_customer_balance(sale.customer_id, unpaid_due, conn=conn)

            # 6. Post double-entry accounting voucher
            self._post_sales_voucher(sale, sale_id, conn)

            return sale_id

    def _post_sales_voucher(self, sale: Sale, sale_id: int, conn) -> None:
        """Post double-entry voucher for sale."""
        sales_ac = self.accounting_repo.get_account_by_name("Sales Account")
        cgst_out_ac = self.accounting_repo.get_account_by_name("CGST Output Account")
        sgst_out_ac = self.accounting_repo.get_account_by_name("SGST Output Account")
        igst_out_ac = self.accounting_repo.get_account_by_name("IGST Output Account")
        cash_ac = self.accounting_repo.get_account_by_name("Cash in Hand")
        bank_ac = self.accounting_repo.get_account_by_name("Bank Account")

        entries = []

        # Debit Cash/Bank for paid amount
        if sale.paid_amount > 0:
            pay_ac = cash_ac if sale.payment_mode == "CASH" else bank_ac
            entries.append(
                LedgerEntry(
                    account_id=pay_ac.account_id,
                    debit_amount=sale.paid_amount,
                    credit_amount=0.0,
                    particulars=f"Sale Receipt Inv {sale.invoice_no}",
                )
            )

        # Debit Customer / Accounts Receivable for due amount
        due = sale.net_amount - sale.paid_amount
        if due > 0:
            entries.append(
                LedgerEntry(
                    account_id=sales_ac.account_id,  # or Accounts Receivable mapping
                    debit_amount=due,
                    credit_amount=0.0,
                    particulars=f"Credit Sale to Cust ID: {sale.customer_id}",
                )
            )

        # Credit Sales Account with taxable value
        if sale.total_taxable > 0:
            entries.append(
                LedgerEntry(
                    account_id=sales_ac.account_id,
                    debit_amount=0.0,
                    credit_amount=sale.total_taxable,
                    particulars="Sales Revenue",
                )
            )

        # Credit Output GST
        if sale.total_cgst > 0 and cgst_out_ac:
            entries.append(
                LedgerEntry(
                    account_id=cgst_out_ac.account_id,
                    debit_amount=0.0,
                    credit_amount=sale.total_cgst,
                    particulars="Output CGST",
                )
            )
        if sale.total_sgst > 0 and sgst_out_ac:
            entries.append(
                LedgerEntry(
                    account_id=sgst_out_ac.account_id,
                    debit_amount=0.0,
                    credit_amount=sale.total_sgst,
                    particulars="Output SGST",
                )
            )
        if sale.total_igst > 0 and igst_out_ac:
            entries.append(
                LedgerEntry(
                    account_id=igst_out_ac.account_id,
                    debit_amount=0.0,
                    credit_amount=sale.total_igst,
                    particulars="Output IGST",
                )
            )

        tot_dr = sum(e.debit_amount for e in entries)
        tot_cr = sum(e.credit_amount for e in entries)
        if round(tot_dr, 2) == round(tot_cr, 2) and tot_dr > 0:
            vch_no = self.accounting_repo.generate_next_voucher_no("RECEIPT" if due == 0 else "JOURNAL")
            vch = Voucher(
                voucher_no=vch_no,
                voucher_date=sale.sale_date,
                voucher_type="RECEIPT" if due == 0 else "JOURNAL",
                total_amount=sale.net_amount,
                narration=f"Sales Bill #{sale.invoice_no}",
                reference_type="SALE",
                reference_id=sale_id,
                entries=entries,
            )
            self.accounting_repo.create_voucher(vch, conn=conn)
