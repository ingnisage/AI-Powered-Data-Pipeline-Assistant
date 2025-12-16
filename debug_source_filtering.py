#!/usr/bin/env python3
"""
Debug script to test source filtering in search functionality.
"""

import os
import sys
import json
import asyncio

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_source_filtering():
    """Debug source filtering issues."""
    
    try:
        # Test the backend search service directly
        from backend.services.search_service import SearchService
        
        logger.info("Testing backend search service with source filtering...")
        search_service = SearchService()
        
        # Test query
        query = "python error"
        max_results = 3
        
        # Test each source
        sources = ["github", "stackoverflow", "official_doc", "spark_docs", "all"]
        
        for source in sources:
            logger.info(f"\n=== Testing source: {source} ===")
            try:
                # Call the search service method directly
                results = await search_service.smart_search(
                    query=query,
                    source=source,
                    max_results=max_results
                )
                
                total_results = results.get('total_results', 0)
                results_list = results.get('results', [])
                
                logger.info(f"Total results: {total_results}")
                logger.info(f"Results list length: {len(results_list)}")
                
                for i, result in enumerate(results_list):
                    title = result.get('title', 'No title')[:50]
                    source_type = result.get('source', 'Unknown')
                    logger.info(f"  Result {i+1}: {title}... (source: {source_type})")
                    
            except Exception as e:
                logger.error(f"Error testing {source}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    return True

def test_api_endpoint():
    """Test the actual API endpoint to see how parameters are received."""
    try:
        import requests
        import os
        
        base_url = "http://localhost:8000"
        api_key = os.getenv("BACKEND_API_KEY")
        
        if not api_key:
            logger.error("BACKEND_API_KEY not found in environment")
            return False
            
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Test different sources
        sources = ["github", "stackoverflow", "official_doc", "spark_docs", "all"]
        query = "python error"
        
        for source in sources:
            logger.info(f"\n=== Testing API endpoint with source: {source} ===")
            
            payload = {
                "query": query,
                "source": source,
                "max_results": 3
            }
            
            try:
                response = requests.post(
                    f"{base_url}/search/",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                logger.info(f"Response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    total_results = data.get('total_results', 0)
                    results_list = data.get('results', [])
                    logger.info(f"Total results: {total_results}")
                    logger.info(f"Results list length: {len(results_list)}")
                    
                    for i, result in enumerate(results_list[:2]):  # Show first 2
                        title = result.get('title', 'No title')[:50]
                        source_type = result.get('source', 'Unknown')
                        logger.info(f"  Result {i+1}: {title}... (source: {source_type})")
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"API request failed for {source}: {e}")
                
    except Exception as e:
        logger.error(f"API endpoint test failed: {e}")
        return False
        
    return True

if __name__ == "__main__":
    logger.info("Starting source filtering debug...")
    
    # Test direct service call
    try:
        logger.info("\n" + "="*50)
        logger.info("TEST 1: Direct service call")
        logger.info("="*50)
        result1 = asyncio.run(debug_source_filtering())
        if result1:
            logger.info("Direct service call test completed")
        else:
            logger.error("Direct service call test failed")
    except Exception as e:
        logger.error(f"Direct service call test failed: {e}")
    
    # Test API endpoint
    try:
        logger.info("\n" + "="*50)
        logger.info("TEST 2: API endpoint call")
        logger.info("="*50)
        result2 = test_api_endpoint()
        if result2:
            logger.info("API endpoint test completed")
        else:
            logger.error("API endpoint test failed")
    except Exception as e:
        logger.error(f"API endpoint test failed: {e}")
    
    logger.info("\nDebug completed.")