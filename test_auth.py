#!/usr/bin/env python3
"""
Test script to verify authentication works in both development and production modes.
"""

import os
import requests
import time

def test_authentication():
    """Test authentication in different environments."""
    
    # Test backend URL
    backend_url = "http://localhost:8000"
    
    print("Testing authentication modes...\n")
    
    # Test 1: Development mode without API key
    print("Test 1: Development mode without API key")
    os.environ["ENVIRONMENT"] = "development"
    
    try:
        response = requests.get(f"{backend_url}/health")
        print(f"  Status Code: {response.status_code}")
        if response.status_code == 200:
            print("  ✓ Development mode working - no API key required")
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 2: Development mode with API key
    print("\nTest 2: Development mode with API key")
    try:
        response = requests.get(
            f"{backend_url}/health",
            headers={"X-API-Key": "dev-key-12345"}
        )
        print(f"  Status Code: {response.status_code}")
        if response.status_code == 200:
            print("  ✓ Development mode working - with API key")
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 3: Production mode without API key (should fail)
    print("\nTest 3: Production mode without API key (should fail)")
    os.environ["ENVIRONMENT"] = "production"
    
    try:
        response = requests.get(f"{backend_url}/health")
        print(f"  Status Code: {response.status_code}")
        if response.status_code == 401:
            print("  ✓ Production mode correctly rejects requests without API key")
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 4: Production mode with invalid API key (should fail)
    print("\nTest 4: Production mode with invalid API key (should fail)")
    try:
        response = requests.get(
            f"{backend_url}/health",
            headers={"X-API-Key": "invalid-key"}
        )
        print(f"  Status Code: {response.status_code}")
        if response.status_code == 401:
            print("  ✓ Production mode correctly rejects invalid API key")
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print("\nAuthentication tests completed!")

if __name__ == "__main__":
    test_authentication()