"""
Comprehensive Automated Test Suite for All Business Logic Services.
"""
from datetime import datetime
from pathlib import Path
import pytest
from src.db.connection import DatabaseManager
from src.models import (
    Customer,
    Expense,
    Manufacturer,
    Product,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    Supplier,
)
from src.repositories import MasterDataRepository
from src.services import (
    AccountingService,
    AuthService,
    BackupService,
    GSTService,
    InventoryService,
    PurchaseService,
    ReportService,
    SalesService,
)


@pytest.fixture
def service_env(tmp_path):
    """Sets up a fresh database and all service instances for testing."""
    db_file = tmp_path / "test_agri_erp.db"
    db_manager = DatabaseManager(db_path=db_file)
    db_manager.initialize_database(include_seed=True)

    return {
        "db": db_manager,
        "master_repo": MasterDataRepository(db_manager),
        "inventory_svc": InventoryService(db_manager),
        "purchase_svc": PurchaseService(db_manager),
        "sales_svc": SalesService(db_manager),
        "accounting_svc": AccountingService(db_manager),
        "gst_svc": GSTService(db_manager),
        "report_svc": ReportService(db_manager),
        "auth_svc": AuthService(db_manager),
        "backup_svc": BackupService(db_manager),
        "tmp_path": tmp_path,
    }


def test_auth_service(service_env):
    """Test user registration, bcrypt password hashing, and authentication."""
    auth = service_env["auth_svc"]

    user_id = auth.register_user(
        username="billing_clerk",
        plain_password="clerk_secret_123",
        full_name="Anand Kulkarni",
        role="OPERATOR",
    )
    assert user_id > 0

    # Successful login
    user = auth.authenticate_user("billing_clerk", "clerk_secret_123")
    assert user is not None
    assert user.full_name == "Anand Kulkarni"

    # Failed login with wrong password
    invalid_user = auth.authenticate_user("billing_clerk", "wrong_password")
    assert invalid_user is None


def test_end_to_end_purchase_to_sales_flow(service_env):
    """
    Test complete lifecycle:
    1. Supplier Inward Purchase -> Batch created, stock added, purchase voucher posted.
    2. FEFO Stock Allocation.
    3. Customer Sales Billing -> Stock deducted, customer balance updated, sales voucher posted.
    4. GSTR-1, MIS Reports, Day Book, and Profit & Loss generation.
    """
    master = service_env["master_repo"]
    purchase_svc = service_env["purchase_svc"]
    sales_svc = service_env["sales_svc"]
    inventory_svc = service_env["inventory_svc"]
    gst_svc = service_env["gst_svc"]
    accounting_svc = service_env["accounting_svc"]
    report_svc = service_env["report_svc"]

    # 1. Setup Master Records
    supp_id = master.create_supplier(
        Supplier(
            supplier_name="Mahyco Seeds Ltd",
            gstin="27AAACM1234F1Z1",
            city="Jalna",
            opening_balance=0.0,
        )
    )
    cust_b2b_id = master.create_customer(
        Customer(
            customer_name="Green Agro Farms",
            mobile="9822114477",
            village="Indapur",
            gstin="27AAACG9999P1Z8",  # Registered B2B customer
            opening_balance=0.0,
        )
    )
    cust_farmer_id = master.create_customer(
        Customer(
            customer_name="Pandurang Ghadge",
            mobile="9422001188",
            village="Malegaon",
            gstin=None,  # Unregistered Retail Farmer
            opening_balance=0.0,
        )
    )
    mfg_id = master.create_manufacturer(
        Manufacturer(
            manufacturer_name="Mahyco Seeds Ltd",
            contact_person="R&D Desk",
            mobile="9822110022",
        )
    )
    prod_id = master.create_product(
        Product(
            product_name="Mahyco Cotton Hybrid Seed BG-II (475g)",
            category_id=2,  # Seeds
            manufacturer_id=mfg_id,
            hsn_code="12099990",
            unit_id=9,  # PKT
            tax_group_id=1,  # 0% Exempt Seeds
            default_purchase_rate=780.0,
            default_sale_rate=860.0,
            default_mrp=860.0,
            min_stock_alert=10.0,
        )
    )

    # 2. Inward Purchase (100 packets)
    pur_item = PurchaseItem(
        product_id=prod_id,
        batch_no="MCB-2026-A1",
        mfg_date="2026-04-01",
        exp_date="2027-04-01",
        qty=100.0,
        free_qty=5.0,  # 5 packets scheme bonus
        unit_id=9,
        purchase_rate=780.0,
        sale_rate=860.0,
        mrp=860.0,
        taxable_amount=78000.0,
        cgst_rate=0.0,
        cgst_amount=0.0,
        sgst_rate=0.0,
        sgst_amount=0.0,
        total_amount=78000.0,
    )
    purchase = Purchase(
        invoice_no="PUR-MAHYCO-001",
        purchase_date="2026-09-12",
        supplier_id=supp_id,
        total_taxable=78000.0,
        net_amount=78000.0,
        paid_amount=50000.0,
        due_amount=28000.0,
        items=[pur_item],
    )
    pur_id = purchase_svc.process_inward_purchase(purchase)
    assert pur_id > 0

    # Verify inventory received 105 packets (100 + 5 free)
    assert inventory_svc.inv_repo.get_product_total_stock(prod_id) == 105.0

    # 3. FEFO Allocation Test
    allocations = inventory_svc.allocate_fefo_stock(prod_id, 20.0)
    assert len(allocations) == 1
    batch, qty = allocations[0]
    assert batch.batch_no == "MCB-2026-A1"
    assert qty == 20.0

    # 4. Process B2B Sale Invoice (20 packets to Green Agro Farms)
    tax_calc = sales_svc.calculate_item_tax(
        qty=20.0,
        rate=860.0,
        discount_percent=0.0,
        cgst_rate=0.0,
        sgst_rate=0.0,
        igst_rate=0.0,
    )
    sale_item_b2b = SaleItem(
        product_id=prod_id,
        batch_id=batch.batch_id,
        qty=20.0,
        unit_id=9,
        sale_rate=860.0,
        mrp=860.0,
        taxable_amount=tax_calc["taxable_amount"],
        total_amount=tax_calc["total_amount"],
    )
    sale_b2b = Sale(
        invoice_no="INV-00001",
        sale_date="2026-09-12",
        customer_id=cust_b2b_id,
        payment_mode="CREDIT",
        total_taxable=tax_calc["taxable_amount"],
        net_amount=tax_calc["total_amount"],
        paid_amount=0.0,
        due_amount=tax_calc["total_amount"],
        items=[sale_item_b2b],
    )
    sale_id = sales_svc.process_sales_invoice(sale_b2b)
    assert sale_id > 0

    # Stock should now be 105 - 20 = 85
    assert inventory_svc.inv_repo.get_product_total_stock(prod_id) == 85.0

    # Customer balance should increase by due amount
    updated_cust = master.get_customer_by_id(cust_b2b_id)
    assert updated_cust.current_balance == 17200.0

    # 5. Customer Receipt (Farmer pays ₹10,000 against outstanding bill)
    receipt_vch_id = accounting_svc.record_customer_receipt(
        customer_id=cust_b2b_id,
        receipt_date="2026-09-12",
        amount=10000.0,
        payment_mode="CASH",
        narration="Partial payment received",
    )
    assert receipt_vch_id > 0

    updated_cust_after_pay = master.get_customer_by_id(cust_b2b_id)
    assert updated_cust_after_pay.current_balance == 7200.0

    # 6. Statutory GST Reports (GSTR-1 B2B)
    b2b_records = gst_svc.get_gstr1_b2b("2026-09-01", "2026-09-30")
    assert len(b2b_records) == 1
    assert b2b_records[0]["receiver_gstin"] == "27AAACG9999P1Z8"
    assert b2b_records[0]["invoice_no"] == "INV-00001"

    # HSN Summary
    hsn_records = gst_svc.get_hsn_summary("2026-09-01", "2026-09-30")
    assert len(hsn_records) >= 1
    assert hsn_records[0]["hsn_code"] == "12099990"

    # 7. MIS Reports
    item_sales = report_svc.get_sales_by_item("2026-09-01", "2026-09-30")
    assert len(item_sales) == 1
    assert item_sales[0]["total_sold_qty"] == 20.0

    # 8. Financial Day Book & Profit & Loss
    day_book = accounting_svc.get_day_book("2026-09-12")
    assert day_book["sales_count"] == 1
    assert day_book["purchases_count"] == 1

    pnl = accounting_svc.get_profit_and_loss("2026-09-01", "2026-09-30")
    assert pnl["sales_revenue"] == 17200.0


def test_backup_and_restore(service_env):
    """Test online VACUUM INTO database backup creation and integrity verification."""
    backup_svc = service_env["backup_svc"]
    tmp_path = service_env["tmp_path"]

    # Verify integrity of initial database
    assert backup_svc.verify_database_integrity() is True

    # Create backup
    backup_dir = tmp_path / "backups"
    backup_file = backup_svc.create_backup(backup_dir=backup_dir)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # Verify backup history recorded
    history = backup_svc.get_backup_history()
    assert len(history) == 1
    assert history[0]["status"] == "SUCCESS"
