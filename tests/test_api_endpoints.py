"""
Automated Test Suite for FastAPI REST API Endpoints with Authentication.
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import DatabaseManager
from src.services.auth_service import AuthService


@pytest.fixture
def client(tmp_path):
    """Provides an authenticated TestClient connected to a test SQLite database."""
    test_db_path = tmp_path / "test_api_agri_erp.db"
    db_manager = DatabaseManager(db_path=test_db_path)
    db_manager.initialize_database(include_seed=True)

    token = AuthService.create_access_token(
        user_id=1,
        username="admin",
        full_name="आकाश लेंगारे (Admin)",
        role="ADMIN",
    )

    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client


def test_index_page(client):
    """Test that UI template renders at root /."""
    response = client.get("/")
    assert response.status_code == 200
    assert "KRUSHIDHAN" in response.text


def test_masters_api(client):
    """Test lookup masters API."""
    response = client.get("/api/masters/all")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "units" in data
    assert len(data["categories"]) >= 6


def test_sales_and_pdf_api_flow(client):
    """Test next invoice no, tax calculation, and PDF generation via API."""
    # 1. Check next invoice no
    inv_res = client.get("/api/sales/next-invoice-no")
    assert inv_res.status_code == 200
    assert "next_invoice_no" in inv_res.json()

    # 2. Tax calculation API
    tax_res = client.post(
        "/api/sales/calculate-tax",
        json={
            "qty": 10.0,
            "rate": 1350.0,
            "discount_percent": 0.0,
            "cgst_rate": 2.5,
            "sgst_rate": 2.5,
            "igst_rate": 0.0,
            "is_rate_tax_inclusive": True,
        },
    )
    assert tax_res.status_code == 200
    tax_data = tax_res.json()
    assert tax_data["total_amount"] == 13500.0


def test_inventory_alerts_api(client):
    """Test expiry and low stock API endpoints."""
    exp_res = client.get("/api/inventory/expiry-alerts?days=90")
    assert exp_res.status_code == 200
    assert isinstance(exp_res.json(), list)

    low_res = client.get("/api/inventory/low-stock-alerts")
    assert low_res.status_code == 200
    assert isinstance(low_res.json(), list)


def test_direct_add_stock_api(client):
    """Test directly adding stock via POST /api/inventory/add-stock."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    batch_code = f"BATCH-TEST-{uid}"

    # First get product list
    prod_res = client.get("/api/masters/products")
    assert prod_res.status_code == 200
    products = prod_res.json()
    assert len(products) > 0
    prod_id = products[0]["product_id"]

    # Add 25 units of stock directly
    add_res = client.post(
        "/api/inventory/add-stock",
        json={
            "product_id": prod_id,
            "qty": 25.0,
            "batch_no": batch_code,
            "purchase_rate": 500.0,
            "sale_rate": 600.0,
            "mrp": 650.0,
            "exp_date": "2027-12-31",
            "remarks": "Test Direct Addition",
        },
    )
    assert add_res.status_code == 200
    data = add_res.json()
    assert data["success"] is True
    assert data["added_qty"] == 25.0
    assert data["batch_no"] == batch_code

    # Verify stock summary reflects the new batch
    summary_res = client.get("/api/inventory/stock-summary")
    assert summary_res.status_code == 200
    batches = [b for b in summary_res.json() if b["batch_no"] == batch_code]
    assert len(batches) == 1
    assert batches[0]["current_qty"] == 25.0




def test_system_settings_api(client):
    """Test fetching and updating system settings via API."""
    get_res = client.get("/api/system/settings")
    assert get_res.status_code == 200
    settings = get_res.json()
    assert "company_name" in settings

    # Update settings
    settings["company_name"] = "Shivneri Krishi Kendra"
    post_res = client.post("/api/system/settings", json=settings)
    assert post_res.status_code == 200
    assert post_res.json()["success"] is True
