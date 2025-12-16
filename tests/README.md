# Tests Directory

This directory contains all the test files for the AI-Powered Data Pipeline Assistant project.

## Test Files

- `test_auth.py` - Authentication system tests
- `test_suite.py` - Consolidated test suite with all test cases
- `run_tests.py` - Test runner script

## Running Tests

### Run Individual Test Files

```bash
# Run authentication tests
python tests/test_auth.py

# Run all tests
python tests/run_tests.py
```

### Run Tests with unittest

```bash
# Run all tests using unittest discovery
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_auth
```

## Test Environment

The tests expect the backend to be running at `http://localhost:8000`. You can override this by setting the `TEST_BACKEND_URL` environment variable:

```bash
export TEST_BACKEND_URL=http://your-backend-url:port
python tests/run_tests.py
```

## Test Categories

1. **Authentication Tests** - Verify authentication works in both development and production modes
2. **API Tests** - Test API endpoints for proper responses
3. **Core Functionality Tests** - Test that core modules can be imported and function properly

## Adding New Tests

To add new tests:
1. Add test methods to the appropriate TestCase class in `test_suite.py`
2. Or create a new test file following the naming convention `test_*.py`
3. Import and include the new tests in the `create_test_suite()` function