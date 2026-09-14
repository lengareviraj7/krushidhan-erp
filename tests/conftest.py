"""
Pytest configuration and test database isolation fixture.
Ensures tests run against an isolated test database in /tmp and never dirty data/agri_erp.db.
"""
import os
from pathlib import Path
import pytest
from src.db.connection import DatabaseManager, get_db_manager

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    test_db_path = Path("/tmp/test_agri_erp.db")
    if test_db_path.exists():
        test_db_path.unlink()
    
    os.environ["DB_PATH"] = str(test_db_path)
    
    # Initialize fresh schema & seed for test run
    db = DatabaseManager(db_path=test_db_path)
    db.initialize_database(include_seed=True)
    
    yield
    
    # Clean up test database after test session
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass
