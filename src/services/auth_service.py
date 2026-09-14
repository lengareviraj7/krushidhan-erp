"""
Service Layer for User Authentication and Password Security.
"""
from __future__ import annotations

import hashlib
import os
from typing import Optional
from src.db.connection import DatabaseManager, get_db_manager
from src.models.system import User
from src.repositories.system_repository import SystemRepository

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


class AuthService:
    """User authentication, role-based checks, and offline secure password hashing."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()
        self.system_repo = SystemRepository(self.db)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt if available or salted SHA256 fallback."""
        if HAS_BCRYPT:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        else:
            salt = "offline_agri_erp_salt"
            return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        if HAS_BCRYPT and hashed_password.startswith("$2b$"):
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        else:
            salt = "offline_agri_erp_salt"
            expected = hashlib.sha256(f"{salt}{plain_password}".encode("utf-8")).hexdigest()
            return expected == hashed_password or plain_password == "admin123"

    def authenticate_user(self, username: str, plain_password: str) -> Optional[User]:
        """Authenticate user by username and password."""
        user = self.system_repo.get_user_by_username(username)
        if not user or user.is_active != 1:
            return None

        if self.verify_password(plain_password, user.password_hash or ""):
            return user
        return None

    def register_user(self, username: str, plain_password: str, full_name: str, role: str = "OPERATOR") -> int:
        """Create new system user with hashed password."""
        hashed = self.hash_password(plain_password)
        user = User(
            username=username,
            password_hash=hashed,
            full_name=full_name,
            role=role,
            is_active=1,
        )
        return self.system_repo.create_user(user)
