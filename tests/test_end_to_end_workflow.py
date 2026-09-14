"""
Comprehensive End-to-End Workflow and Stress Test for Krushidhan Agri-Input Shop ERP.
Tests full lifecycle:
1. Product Registration & Cataloging
2. Inward Purchase & Direct Stock Inward (FEFO)
3. POS Counter Billing & Stock Deduction
4. Farmer Khata Credit & Recovery
5. Supplier Khata Settlement
6. Daily Expense & Cash Closing Reconciliation
7. Statutory Agriculture Registers
8. High-Concurreny Heavy Workload Stress Test (Zero Deadlocks/Zero Hangs)
"""
import pytest
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import get_db_manager
from src.services.auth_service import AuthService

@pytest.fixture(scope="module")
def client():
    db = get_db_manager()
    db.initialize_database(include_seed=True)
    token = AuthService.create_access_token(
        user_id=1,
        username="admin",
        full_name="आकाश लेंगारे (Admin)",
        role="ADMIN"
    )
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c

def test_full_owner_business_lifecycle(client):
    # Step 1: Register a new high-demand Pesticide Product
    new_prod_payload = {
        "product_name": "Xivana Bayer 100ml",
        "category_id": 3, # Pesticide / Fungicide
        "manufacturer_id": 1,
        "hsn_code": "38089910",
        "unit_id": 1, # BTL
        "tax_group_id": 4, # 18% GST
        "default_purchase_rate": 656.0,
        "default_sale_rate": 700.0,
        "default_mrp": 700.0,
        "min_stock_alert": 10.0,
        "is_active": 1
    }
    prod_resp = client.post("/api/masters/products", json=new_prod_payload)
    assert prod_resp.status_code == 200
    prod_data = prod_resp.json()
    prod_id = prod_data["product_id"]
    assert prod_id > 0

    # Step 2: Add Direct Stock to Inventory for this Product
    stock_payload = {
        "product_id": prod_id,
        "qty": 50.0,
        "batch_no": "XIV-2026-B1",
        "purchase_rate": 656.0,
        "sale_rate": 700.0,
        "mrp": 700.0,
        "mfg_date": "2026-01-10",
        "exp_date": "2028-01-10",
        "remarks": "Initial Season Stock Intake"
    }
    stock_resp = client.post("/api/inventory/add-stock", json=stock_payload)
    assert stock_resp.status_code == 200
    stock_data = stock_resp.json()
    assert stock_data["success"] is True
    batch_id = stock_data["batch_id"]
    assert batch_id > 0

    # Verify inventory shows the stock batch
    inv_resp = client.get(f"/api/inventory/batches/{prod_id}")
    assert inv_resp.status_code == 200
    batches = inv_resp.json()
    assert any(b["batch_no"] == "XIV-2026-B1" and b["current_qty"] == 50.0 for b in batches)

    # Step 3: Register a Farmer Customer
    farmer_payload = {
        "customer_name": "हनुमंत रामचंद्र माने",
        "mobile": "9850112233",
        "village": "वाळवा",
        "taluka": "वाळवा",
        "district": "सांगली",
        "aadhar_no": "889900112233",
        "credit_limit": 50000.0,
        "opening_balance": 0.0
    }
    farmer_resp = client.post("/api/masters/customers", json=farmer_payload)
    assert farmer_resp.status_code == 200
    farmer_id = farmer_resp.json()["customer_id"]

    # Step 4: Perform POS Counter Sale on Partial Credit
    next_inv_resp = client.get("/api/sales/next-invoice-no")
    inv_no = next_inv_resp.json().get("next_invoice_no", "INV-2026-999")

    sale_payload = {
        "invoice_no": inv_no,
        "sale_date": date.today().isoformat(),
        "customer_id": farmer_id,
        "payment_mode": "CREDIT",
        "total_taxable": 2966.10,
        "total_cgst": 266.95,
        "total_sgst": 266.95,
        "total_igst": 0.0,
        "net_amount": 3500.0,
        "paid_amount": 1000.0,
        "due_amount": 2500.0,
        "items": [
            {
                "product_id": prod_id,
                "batch_id": batch_id,
                "qty": 5.0,
                "sale_rate": 700.0,
                "mrp": 700.0,
                "discount_percent": 0.0,
                "taxable_amount": 2966.10,
                "cgst_rate": 9.0,
                "cgst_amount": 266.95,
                "sgst_rate": 9.0,
                "sgst_amount": 266.95,
                "igst_rate": 0.0,
                "igst_amount": 0.0,
                "total_amount": 3500.0
            }
        ]
    }
    sale_resp = client.post("/api/sales/create", json=sale_payload)
    if sale_resp.status_code != 200:
        print("SALE ERROR:", sale_resp.json())
    assert sale_resp.status_code == 200
    sale_data = sale_resp.json()
    assert sale_data["success"] is True

    # Verify stock reduced from 50 to 45
    inv_resp2 = client.get(f"/api/inventory/batches/{prod_id}")
    b_updated = next(b for b in inv_resp2.json() if b["batch_id"] == batch_id)
    assert b_updated["current_qty"] == 45.0

    # Verify Farmer Khata reflects 2500 balance due
    stmt_resp = client.get(f"/api/masters/farmers/{farmer_id}/statement")
    assert stmt_resp.status_code == 200
    f_stmt = stmt_resp.json()
    assert f_stmt["customer"]["current_balance"] == 2500.0

    # Step 5: Farmer Pays ₹2000 Credit Recovery
    receipt_payload = {
        "customer_id": farmer_id,
        "receipt_date": date.today().isoformat(),
        "amount": 2000.0,
        "payment_mode": "CASH",
        "narration": "Farmer partial credit recovery"
    }
    rec_resp = client.post("/api/accounting/customer-receipt", json=receipt_payload)
    assert rec_resp.status_code == 200

    # Verify new farmer balance is ₹500
    stmt_resp2 = client.get(f"/api/masters/farmers/{farmer_id}/statement")
    assert stmt_resp2.json()["customer"]["current_balance"] == 500.0

    # Step 6: Record Shop Operational Expense (हमाली)
    exp_payload = {
        "category_id": 3, # Staff & Wages / हमाली
        "amount": 250.0,
        "payment_mode": "CASH",
        "description": "अनलोडिंग हमाली"
    }
    exp_resp = client.post("/api/accounting/expenses", json=exp_payload)
    assert exp_resp.status_code == 200

    # Step 7: Evening Cash Drawer Closing Reconciliation
    today_str = date.today().isoformat()
    cash_resp = client.get(f"/api/accounting/cash-closing-summary?target_date={today_str}")
    assert cash_resp.status_code == 200
    c_data = cash_resp.json()
    assert c_data["farmer_cash_receipts"] >= 2000.0
    assert c_data["cash_expenses"] >= 250.0

    # Step 8: Verify Statutory Pesticide Register has this sale
    pest_reg_resp = client.get("/api/statutory/pesticide-register")
    assert pest_reg_resp.status_code == 200
    p_records = pest_reg_resp.json()
    assert any(r["pesticide_name"] == "Xivana Bayer 100ml" for r in p_records)

def test_heavy_workload_stress_and_concurrency(client):
    """Verify that multiple concurrent operations execute cleanly with zero database lockups or hangs."""
    def create_quick_product(i):
        payload = {
            "product_name": f"Stress Test Product {i}",
            "category_id": 1,
            "manufacturer_id": 1,
            "hsn_code": "31052000",
            "unit_id": 2,
            "tax_group_id": 2,
            "default_purchase_rate": 100.0 + i,
            "default_sale_rate": 120.0 + i,
            "default_mrp": 120.0 + i,
            "min_stock_alert": 5.0,
            "is_active": 1
        }
        res = client.post("/api/masters/products", json=payload)
        return res.status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(create_quick_product, i) for i in range(25)]
        results = [f.result() for f in futures]

    assert all(code == 200 for code in results)
