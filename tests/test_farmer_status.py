"""
Automated Test Suite for Farmer Status, Statement, and Credit Recovery.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import DatabaseManager, get_db_manager
from src.models import Customer, Product, Sale, SaleItem, StockBatch
from src.repositories import InventoryRepository, MasterDataRepository
from src.services import SalesService


@pytest.fixture
def client():
    db = get_db_manager()
    db.initialize_database(include_seed=True)

    with TestClient(app) as test_client:
        yield test_client, db


def test_farmer_status_and_ledger_endpoints(client):
    test_client, db = client
    master = MasterDataRepository(db)
    inventory = InventoryRepository(db)
    sales_svc = SalesService(db)

    uid = uuid.uuid4().hex[:6]

    # 1. Create 2 Farmers in different villages
    c1_id = master.create_customer(
        Customer(
            customer_name=f"Vitthal Jagtap {uid}",
            mobile="9822998877",
            village="Malegaon",
            opening_balance=0.0,
        )
    )
    c2_id = master.create_customer(
        Customer(
            customer_name=f"Ganesh More {uid}",
            mobile="9422112233",
            village="Baramati",
            opening_balance=500.0,
        )
    )

    # Create Product & Batch
    prod_id = master.create_product(
        Product(
            product_name=f"IFFCO 10:26:26 NPK {uid}",
            category_id=1,
            unit_id=5,
            tax_group_id=2,
            default_purchase_rate=1400.0,
            default_sale_rate=1470.0,
        )
    )
    b_id = inventory.upsert_batch(
        StockBatch(
            product_id=prod_id,
            batch_no=f"NPK-{uid}",
            purchase_rate=1400.0,
            sale_rate=1470.0,
            mrp=1470.0,
            current_qty=50.0,
        )
    )

    # Record Credit Sale for Farmer 1
    sale = Sale(
        invoice_no=f"INV-STAT-{uid}",
        sale_date="2026-09-12",
        customer_id=c1_id,
        payment_mode="CREDIT",
        total_taxable=2800.0,
        net_amount=2940.0,
        paid_amount=1000.0,
        due_amount=1940.0,
        items=[
            SaleItem(
                product_id=prod_id,
                batch_id=b_id,
                qty=2.0,
                sale_rate=1470.0,
                mrp=1470.0,
                taxable_amount=2800.0,
                total_amount=2940.0,
            )
        ],
    )
    sales_svc.process_sales_invoice(sale)

    # 2. Test /api/masters/farmers/status-list
    res = test_client.get("/api/masters/farmers/status-list")
    assert res.status_code == 200
    farmers = res.json()
    assert len(farmers) >= 2

    # Check Vitthal Jagtap
    v_farmer = next(f for f in farmers if f["customer_id"] == c1_id)
    assert v_farmer["customer_name"] == f"Vitthal Jagtap {uid}"
    assert v_farmer["village"] == "Malegaon"
    assert v_farmer["total_bills_count"] == 1
    assert v_farmer["total_purchases_amount"] == 2940.0
    assert v_farmer["current_balance"] == 1940.0

    # 3. Test Village Filter
    m_res = test_client.get("/api/masters/farmers/status-list?village=Malegaon")
    assert m_res.status_code == 200
    m_farmers = m_res.json()
    assert all("Malegaon" in f["village"] for f in m_farmers)

    # 4. Test Only Credit Filter
    credit_res = test_client.get("/api/masters/farmers/status-list?only_credit=true")
    assert credit_res.status_code == 200
    credit_farmers = credit_res.json()
    assert all(f["current_balance"] > 0 for f in credit_farmers)

    # 5. Test Statement & Goods Detail
    stmt_res = test_client.get(f"/api/masters/farmers/{c1_id}/statement")
    assert stmt_res.status_code == 200
    stmt = stmt_res.json()
    assert stmt["customer"]["customer_name"] == f"Vitthal Jagtap {uid}"
    assert len(stmt["invoices"]) == 1
    assert stmt["invoices"][0]["invoice_no"] == f"INV-STAT-{uid}"
    assert len(stmt["invoices"][0]["items"]) == 1
    assert stmt["invoices"][0]["items"][0]["product_name"] == f"IFFCO 10:26:26 NPK {uid}"
