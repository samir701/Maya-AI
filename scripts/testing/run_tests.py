#!/usr/bin/env python3
"""Script to run all ZETTA test suites deterministically."""

import sys
import unittest
from pathlib import Path

root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def main():
    print("Running ZETTA Test Suites...")
    try:
        import pytest
        ret_code = pytest.main(["-v", str(root_dir / "tests")])
        if ret_code != 0:
            print("Tests failed!")
            sys.exit(1)
        else:
            print("All discovered tests passed successfully!")
    except ImportError:
        loader = unittest.TestLoader()
        tests_dir = root_dir / "tests"
        suite = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        print("-" * 60)
        print(f"Tests Run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped)}")
        print("-" * 60)

        if not result.wasSuccessful():
            print("Tests failed!")
            sys.exit(1)
        else:
            print("All discovered tests passed successfully!")


if __name__ == "__main__":
    main()
