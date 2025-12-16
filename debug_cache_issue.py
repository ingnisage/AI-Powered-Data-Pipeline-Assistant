#!/usr/bin/env python3
"""
Debug script to test cache issue with search functionality.
"""

import os
import sys
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

async def debug_cache_issue():
    """Debug cache issue with search functionality."""
    
    try:
        # Clear all caches first
        from backend.services.search_clients import clear_all_caches
        clear_all_caches()
        logger.info("Cleared all search caches")
        
        # Import the cached search functions
        from backend.services.search_clients import (
            search_stackoverflow_cached,
            search_github_cached,
            search_official_docs_cached,
            _convert_cached_tuple_to_documents
        )
        
        # Test query
        query = "python error"
        max_results = 3
        
        logger.info("Testing individual cached search functions...")
        
        # Test StackOverflow search
        logger.info("\n=== Testing StackOverflow cache ===")
        so_results_tuple = await search_stackoverflow_cached(query, max_results)
        so_results = _convert_cached_tuple_to_documents(so_results_tuple)
        logger.info(f"StackOverflow results count: {len(so_results)}")
        for i, result in enumerate(so_results):
            logger.info(f"  Result {i+1}: {result.title[:50]}... (source: {result.source_type})")
        
        # Test GitHub search
        logger.info("\n=== Testing GitHub cache ===")
        gh_results_tuple = await search_github_cached(query, max_results)
        gh_results = _convert_cached_tuple_to_documents(gh_results_tuple)
        logger.info(f"GitHub results count: {len(gh_results)}")
        for i, result in enumerate(gh_results):
            logger.info(f"  Result {i+1}: {result.title[:50]}... (source: {result.source_type})")
        
        # Test Official Docs search
        logger.info("\n=== Testing Official Docs cache ===")
        docs_results_tuple = await search_official_docs_cached(query, max_results)
        docs_results = _convert_cached_tuple_to_documents(docs_results_tuple)
        logger.info(f"Official Docs results count: {len(docs_results)}")
        for i, result in enumerate(docs_results):
            logger.info(f"  Result {i+1}: {result.title[:50]}... (source: {result.source_type})")
            
        # Test with different queries to see if cache is working correctly
        logger.info("\n=== Testing with different query ===")
        query2 = "spark exception"
        
        # Test StackOverflow search with different query
        logger.info("\n--- StackOverflow with 'spark exception' ---")
        so_results2_tuple = await search_stackoverflow_cached(query2, max_results)
        so_results2 = _convert_cached_tuple_to_documents(so_results2_tuple)
        logger.info(f"StackOverflow results count: {len(so_results2)}")
        for i, result in enumerate(so_results2):
            logger.info(f"  Result {i+1}: {result.title[:50]}... (source: {result.source_type})")
            
        # Now test the original query again to see if cache is working
        logger.info("\n--- StackOverflow with 'python error' (again) ---")
        so_results3_tuple = await search_stackoverflow_cached(query, max_results)
        so_results3 = _convert_cached_tuple_to_documents(so_results3_tuple)
        logger.info(f"StackOverflow results count: {len(so_results3)}")
        for i, result in enumerate(so_results3):
            logger.info(f"  Result {i+1}: {result.title[:50]}... (source: {result.source_type})")
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    logger.info("Starting cache issue debug...")
    
    try:
        result = asyncio.run(debug_cache_issue())
        if result:
            logger.info("Cache issue debug completed successfully")
        else:
            logger.error("Cache issue debug failed")
    except Exception as e:
        logger.error(f"Cache issue debug failed: {e}")
    
    logger.info("Debug completed.")