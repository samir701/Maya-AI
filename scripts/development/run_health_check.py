#!/usr/bin/env python3
"""Script to run ZETTA foundation health check."""

import json
import sys
from pathlib import Path

# Ensure root import path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from core.zetta.health import check_health


def main():
    print("Running ZETTA Health Check...")
    health = check_health()
    print(f"Status: {health.status}")
    print(json.dumps(health.checks, indent=2))
    if health.status != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()
