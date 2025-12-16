#!/usr/bin/env python3
"""
Test runner for the AI-Powered Data Pipeline Assistant.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def main():
    """Run all tests."""
    try:
        # Import and run the test suite
        from tests.test_suite import run_tests
        success = run_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())