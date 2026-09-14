"""
Base Repository providing generic database execution utilities.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from src.db.connection import DatabaseManager, get_db_manager


class BaseRepository:
    """Base data access object for SQLite queries."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()

    def row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        """Convert a sqlite3.Row to a plain dictionary."""
        if row is None:
            return None
        return dict(row)

    def rows_to_list(self, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """Convert a list of sqlite3.Row objects to a list of dicts."""
        return [dict(r) for r in rows]
