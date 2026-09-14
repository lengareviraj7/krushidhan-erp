"""
Demo Data Seeder: Populates realistic fertilizer, seed, and pesticide products, batches, and farmer customers.
"""
from src.db.connection import get_db_manager
from src.models import (
    Customer,
    Manufacturer,
    Product,
    StockBatch,
    Supplier,
)
from src.repositories import (
    InventoryRepository,
    MasterDataRepository,
)


def seed_demo_data():
    db = get_db_manager()
    db.initialize_database(include_seed=True)

    master = MasterDataRepository(db)
    inventory = InventoryRepository(db)

    # 1. Manufacturers / Companies
    mfg_iffco = master.create_manufacturer(
        Manufacturer(
            manufacturer_name="Indian Farmers Fertiliser Co-operative (IFFCO)",
            contact_person="K. S. Patil",
            mobile="9822012345",
            address="APMC Market Yard, Pune",
        )
    )
    mfg_bayer = master.create_manufacturer(
        Manufacturer(
            manufacturer_name="Bayer CropScience India",
            contact_person="Sunil Deshmukh",
            mobile="9890123411",
            address="Thane West, Maharashtra",
        )
    )
    mfg_syngenta = master.create_manufacturer(
        Manufacturer(
            manufacturer_name="Syngenta India Ltd",
            contact_person="Ramesh Kulkarni",
            mobile="9422003344",
            address="Baner Road, Pune",
        )
    )
    mfg_mahyco = master.create_manufacturer(
        Manufacturer(
            manufacturer_name="Maharashtra Hybrid Seeds Co. (Mahyco)",
            contact_person="Vikas Shinde",
            mobile="9823114455",
            address="Jalna, Maharashtra",
        )
    )

    # 2. Suppliers
    master.create_supplier(
        Supplier(
            supplier_name="IFFCO State Marketing Federation",
            contact_person="Regional Officer",
            mobile="9822119988",
            city="Pune",
            gstin="27AAACI1234A1Z1",
            opening_balance=0.0,
        )
    )
    master.create_supplier(
        Supplier(
            supplier_name="Krishi Udyog Distributors",
            contact_person="Mahesh Jadhav",
            mobile="9890998877",
            city="Baramati",
            gstin="27AABCK5566L1Z4",
            opening_balance=15000.0,
        )
    )

    # 3. Farmer Customers
    master.create_customer(
        Customer(
            customer_name="Suresh Baban Shinde",
            mobile="9422334455",
            village="Baramati",
            taluka="Baramati",
            district="Pune",
            opening_balance=0.0,
        )
    )
    master.create_customer(
        Customer(
            customer_name="Pandurang Kisan Ghadge",
            mobile="9822556677",
            village="Malegaon Bk",
            taluka="Baramati",
            district="Pune",
            opening_balance=1200.0,
        )
    )
    master.create_customer(
        Customer(
            customer_name="Someshwar Agro Farmers Producer Co.",
            mobile="9890112233",
            village="Nira",
            taluka="Purandar",
            district="Pune",
            gstin="27AAACS9988P1Z3",  # B2B customer
            opening_balance=0.0,
        )
    )

    # 4. Products & Initial Stock Batches (FEFO configured)
    # Product 1: Urea (Fertilizer - 5% GST)
    p1 = master.create_product(
        Product(
            product_name="IFFCO Neem Coated Urea (45 kg Bag)",
            category_id=1,
            manufacturer_id=mfg_iffco,
            hsn_code="31021000",
            unit_id=5,  # Bag
            tax_group_id=2,  # 5%
            default_purchase_rate=242.0,
            default_sale_rate=266.5,
            default_mrp=266.5,
            min_stock_alert=20.0,
        )
    )
    inventory.upsert_batch(
        StockBatch(
            product_id=p1,
            batch_no="UREA-MAY-26",
            mfg_date="2026-05-01",
            exp_date="2028-05-01",
            purchase_rate=242.0,
            sale_rate=266.5,
            mrp=266.5,
            current_qty=120.0,
        )
    )

    # Product 2: DAP 18:46:0 (Fertilizer - 5% GST)
    p2 = master.create_product(
        Product(
            product_name="IFFCO DAP 18:46:0 (50 kg Bag)",
            category_id=1,
            manufacturer_id=mfg_iffco,
            hsn_code="31053000",
            unit_id=5,  # Bag
            tax_group_id=2,  # 5%
            default_purchase_rate=1280.0,
            default_sale_rate=1350.0,
            default_mrp=1350.0,
            min_stock_alert=15.0,
        )
    )
    # Batch 1 (Expiring sooner - FEFO first)
    inventory.upsert_batch(
        StockBatch(
            product_id=p2,
            batch_no="DAP-BATCH-01",
            mfg_date="2026-01-10",
            exp_date="2026-11-30",
            purchase_rate=1280.0,
            sale_rate=1350.0,
            mrp=1350.0,
            current_qty=40.0,
        )
    )
    # Batch 2 (Expiring later)
    inventory.upsert_batch(
        StockBatch(
            product_id=p2,
            batch_no="DAP-BATCH-02",
            mfg_date="2026-06-01",
            exp_date="2028-06-01",
            purchase_rate=1280.0,
            sale_rate=1350.0,
            mrp=1350.0,
            current_qty=100.0,
        )
    )

    # Product 3: Mahyco Hybrid Cotton Seeds (Seeds - 0% Exempt GST)
    p3 = master.create_product(
        Product(
            product_name="Mahyco Hybrid Cotton BG-II (475 gm)",
            category_id=2,
            manufacturer_id=mfg_mahyco,
            hsn_code="12099990",
            unit_id=9,  # Packet
            tax_group_id=1,  # 0% Exempt
            default_purchase_rate=780.0,
            default_sale_rate=864.0,
            default_mrp=864.0,
            min_stock_alert=10.0,
        )
    )
    inventory.upsert_batch(
        StockBatch(
            product_id=p3,
            batch_no="MAHYCO-BG2-88",
            mfg_date="2026-04-01",
            exp_date="2027-03-31",
            purchase_rate=780.0,
            sale_rate=864.0,
            mrp=864.0,
            current_qty=65.0,
        )
    )

    # Product 4: Bayer Confidor Insecticide (Pesticide - 18% GST)
    p4 = master.create_product(
        Product(
            product_name="Bayer Confidor Insecticide (100 ml)",
            category_id=3,
            manufacturer_id=mfg_bayer,
            hsn_code="38089190",
            unit_id=8,  # Bottle
            tax_group_id=4,  # 18%
            default_purchase_rate=380.0,
            default_sale_rate=450.0,
            default_mrp=490.0,
            min_stock_alert=10.0,
        )
    )
    inventory.upsert_batch(
        StockBatch(
            product_id=p4,
            batch_no="CONF-2026-09",
            mfg_date="2026-03-01",
            exp_date="2028-02-28",
            purchase_rate=380.0,
            sale_rate=450.0,
            mrp=490.0,
            current_qty=35.0,
        )
    )

    # Product 5: Syngenta Ampligo Insecticide (Pesticide - 18% GST - Expiring in 45 days for alert demo)
    p5 = master.create_product(
        Product(
            product_name="Syngenta Ampligo (100 ml)",
            category_id=3,
            manufacturer_id=mfg_syngenta,
            hsn_code="38089190",
            unit_id=8,  # Bottle
            tax_group_id=4,  # 18%
            default_purchase_rate=760.0,
            default_sale_rate=880.0,
            default_mrp=940.0,
            min_stock_alert=5.0,
        )
    )
    inventory.upsert_batch(
        StockBatch(
            product_id=p5,
            batch_no="AMP-ALERT-EXP",
            mfg_date="2025-10-01",
            exp_date="2026-10-25",  # Expiring soon (< 45 days)
            purchase_rate=760.0,
            sale_rate=880.0,
            mrp=940.0,
            current_qty=8.0,
        )
    )

    print("✓ Successfully seeded realistic agri shop products, FEFO batches, suppliers, and farmers!")


if __name__ == "__main__":
    seed_demo_data()
