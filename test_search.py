#!/usr/bin/env python3
"""
Test script to diagnose search functionality issues.
"""

import os
import sys
import asyncio
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search_functionality():
    """Test search functionality to diagnose issues."""
    
    # Import required modules
    try:
        from backend.services.search_service import SearchService
        from backend.services.search_clients import StackOverflowClient, GitHubClient, OfficialDocsClient
        
        logger.info("Testing search functionality...")
        
        # Test StackOverflow client
        logger.info("Testing StackOverflow client...")
        so_client = StackOverflowClient()
        try:
            so_results = await so_client.search("python error", 3)
            logger.info(f"StackOverflow results: {len(so_results)}")
            if so_results:
                logger.info(f"First result title: {so_results[0].title[:100]}...")
        except Exception as e:
            logger.error(f"StackOverflow search failed: {e}")
        
        # Test GitHub client
        logger.info("Testing GitHub client...")
        gh_client = GitHubClient()
        try:
            gh_results = await gh_client.search("python error", 3)
            logger.info(f"GitHub results: {len(gh_results)}")
            if gh_results:
                logger.info(f"First result title: {gh_results[0].title[:100]}...")
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
        
        # Test Official Docs client
        logger.info("Testing Official Docs client...")
        docs_client = OfficialDocsClient()
        try:
            docs_results = await docs_client.search("python error", 3)
            logger.info(f"Official Docs results: {len(docs_results)}")
            if docs_results:
                logger.info(f"First result title: {docs_results[0].title[:100]}...")
                logger.info(f"First result source: {docs_results[0].source_type}")
        except Exception as e:
            logger.error(f"Official Docs search failed: {e}")
        
        # Test Search Service
        logger.info("Testing Search Service...")
        search_service = SearchService()
        
        # Test individual sources
        try:
            stackoverflow_results = await search_service.search_stackoverflow("python error", 2)
            logger.info(f"Search service - StackOverflow: {len(stackoverflow_results)} results")
            
            github_results = await search_service.search_github("python error", 2)
            logger.info(f"Search service - GitHub: {len(github_results)} results")
            
            docs_results = await search_service.search_official_docs("python error", 2)
            logger.info(f"Search service - Official Docs: {len(docs_results)} results")
            
            spark_results = await search_service.search_spark_docs("spark error", 2)
            logger.info(f"Search service - Spark Docs: {len(spark_results)} results")
            
            # Test all sources
            all_results = await search_service.smart_search("python error", "all", 5)
            logger.info(f"Search service - All sources: {all_results.get('total_results', 0)} results")
            
        except Exception as e:
            logger.error(f"Search service test failed: {e}")
            
    except Exception as e:
        logger.error(f"Failed to import search modules: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Run the test
    try:
        result = asyncio.run(test_search_functionality())
        if result:
            logger.info("Search functionality test completed successfully")
        else:
            logger.error("Search functionality test failed")
    except Exception as e:
        logger.error(f"Test execution failed: {e}")