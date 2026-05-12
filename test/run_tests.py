#!/usr/bin/env python3
"""
Test runner for VinceZcrikl-skills.

Usage:
  python test/run_tests.py              # all tests
  python test/run_tests.py -v           # verbose
  python test/run_tests.py everything   # filter by skill name
  python test/run_tests.py patent       # filter by skill name
"""

import sys
import unittest
import pathlib

TEST_DIR = pathlib.Path(__file__).resolve().parent


def main():
    filter_term = None
    verbosity   = 1

    for arg in sys.argv[1:]:
        if arg == "-v":
            verbosity = 2
        elif not arg.startswith("-"):
            filter_term = arg.lower()

    loader  = unittest.TestLoader()
    pattern = f"test_*{filter_term}*.py" if filter_term else "test_*.py"
    suite   = loader.discover(str(TEST_DIR), pattern=pattern)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
