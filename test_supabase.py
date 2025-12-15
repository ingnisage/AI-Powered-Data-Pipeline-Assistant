#!/usr/bin/env python3
"""
Test script to verify Supabase connection
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test Supabase connection with current environment variables."""
    print("Testing Supabase connection...")
    
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_SERVICE_ROLE_KEY present: {supabase_service_role_key is not None}")
    print(f"SUPABASE_KEY present: {supabase_key is not None}")
    
    # Use service role key if available, otherwise fallback to SUPABASE_KEY
    key_to_use = supabase_service_role_key or supabase_key
    key_type = "SERVICE_ROLE_KEY" if supabase_service_role_key else "SUPABASE_KEY (fallback)"
    
    if key_to_use:
        print(f"Using {key_type} (first 10 chars): {key_to_use[:10]}...")
    
    if not supabase_url or not key_to_use:
        print("❌ Missing required environment variables")
        return False
    
    try:
        print("Creating Supabase client...")
        client = create_client(supabase_url, key_to_use)
        print("✅ Supabase client created successfully")
        
        print("Testing connection with a simple query...")
        response = client.table("tasks").select("id").limit(1).execute()
        print(f"✅ Connection test successful. Response: {response.data if response else 'None'}")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    if success:
        print("\n🎉 Supabase connection is working!")
    else:
        print("\n💥 Supabase connection failed. Please check your keys.")