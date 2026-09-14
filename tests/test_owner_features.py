import pytest
from datetime import date
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import get_db_manager
from src.services.auth_service import AuthService
from src.services.inventory_service import InventoryService
from src.services.accounting_service import AccountingService
from src.services.statutory_service import StatutoryService

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

def test_supplier_khata_endpoints(client):
    # 1. Fetch suppliers with balances or create one
    resp = client.get("/api/accounting/suppliers")
    assert resp.status_code == 200
    suppliers = resp.json()
    assert isinstance(suppliers, list)
    if not suppliers:
        s_res = client.post("/api/masters/suppliers", json={
            "supplier_name": "महालक्ष्मी ॲग्रो एजन्सी",
            "contact_person": "सचिन पाटील",
            "mobile": "9876543210",
            "city": "सांगली"
        })
        assert s_res.status_code == 200
        resp = client.get("/api/accounting/suppliers")
        suppliers = resp.json()

    assert len(suppliers) > 0
    supplier = suppliers[0]
    assert "supplier_id" in supplier
    assert "supplier_name" in supplier
    assert "outstanding_payable" in supplier

    # 2. Record supplier payment
    pay_payload = {
        "supplier_id": supplier["supplier_id"],
        "amount": 500.0,
        "payment_mode": "UPI",
        "reference_no": "UPI-TEST-1234",
        "notes": "Testing owner payment flow"
    }
    pay_resp = client.post("/api/accounting/supplier-payment", json=pay_payload)
    if pay_resp.status_code != 200:
        print("PAY RESP ERROR:", pay_resp.json())
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["success"] is True
    assert "voucher_id" in pay_data

    # 3. Fetch supplier statement
    stmt_resp = client.get(f"/api/accounting/suppliers/{supplier['supplier_id']}/statement")
    assert stmt_resp.status_code == 200
    stmt = stmt_resp.json()
    assert "supplier" in stmt
    assert "ledger" in stmt
    assert stmt["supplier"]["supplier_id"] == supplier["supplier_id"]

def test_daily_expense_and_cash_closing(client):
    # 1. Fetch expense categories
    cat_resp = client.get("/api/accounting/expense-categories")
    assert cat_resp.status_code == 200
    cats = cat_resp.json()
    assert isinstance(cats, list)
    assert any("Shop Rent" in c["category_name"] for c in cats)

    # 2. Add an expense
    exp_payload = {
        "category_id": cats[0]["category_id"],
        "amount": 120.0,
        "payment_mode": "CASH",
        "description": "शेतकरी चहा नाष्टा",
        "paid_to": "आनंद टी"
    }
    exp_resp = client.post("/api/accounting/expenses", json=exp_payload)
    if exp_resp.status_code != 200:
        print("EXP RESP ERROR:", exp_resp.json())
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["success"] is True
    assert "expense_id" in exp_data

    # 3. Cash closing summary
    today_str = date.today().isoformat()
    cash_resp = client.get(f"/api/accounting/cash-closing-summary?target_date={today_str}")
    assert cash_resp.status_code == 200
    cash_data = cash_resp.json()
    assert "total_cash_inflow" in cash_data
    assert "total_cash_outflow" in cash_data
    assert "expected_cash_in_hand" in cash_data
    assert cash_data["total_cash_outflow"] >= 120.0

def test_statutory_registers_endpoints(client):
    # Test Fertilizer Register
    f_resp = client.get("/api/statutory/fertilizer-register")
    assert f_resp.status_code == 200
    f_data = f_resp.json()
    assert isinstance(f_data, list)

    # Test Pesticide Register
    p_resp = client.get("/api/statutory/pesticide-register")
    assert p_resp.status_code == 200
    p_data = p_resp.json()
    assert isinstance(p_data, list)

    # Test Seed Register
    s_resp = client.get("/api/statutory/seed-register")
    assert s_resp.status_code == 200
    s_data = s_resp.json()
    assert isinstance(s_data, list)
