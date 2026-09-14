"""
Service Layer for Offline SQLite Database Backup, Integrity Checks, and Restore Operations.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.db.connection import DatabaseManager, get_db_manager
from src.models.system import BackupLogEntry
from src.repositories.system_repository import SystemRepository


class BackupService:
    """Business logic for local SQLite database backups, automated timestamping, and restoration."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()
        self.system_repo = SystemRepository(self.db)

    def create_backup(self, backup_dir: Optional[Path] = None, backup_type: str = "MANUAL") -> Path:
        """
        Creates a consistent, online snapshot backup of the SQLite database using VACUUM INTO.
        Records the backup metadata in backup_log.
        """
        if self.db.db_path == ":memory:":
            raise ValueError("Cannot backup an in-memory database to file!")

        if backup_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            backup_dir = base_dir / "backups"

        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"agri_erp_backup_{timestamp}.db"

        # Use SQLite VACUUM INTO for live, atomic online backup without blocking
        with self.db.get_connection() as conn:
            conn.execute(f"VACUUM INTO '{str(backup_file)}';")

        # Get backup file size
        size_bytes = backup_file.stat().st_size

        # Log backup record
        self.system_repo.record_backup(
            BackupLogEntry(
                file_path=str(backup_file),
                backup_type=backup_type,
                backup_size_bytes=size_bytes,
                status="SUCCESS",
            )
        )

        return backup_file

    def verify_database_integrity(self, db_file_path: Optional[Path] = None) -> bool:
        """Runs SQLite PRAGMA quick_check to verify database health."""
        target_path = db_file_path or self.db.db_path
        if target_path == ":memory:":
            return True

        conn = sqlite3.connect(str(target_path))
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA quick_check;")
            result = cursor.fetchone()
            return result is not None and result[0] == "ok"
        finally:
            conn.close()

    def restore_backup(self, backup_file_path: Path) -> bool:
        """Restores a backup database file after integrity validation."""
        if not backup_file_path.exists():
            raise FileNotFoundError(f"Backup file does not exist: {backup_file_path}")

        # Verify integrity of backup file first
        if not self.verify_database_integrity(backup_file_path):
            raise ValueError("The selected backup file is corrupted or not a valid SQLite database!")

        # Copy over the active database file
        shutil.copy2(str(backup_file_path), str(self.db.db_path))
        return True

    def get_backup_history(self) -> List[Dict[str, Any]]:
        """Fetch list of all past backups."""
        rows = self.db.fetch_all("SELECT * FROM backup_log ORDER BY created_at DESC;")
        return [dict(r) for r in rows]
