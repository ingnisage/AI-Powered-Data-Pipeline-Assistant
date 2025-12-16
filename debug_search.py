#!/usr/bin/env python3
"""
Debug script to trace search functionality issues.
"""

import os
import sys
import json

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_search_issues():
    """Debug search functionality issues."""
    
    try:
        # Test the backend search service directly
        from backend.services.search_service import SearchService
        
        logger.info("Testing backend search service directly...")
        search_service = SearchService()
        
        # Test each source individually
        test_cases = [
            ("stackoverflow", "python error"),
            ("github", "python error"), 
            ("official_doc", "python error"),
            ("spark_docs", "spark error"),
            ("all", "python error")
        ]
        
        for source, query in test_cases:
            logger.info(f"\n=== Testing source: {source} ===")
            try:
                results = search_service.smart_search.__wrapped__(search_service, query=query, source=source, max_results=3)
                # Since this is a sync method calling async, we need to run it properly
                import asyncio
                actual_results = asyncio.run(results)
                
                logger.info(f"Results count: {actual_results.get('total_results', 0)}")
                results_list = actual_results.get('results', [])
                for i, result in enumerate(results_list):
                    logger.info(f"  Result {i+1}: {result.get('title', 'No title')[:50]}... (source: {result.get('source', 'Unknown')})")
                    
            except Exception as e:
                logger.error(f"Error testing {source}: {e}")
                
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = debug_search_issues()
        if result:
            logger.info("Debug completed successfully")
        else:
            logger.error("Debug failed")
    except Exception as e:
        logger.error(f"Debug execution failed: {e}")