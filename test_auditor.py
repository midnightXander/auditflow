"""
Test script for the Website Auditor
Tests basic functionality before running the full API
"""

import asyncio
from auditor import WebsiteAuditor


async def test_basic_audit():
    """Test basic audit functionality"""
    
    # Test with a well-known website
    test_urls = [
        "https://example.com",
        # Add more URLs to test
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing audit for: {url}")
        print(f"{'='*60}\n")
        
        try:
            auditor = WebsiteAuditor(url)
            results = await auditor.run_full_audit()
            auditor.print_summary()
            
            # Basic assertions
            assert "url" in results
            assert "overall_score" in results
            assert 0 <= results["overall_score"] <= 100
            
            print("✓ Test passed!")
            
        except Exception as e:
            print(f"✗ Test failed: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(test_basic_audit())