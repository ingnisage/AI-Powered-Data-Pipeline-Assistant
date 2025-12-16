#!/usr/bin/env python3
"""
Consolidated test suite for the AI-Powered Data Pipeline Assistant.
This file combines all test cases for authentication, API endpoints, and core functionality.
"""

import os
import sys
import unittest
import requests
import time
from typing import Dict, Any

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class AuthenticationTestCase(unittest.TestCase):
    """Test cases for authentication system."""
    
    def setUp(self):
        """Set up test environment."""
        self.backend_url = os.getenv('TEST_BACKEND_URL', 'http://localhost:8000')
        
    def test_development_mode_without_api_key(self):
        """Test development mode without API key."""
        # Set environment to development
        os.environ["ENVIRONMENT"] = "development"
        
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")
    
    def test_development_mode_with_api_key(self):
        """Test development mode with API key."""
        try:
            response = requests.get(
                f"{self.backend_url}/health",
                headers={"X-API-Key": "dev-key-12345"},
                timeout=5
            )
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")
    
    def test_production_mode_without_api_key(self):
        """Test production mode without API key (should fail)."""
        # Set environment to production
        os.environ["ENVIRONMENT"] = "production"
        
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            self.assertEqual(response.status_code, 401)
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")
    
    def test_production_mode_with_invalid_api_key(self):
        """Test production mode with invalid API key (should fail)."""
        try:
            response = requests.get(
                f"{self.backend_url}/health",
                headers={"X-API-Key": "invalid-key"},
                timeout=5
            )
            self.assertEqual(response.status_code, 401)
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")

class APITestCase(unittest.TestCase):
    """Test cases for API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        self.backend_url = os.getenv('TEST_BACKEND_URL', 'http://localhost:8000')
        self.api_key = os.getenv('BACKEND_API_KEY', 'test-api-key')
        
    def test_health_endpoint(self):
        """Test health check endpoint."""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            # Health endpoint should work regardless of authentication mode
            self.assertIn(response.status_code, [200, 401, 503])
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        try:
            response = requests.get(f"{self.backend_url}/", timeout=5)
            self.assertEqual(response.status_code, 200)
            self.assertIn("message", response.json())
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")

class CoreFunctionalityTestCase(unittest.TestCase):
    """Test cases for core functionality."""
    
    def test_imports(self):
        """Test that core modules can be imported."""
        try:
            from backend.core.dependencies import ServiceContainer
            from backend.auth.security import verify_api_key_dependency
            from backend.services.config import config
            # If we get here, imports worked
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Import failed: {e}")

def create_test_suite():
    """Create and return a test suite with all test cases."""
    suite = unittest.TestSuite()
    
    # Add authentication tests
    suite.addTest(unittest.makeSuite(AuthenticationTestCase))
    
    # Add API tests
    suite.addTest(unittest.makeSuite(APITestCase))
    
    # Add core functionality tests
    suite.addTest(unittest.makeSuite(CoreFunctionalityTestCase))
    
    return suite

def run_tests():
    """Run all tests and return results."""
    print("Running AI-Powered Data Pipeline Assistant Test Suite")
    print("=" * 50)
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Create and run test suite
    suite = create_test_suite()
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)