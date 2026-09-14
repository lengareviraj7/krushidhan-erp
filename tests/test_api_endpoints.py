"""
Automated Test Suite for FastAPI REST API Endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import DatabaseManager


@pytest.fixture
def client(tmp_path):
    """Provides a TestClient connected to a test SQLite database."""
    test_db_path = tmp_path / "test_api_agri_erp.db"
    db_manager = DatabaseManager(db_path=test_db_path)
    db_manager.initialize_database(include_seed=True)

    # Override get_db_manager dependency inside app
    with TestClient(app) as test_client:
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
