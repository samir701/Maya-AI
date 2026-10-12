#!/usr/bin/env python3
"""Run complete ZETTA Validation (Module Imports + Health Check + Test Suite)."""

import importlib
import sys
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scripts.development.check_imports import main as check_imports_main
from core.zetta.health import check_health


def print_env_info():
    print("==================================================")
    print("ENVIRONMENT INTERPRETER & PACKAGE LOCATIONS")
    print("==================================================")
    print(f"Python interpreter: {sys.executable}")
    print(f"Python version:     {sys.version.split()[0]}")

    for pkg_name in ["pytest", "pydantic", "dotenv"]:
        try:
            mod = importlib.import_module(pkg_name)
            loc = getattr(mod, "__file__", "built-in")
            print(f"{pkg_name:<18} location: {loc}")
        except Exception as e:
            print(f"{pkg_name:<18} location: FAILED ({e})")
    print("==================================================")


def run_tests() -> bool:
    print("==================================================")
    print("RUNNING ZETTA TEST SUITE")
    print("==================================================")
    try:
        import pytest
        ret_code = pytest.main(["-v", str(root_dir / "tests")])
        return ret_code == 0
    except ImportError:
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=str(root_dir / "tests"), pattern="test_*.py")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        print("-" * 50)
        print(f"Collected Tests: {result.testsRun}")
        print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"Failed: {len(result.failures) + len(result.errors)}")
        print(f"Skipped: {len(result.skipped)}")
        print("-" * 50)
        return result.wasSuccessful()


def main():
    print_env_info()

    print("==================================================")
    print("STEP 1: IMPORT & MODULE RESOLUTION AUDIT")
    print("==================================================")
    try:
        check_imports_main()
    except SystemExit as e:
        if e.code != 0:
            print("Import audit failed!")
            sys.exit(1)

    print("==================================================")
    print("STEP 2: RUNNING ZETTA FOUNDATION & HEALTH CHECKS")
    print("==================================================")
    health = check_health()
    print(f"Health Status: {health.status}")
    for k, v in health.checks.items():
        print(f" - {k:<15}: {v['status']}")
    print("==================================================")

    print("==================================================")
    print("STEP 3: RUNNING ZETTA TEST SUITE")
    print("==================================================")
    tests_passed = run_tests()

    if health.status == "OK" and tests_passed:
        print("\nALL STABILITY AUDIT CHECKS & TESTS PASSED SUCCESSFULLY!\n")
    else:
        print("\nVALIDATION FAILED!\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
