"""
Automated Test Suite for Krushidhan Profit & Loss (P&L) Session and Profitability Analytics.
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.db.connection import get_db_manager
from src.services.accounting_service import AccountingService
from src.services.auth_service import AuthService


@pytest.fixture
def client():
    token = AuthService.create_access_token(
        user_id=1,
        username="admin",
        full_name="आकाश लेंगारे (Admin)",
        role="ADMIN",
    )
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


def test_pnl_service_calculation():
    """Verify backend P&L calculations for Revenue, COGS, Gross Profit, and Net Profit."""
    db = get_db_manager()
    svc = AccountingService(db)

    # Test date range covering historical seed data or recent sales
    pnl = svc.get_profit_and_loss(from_date="2020-01-01", to_date="2030-12-31")

    assert "sales_revenue" in pnl
    assert "cogs" in pnl
    assert "gross_profit" in pnl
    assert "net_profit" in pnl
    assert "gross_margin_pct" in pnl
    assert "net_margin_pct" in pnl
    assert "category_breakdown" in pnl
    assert "closing_stock_value" in pnl

    # Verify math consistency
    assert round(pnl["gross_profit"], 2) == round(pnl["sales_revenue"] - pnl["cogs"], 2)
    assert round(pnl["net_profit"], 2) == round(pnl["gross_profit"] - pnl["total_expenses"], 2)


def test_product_profitability_service():
    """Verify product-by-product margin and profitability analytics."""
    db = get_db_manager()
    svc = AccountingService(db)

    products = svc.get_product_profitability(from_date="2020-01-01", to_date="2030-12-31")
    assert isinstance(products, list)

    for p in products:
        assert "product_name" in p
        assert "category_name" in p
        assert "qty_sold" in p
        assert "sales_revenue" in p
        assert "cogs" in p
        assert "gross_profit" in p
        assert "margin_pct" in p
        assert round(p["gross_profit"], 2) == round(p["sales_revenue"] - p["cogs"], 2)


def test_pnl_api_endpoints(client):
    """Verify HTTP API endpoints for P&L and product margins."""
    res = client.get("/api/accounting/profit-and-loss?from_date=2026-01-01&to_date=2026-12-31")
    assert res.status_code == 200
    data = res.json()
    assert "sales_revenue" in data
    assert "gross_profit" in data
    assert "net_profit" in data

    res_prod = client.get("/api/accounting/profit-and-loss/products?from_date=2026-01-01&to_date=2026-12-31")
    assert res_prod.status_code == 200
    prod_data = res_prod.json()
    assert isinstance(prod_data, list)
