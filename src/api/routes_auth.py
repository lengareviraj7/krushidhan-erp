"""
Authentication API Endpoints for Krushidhan ERP.
Handles Login, Session verification, Password Changes, and User Management.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.auth_middleware import get_current_user, require_admin_user
from src.db.connection import get_db_manager
from src.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication & Security"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "OPERATOR"


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


@router.post("/login")
def login(payload: LoginRequest):
    """Authenticate User ID & Password and return secure JWT token."""
    svc = AuthService(get_db_manager())
    user = svc.authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="चुकीचा युझर आयडी किंवा पासवर्ड (Invalid User ID or Password)",
        )

    token = svc.create_access_token(
        user_id=user.user_id or 1,
        username=user.username,
        full_name=user.full_name or user.username,
        role=user.role or "OPERATOR",
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
        },
        "shop": {
            "name": "श्री कृषीधन कृषी सेवा केंद्र",
            "owner": "आकाश लेंगारे",
            "contact": "9503673620",
        },
    }


@router.get("/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Return active authenticated user profile."""
    return {"authenticated": True, "user": user}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Change logged-in user's password."""
    svc = AuthService(get_db_manager())
    user_id = int(current_user["user_id"])
    success = svc.change_password(user_id, payload.old_password, payload.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="सध्याचा पासवर्ड चुकीचा आहे (Current password is incorrect)",
        )
    return {"success": True, "message": "पासवर्ड यशस्वीरीत्या बदलला आहे (Password updated successfully)"}


@router.get("/users")
def list_system_users(admin: Dict[str, Any] = Depends(require_admin_user)):
    """Admin Only: List all registered operators and administrators."""
    svc = AuthService(get_db_manager())
    users = svc.list_users()
    return [
        {
            "user_id": u.user_id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": bool(u.is_active),
            "created_at": str(u.created_at or ""),
        }
        for u in users
    ]


@router.post("/users")
def create_system_user(
    payload: CreateUserRequest,
    admin: Dict[str, Any] = Depends(require_admin_user),
):
    """Admin Only: Create new billing operator or sub-admin."""
    svc = AuthService(get_db_manager())
    try:
        new_id = svc.register_user(
            username=payload.username,
            plain_password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
        )
        return {"success": True, "user_id": new_id, "message": f"User '{payload.username}' created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: UpdateUserStatusRequest,
    admin: Dict[str, Any] = Depends(require_admin_user),
):
    """Admin Only: Enable or Disable operator account."""
    if user_id == int(admin.get("user_id", 0)):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account.")
    svc = AuthService(get_db_manager())
    svc.set_user_active_status(user_id, payload.is_active)
    status_text = "सक्रिय (Active)" if payload.is_active else "निष्क्रिय (Disabled)"
    return {"success": True, "message": f"User status updated to {status_text}"}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    admin: Dict[str, Any] = Depends(require_admin_user),
):
    """Admin Only: Reset password for an operator."""
    svc = AuthService(get_db_manager())
    success = svc.reset_password_by_admin(user_id, payload.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": "Password reset successfully"}
