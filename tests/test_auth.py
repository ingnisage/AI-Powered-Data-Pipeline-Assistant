#!/usr/bin/env python3
"""
Authentication tests for the AI-Powered Data Pipeline Assistant.
This file contains tests for the authentication system in both development and production modes.
"""

import os
import sys
import unittest
import requests

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

def run_auth_tests():
    """Run authentication tests."""
    print("Running Authentication Tests")
    print("=" * 30)
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Create and run test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(AuthenticationTestCase)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_auth_tests()
    sys.exit(0 if success else 1)