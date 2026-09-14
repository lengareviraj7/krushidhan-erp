"""
API Package and Main Router Setup.
"""
from fastapi import APIRouter
from src.api.routes_accounting import router as accounting_router
from src.api.routes_gst import router as gst_router
from src.api.routes_inventory import router as inventory_router
from src.api.routes_masters import router as masters_router
from src.api.routes_purchase import router as purchase_router
from src.api.routes_sales import router as sales_router
from src.api.routes_system import router as system_router

api_router = APIRouter()
api_router.include_router(sales_router)
api_router.include_router(purchase_router)
api_router.include_router(inventory_router)
api_router.include_router(masters_router)
api_router.include_router(accounting_router)
api_router.include_router(gst_router)
api_router.include_router(system_router)

__all__ = ["api_router"]
