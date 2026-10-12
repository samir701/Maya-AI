#!/usr/bin/env python3
"""Script to initialize SQLite database schema."""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from core.zetta.db import get_db_manager


def main():
    print("Initializing ZETTA Database...")
    db = get_db_manager()
    db.initialize_schema()
    print(f"Database successfully initialized at {db.db_path}")


if __name__ == "__main__":
    main()
