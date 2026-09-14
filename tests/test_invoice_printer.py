"""
Automated Test Suite for ReportLab GST Invoice Printing Engine.
"""
from pathlib import Path
import pytest
from src.models import CompanySettings, Sale, SaleItem
from src.printing.invoice_printer import InvoicePrinter


def test_invoice_pdf_generation(tmp_path):
    """Test generating a GST Tax Invoice PDF."""
    settings = CompanySettings(
        company_name="Krishi Seva Kendra",
        address="Near Bus Stand, Station Road",
        city="Baramati",
        state="Maharashtra",
        pincode="413102",
        mobile="9890123456",
        gstin="27AABCU9603R1ZM",
        dl_fertilizer="LIC/FERT/2026/890",
        dl_pesticide="LIC/PEST/2026/123",
        dl_seed="LIC/SEED/2026/456",
        bank_name="State Bank of India",
        account_no="30012345678",
        ifsc_code="SBIN0000321",
    )

    printer = InvoicePrinter(company_settings=settings)

    items = [
        SaleItem(
            product_id=1,
            batch_id=1,
            product_name="IFFCO NPK 10:26:26 (50kg)",
            batch_no="NPK-2026-99",
            exp_date="2028-06-30",
            hsn_code="31052000",
            qty=4.0,
            unit_name="BAG",
            sale_rate=1470.0,
            mrp=1470.0,
            taxable_amount=5600.0,
            cgst_rate=2.5,
            cgst_amount=140.0,
            sgst_rate=2.5,
            sgst_amount=140.0,
            total_amount=5880.0,
        ),
        SaleItem(
            product_id=2,
            batch_id=2,
            product_name="Bayer Confidor Insecticide (100ml)",
            batch_no="CONF-887",
            exp_date="2027-11-30",
            hsn_code="38089190",
            qty=2.0,
            unit_name="BTL",
            sale_rate=450.0,
            mrp=480.0,
            taxable_amount=762.71,
            cgst_rate=9.0,
            cgst_amount=68.64,
            sgst_rate=9.0,
            sgst_amount=68.64,
            total_amount=900.0,
        ),
    ]

    sale = Sale(
        invoice_no="INV-2026-0042",
        sale_date="2026-09-12",
        customer_id=1,
        customer_name="Shivaji Babar",
        customer_mobile="9823456789",
        customer_village="Karhati",
        payment_mode="CASH",
        total_taxable=6362.71,
        total_cgst=208.64,
        total_sgst=208.64,
        round_off=0.01,
        net_amount=6780.0,
        paid_amount=6780.0,
        due_amount=0.0,
        items=items,
    )

    pdf_output_path = tmp_path / "test_tax_invoice.pdf"
    pdf_bytes = printer.generate_invoice_pdf(sale=sale, output_path=pdf_output_path)

    # Assert PDF file was written and starts with %PDF magic bytes
    assert pdf_output_path.exists()
    assert pdf_output_path.stat().st_size > 1000  # PDF is non-trivial size
    assert pdf_bytes.startswith(b"%PDF-")


def test_number_to_words():
    """Test Rupee amount in words conversion."""
    printer = InvoicePrinter()
    assert "SIX THOUSAND SEVEN HUNDRED EIGHTY" in printer._number_to_words(6780.0)
    assert "FIFTY THOUSAND" in printer._number_to_words(50000.0)
    assert "ONE LAKH TWENTY FIVE THOUSAND" in printer._number_to_words(125000.0)

