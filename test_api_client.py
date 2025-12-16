#!/usr/bin/env python3
"""
Test script to check API client search functionality.
"""

import os
import sys

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

def test_api_client_search():
    """Test API client search functionality."""
    
    try:
        from app.api_client import WorkbenchAPI
        
        # Initialize API client
        api_client = WorkbenchAPI("http://localhost:8000")
        
        logger.info("Testing API client search functionality...")
        
        # Test search with different sources
        sources = ["all", "github", "stackoverflow", "official_doc", "spark_docs"]
        
        for source in sources:
            logger.info(f"Testing search with source: {source}")
            success, search_results, error_msg = api_client.search_knowledge(
                query="python error",
                source=source,
                max_results=5
            )
            
            if success and search_results:
                total_results = search_results.get('total_results', 0)
                results = search_results.get('results', [])
                logger.info(f"  Success: {success}")
                logger.info(f"  Total results: {total_results}")
                logger.info(f"  Results count: {len(results)}")
                if results:
                    logger.info(f"  First result title: {results[0].get('title', 'No title')[:100]}...")
                    logger.info(f"  First result source: {results[0].get('source', 'Unknown')}")
            else:
                logger.error(f"  Failed: {error_msg or 'Unknown error'}")
                
    except Exception as e:
        logger.error(f"API client test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = test_api_client_search()
        if result:
            logger.info("API client search test completed successfully")
        else:
            logger.error("API client search test failed")
    except Exception as e:
        logger.error(f"Test execution failed: {e}")