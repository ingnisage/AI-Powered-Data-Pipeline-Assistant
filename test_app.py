#!/usr/bin/env python3
"""
Test script to verify that the Streamlit application can be imported and initialized properly.
This helps identify import errors or initialization issues before deployment.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test importing the main app module
        import app.app
        print("✅ Main app module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import main app module: {e}")
        return False
    
    try:
        # Test importing backend modules
        from backend.services.config import config
        print("✅ Backend config imported successfully")
    except Exception as e:
        print(f"❌ Failed to import backend config: {e}")
        return False
    
    try:
        # Test importing API client
        from app.api_client import WorkbenchAPI
        print("✅ API client imported successfully")
    except Exception as e:
        print(f"❌ Failed to import API client: {e}")
        return False
    
    return True

def test_environment():
    """Test that required environment variables are set."""
    print("\nTesting environment variables...")
    
    required_vars = [
        "BACKEND_API_KEY",
        "OPENAI_API_KEY",
        "SUPABASE_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=== AI Workbench Application Test ===\n")
    
    import_success = test_imports()
    env_success = test_environment()
    
    print("\n=== Test Results ===")
    if import_success and env_success:
        print("🎉 All tests passed! The application should run properly.")
        return 0
    else:
        print("💥 Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())