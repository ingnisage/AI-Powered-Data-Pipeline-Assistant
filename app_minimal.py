#!/usr/bin/env python3
"""
Minimal version of the Streamlit app for debugging Render deployment issues.
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(page_title="AI Workbench - Minimal Test", layout="centered")
    
    st.title("🚀 AI Workbench - Minimal Test")
    
    # Show basic information
    st.header("Application Status")
    st.success("✅ Application is running!")
    
    st.header("Debug Information")
    
    # Show environment information
    st.subheader("Environment")
    st.write(f"Python Version: {os.sys.version}")
    st.write(f"Working Directory: {os.getcwd()}")
    
    # Show key environment variables (masked)
    st.subheader("Environment Variables")
    backend_key_set = "BACKEND_API_KEY" in os.environ
    openai_key_set = "OPENAI_API_KEY" in os.environ
    supabase_url_set = "SUPABASE_URL" in os.environ
    
    st.write(f"BACKEND_API_KEY set: {'✅' if backend_key_set else '❌'}")
    st.write(f"OPENAI_API_KEY set: {'✅' if openai_key_set else '❌'}")
    st.write(f"SUPABASE_URL set: {'✅' if supabase_url_set else '❌'}")
    
    # Show Render-specific info
    is_render = os.getenv('RENDER', '').lower() == 'true'
    st.write(f"Running on Render: {'✅' if is_render else '❌'}")
    
    if is_render:
        st.write(f"Service Name: {os.getenv('RENDER_SERVICE_NAME', 'Not set')}")
        st.write(f"Region: {os.getenv('RENDER_REGION', 'Not set')}")
        st.write(f"External URL: {os.getenv('RENDER_EXTERNAL_URL', 'Not set')}")
    
    # Simple test functionality
    st.header("Test Functionality")
    user_input = st.text_input("Enter a test message:")
    if user_input:
        st.write(f"You entered: {user_input}")
        st.info("✅ Streamlit components are working correctly!")

if __name__ == "__main__":
    main()