"""
Automated Test Suite for Data Repositories (Phase 2).
"""
import pytest
from src.db.connection import DatabaseManager
from src.models import (
    AuditLogEntry,
    Category,
    CompanySettings,
    Crop,
    Customer,
    Expense,
    LedgerAccount,
    LedgerEntry,
    Manufacturer,
    Product,
    Purchase,
    PurchaseItem,
    Sale,
    SaleItem,
    StockBatch,
    StockLedgerEntry,
    Supplier,
    User,
    Voucher,
)
from src.repositories import (
    AccountingRepository,
    InventoryRepository,
    MasterDataRepository,
    PurchaseRepository,
    SalesRepository,
    SystemRepository,
)


@pytest.fixture
def test_env(tmp_path):
    """Sets up a temporary SQLite database and instantiates all repositories."""
    db_file = tmp_path / "test_agri_erp.db"
    db_manager = DatabaseManager(db_path=db_file)
    db_manager.initialize_database(include_seed=True)

    return {
        "db": db_manager,
        "master": MasterDataRepository(db_manager),
        "inventory": InventoryRepository(db_manager),
        "purchase": PurchaseRepository(db_manager),
        "sales": SalesRepository(db_manager),
        "accounting": AccountingRepository(db_manager),
        "system": SystemRepository(db_manager),
    }


def test_master_data_crud(test_env):
    """Test Category, Manufacturer, Product, Customer and Supplier CRUD operations."""
    master = test_env["master"]

    # 1. Create Category & Manufacturer
    cat_id = master.create_category(Category(category_name="Bio-Pesticides", short_name="BIO-P"))
    mfg_id = master.create_manufacturer(Manufacturer(manufacturer_name="Syngenta India", mobile="9822001122"))
    assert cat_id > 0
    assert mfg_id > 0

    # 2. Create Product
    prod = Product(
        product_name="Syngenta Ampligo (100 ml)",
        category_id=cat_id,
        manufacturer_id=mfg_id,
        hsn_code="38089190",
        unit_id=8,  # Bottle
        tax_group_id=4,  # 18%
        default_purchase_rate=750.0,
        default_sale_rate=850.0,
        default_mrp=920.0,
        min_stock_alert=10.0,
    )
    prod_id = master.create_product(prod)
    assert prod_id > 0

    # Retrieve & Search Product
    fetched_prod = master.get_product_by_id(prod_id)
    assert fetched_prod.product_name == "Syngenta Ampligo (100 ml)"

    search_results = master.search_products("Ampligo")
    assert len(search_results) == 1
    assert search_results[0]["category_name"] == "Bio-Pesticides"
    assert search_results[0]["manufacturer_name"] == "Syngenta India"

    # 3. Create Customer
    cust = Customer(
        customer_name="Ramesh Patil",
        mobile="9890123456",
        village="Baramati",
        opening_balance=500.0,
    )
    cust_id = master.create_customer(cust)
    assert cust_id > 0

    fetched_cust = master.get_customer_by_id(cust_id)
    assert fetched_cust.customer_name == "Ramesh Patil"
    assert fetched_cust.current_balance == 500.0

    # Update Customer Balance
    master.update_customer_balance(cust_id, 1200.0)
    updated_cust = master.get_customer_by_id(cust_id)
    assert updated_cust.current_balance == 1700.0


def test_inventory_fefo_and_stock_ledger(test_env):
    """Test batch management, First Expired First Out (FEFO) sorting, and stock ledger recording."""
    master = test_env["master"]
    inventory = test_env["inventory"]

    # Create test product
    prod_id = master.create_product(
        Product(
            product_name="Urea 45kg Bag",
            category_id=1,
            unit_id=5,
            tax_group_id=2,
            default_purchase_rate=266.5,
            default_sale_rate=266.5,
        )
    )

    # Insert Batch 1: Expiring 2026-12-31
    b1_id = inventory.upsert_batch(
        StockBatch(
            product_id=prod_id,
            batch_no="UREA-BATCH-001",
            exp_date="2026-12-31",
            purchase_rate=266.5,
            sale_rate=266.5,
            mrp=266.5,
            current_qty=50.0,
        )
    )

    # Insert Batch 2: Expiring earlier 2026-06-30
    b2_id = inventory.upsert_batch(
        StockBatch(
            product_id=prod_id,
            batch_no="UREA-BATCH-002",
            exp_date="2026-06-30",
            purchase_rate=266.5,
            sale_rate=266.5,
            mrp=266.5,
            current_qty=30.0,
        )
    )

    # Total stock check
    assert inventory.get_product_total_stock(prod_id) == 80.0

    # FEFO Sorting verification: Batch 2 (June 2026) must appear before Batch 1 (Dec 2026)
    fefo_batches = inventory.get_available_batches_fefo(prod_id)
    assert len(fefo_batches) == 2
    assert fefo_batches[0].batch_no == "UREA-BATCH-002"
    assert fefo_batches[1].batch_no == "UREA-BATCH-001"

    # Deduct stock from Batch 2
    inventory.deduct_batch_stock(b2_id, 10.0)
    assert inventory.get_batch_by_id(b2_id).current_qty == 20.0
    assert inventory.get_product_total_stock(prod_id) == 70.0

    # Record stock ledger movement
    ledger_id = inventory.record_stock_movement(
        StockLedgerEntry(
            product_id=prod_id,
            batch_id=b2_id,
            transaction_type="SALE",
            reference_type="INVOICE",
            reference_id=101,
            qty_in=0,
            qty_out=10.0,
            balance_qty=70.0,
            rate=266.5,
            remarks="Sold to farmer",
        )
    )
    assert ledger_id > 0


def test_purchase_and_sales_flow(test_env):
    """Test end-to-end purchase invoice and sales invoice creation with line items."""
    master = test_env["master"]
    inventory = test_env["inventory"]
    purchase_repo = test_env["purchase"]
    sales_repo = test_env["sales"]

    # 1. Setup Product, Supplier, Customer
    supp_id = master.create_supplier(Supplier(supplier_name="IFFCO Fertilizer Depot", gstin="27AAAAA0000A1Z5"))
    cust_id = master.create_customer(Customer(customer_name="Suresh Shinde", mobile="9422334455"))
    prod_id = master.create_product(
        Product(
            product_name="DAP 50kg (IFFCO)",
            category_id=1,
            unit_id=5,
            tax_group_id=2,  # 5% GST
            default_purchase_rate=1300.0,
            default_sale_rate=1350.0,
            default_mrp=1350.0,
        )
    )

    # 2. Record Inward Purchase
    pur_item = PurchaseItem(
        product_id=prod_id,
        batch_no="DAP-IFFCO-99",
        mfg_date="2026-01-01",
        exp_date="2028-01-01",
        qty=100.0,
        purchase_rate=1300.0,
        sale_rate=1350.0,
        mrp=1350.0,
        taxable_amount=130000.0,
        cgst_rate=2.5,
        cgst_amount=3250.0,
        sgst_rate=2.5,
        sgst_amount=3250.0,
        total_amount=136500.0,
    )
    pur = Purchase(
        invoice_no="PUR-2026-881",
        purchase_date="2026-09-12",
        supplier_id=supp_id,
        total_taxable=130000.0,
        total_cgst=3250.0,
        total_sgst=3250.0,
        net_amount=136500.0,
        paid_amount=100000.0,
        due_amount=36500.0,
        items=[pur_item],
    )
    pur_id = purchase_repo.create_purchase(pur)
    assert pur_id > 0

    fetched_pur = purchase_repo.get_purchase_by_id(pur_id)
    assert fetched_pur.invoice_no == "PUR-2026-881"
    assert len(fetched_pur.items) == 1
    assert fetched_pur.items[0].batch_no == "DAP-IFFCO-99"

    # Add batch to stock
    batch_id = inventory.upsert_batch(
        StockBatch(
            product_id=prod_id,
            batch_no="DAP-IFFCO-99",
            mfg_date="2026-01-01",
            exp_date="2028-01-01",
            purchase_rate=1300.0,
            sale_rate=1350.0,
            mrp=1350.0,
            current_qty=100.0,
        )
    )

    # 3. Record Sales Bill
    inv_no = sales_repo.generate_next_invoice_no()
    assert inv_no == "INV-00001"

    sale_item = SaleItem(
        product_id=prod_id,
        batch_id=batch_id,
        qty=10.0,
        unit_id=5,
        sale_rate=1350.0,
        mrp=1350.0,
        taxable_amount=12857.14,
        cgst_rate=2.5,
        cgst_amount=321.43,
        sgst_rate=2.5,
        sgst_amount=321.43,
        total_amount=13500.0,
    )
    sale = Sale(
        invoice_no=inv_no,
        sale_date="2026-09-12",
        customer_id=cust_id,
        payment_mode="CASH",
        total_taxable=12857.14,
        total_cgst=321.43,
        total_sgst=321.43,
        net_amount=13500.0,
        paid_amount=13500.0,
        due_amount=0.0,
        items=[sale_item],
    )
    sale_id = sales_repo.create_sale(sale)
    assert sale_id > 0

    fetched_sale = sales_repo.get_sale_by_id(sale_id)
    assert fetched_sale.invoice_no == "INV-00001"
    assert fetched_sale.customer_name == "Suresh Shinde"
    assert len(fetched_sale.items) == 1
    assert fetched_sale.items[0].product_name == "DAP 50kg (IFFCO)"


def test_double_entry_accounting_voucher(test_env):
    """Test double-entry voucher creation, balance validation, and ledger statements."""
    accounting = test_env["accounting"]

    cash_ac = accounting.get_account_by_name("Cash in Hand")
    sales_ac = accounting.get_account_by_name("Sales Account")
    assert cash_ac is not None
    assert sales_ac is not None

    initial_cash_bal = cash_ac.current_balance
    initial_sales_bal = sales_ac.current_balance

    # Balanced Receipt Voucher: Debit Cash 5000, Credit Sales 5000
    vch_no = accounting.generate_next_voucher_no("RECEIPT")
    voucher = Voucher(
        voucher_no=vch_no,
        voucher_date="2026-09-12",
        voucher_type="RECEIPT",
        total_amount=5000.0,
        narration="Cash sales counter receipt",
        entries=[
            LedgerEntry(account_id=cash_ac.account_id, debit_amount=5000.0, credit_amount=0.0, particulars="By Cash"),
            LedgerEntry(account_id=sales_ac.account_id, debit_amount=0.0, credit_amount=5000.0, particulars="To Sales"),
        ],
    )
    vch_id = accounting.create_voucher(voucher)
    assert vch_id > 0

    # Verify Account Balances Updated Correctly
    updated_cash = accounting.get_account_by_id(cash_ac.account_id)
    updated_sales = accounting.get_account_by_id(sales_ac.account_id)
    assert updated_cash.current_balance == initial_cash_bal + 5000.0
    assert updated_sales.current_balance == initial_sales_bal + 5000.0

    # Unbalanced entry test - must fail
    with pytest.raises(ValueError):
        unbalanced = Voucher(
            voucher_no="ERR-001",
            voucher_date="2026-09-12",
            voucher_type="RECEIPT",
            total_amount=5000.0,
            entries=[
                LedgerEntry(account_id=cash_ac.account_id, debit_amount=5000.0, credit_amount=0.0),
                LedgerEntry(account_id=sales_ac.account_id, debit_amount=0.0, credit_amount=4000.0),
            ],
        )
        accounting.create_voucher(unbalanced)


def test_system_settings_and_audit(test_env):
    """Test company profile update and audit logging."""
    system = test_env["system"]

    # 1. Company Profile
    current_settings = system.get_company_settings()
    assert "Krishi" in current_settings.company_name

    current_settings.company_name = "Om Krishi Seva Kendra"
    current_settings.gstin = "27ABCDE1234F1Z5"
    system.update_company_settings(current_settings)

    saved_settings = system.get_company_settings()
    assert saved_settings.company_name == "Om Krishi Seva Kendra"
    assert saved_settings.gstin == "27ABCDE1234F1Z5"

    # 2. Audit Trail
    log_id = system.log_action(
        AuditLogEntry(
            user_id=1,
            action_type="INSERT",
            table_name="products",
            record_id=10,
            details="Added new product DAP",
        )
    )
    assert log_id > 0
