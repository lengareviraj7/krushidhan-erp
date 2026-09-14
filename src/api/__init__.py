"""
API Package and Main Router Setup with Mandatory Session Authentication.
"""
from fastapi import APIRouter, Depends
from src.api.auth_middleware import get_current_user
from src.api.routes_accounting import router as accounting_router
from src.api.routes_auth import router as auth_router
from src.api.routes_gst import router as gst_router
from src.api.routes_inventory import router as inventory_router
from src.api.routes_masters import router as masters_router
from src.api.routes_purchase import router as purchase_router
from src.api.routes_sales import router as sales_router
from src.api.routes_statutory import router as statutory_router
from src.api.routes_system import router as system_router

api_router = APIRouter()

# 1. Authentication Router (Public login + token-verified endpoints)
api_router.include_router(auth_router)

# 2. Protected Business Operations (Requires valid Krushidhan User Session)
api_router.include_router(sales_router, dependencies=[Depends(get_current_user)])
api_router.include_router(purchase_router, dependencies=[Depends(get_current_user)])
api_router.include_router(inventory_router, dependencies=[Depends(get_current_user)])
api_router.include_router(masters_router, dependencies=[Depends(get_current_user)])
api_router.include_router(accounting_router, dependencies=[Depends(get_current_user)])
api_router.include_router(gst_router, dependencies=[Depends(get_current_user)])
api_router.include_router(statutory_router, dependencies=[Depends(get_current_user)])
api_router.include_router(system_router, dependencies=[Depends(get_current_user)])


__all__ = ["api_router"]
