#!/usr/bin/env python3
"""
1-Click Application Launcher for Offline Agri-Input Shop ERP.
Usage: python run.py
"""
import os
import sys
import threading
import time
import webbrowser
import uvicorn
from src.db.connection import get_db_manager


def open_browser(url: str = "http://127.0.0.1:8008"):
    """Wait for server to start, then open the browser window."""
    time.sleep(1.2)
    print(f"🚀 Opening Agri-Shop ERP at {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not auto-open browser: {e}")


def main():
    print("=" * 60)
    print("🌾 KRISHI AGRI-INPUT SHOP ERP (100% Offline)")
    print("=" * 60)

    # Initialize local SQLite database
    print("⚙️ Initializing local database...")
    db = get_db_manager()
    db.initialize_database(include_seed=True)
    print("✓ Database ready at: data/agri_erp.db")

    # Start browser opener in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start FastAPI server
    print("🚀 Starting local ERP server on http://127.0.0.1:8008 (Press Ctrl+C to quit)...")
    uvicorn.run("src.app:app", host="127.0.0.1", port=8008, log_level="info")


if __name__ == "__main__":
    main()
