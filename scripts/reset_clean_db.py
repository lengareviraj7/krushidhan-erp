"""
Script to create a completely clean, production-ready Krushidhan ERP Database.
Removes all test mock records and initializes master lookups and Krushidhan profile.
"""
from pathlib import Path
from src.db.connection import DatabaseManager

def reset_clean_database():
    base_dir = Path(__file__).resolve().parent.parent
    db_file = base_dir / "data" / "agri_erp.db"
    
    if db_file.exists():
        db_file.unlink()
        print(f"Removed existing dirty database: {db_file}")

    db = DatabaseManager(db_path=db_file)
    db.initialize_database(include_seed=True)
    print("✓ Successfully initialized clean database with authentic master lookups!")

if __name__ == "__main__":
    reset_clean_database()
