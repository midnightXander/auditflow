#!/usr/bin/env python3
"""
Rank Tracker - Quick Start Examples

Run these examples to see the rank tracking engine in action.
"""

import asyncio
import json
from backend.apps.rank_tracker_sample import (
    RankTracker,
    SearchEngine,
    ProxyRotator,
    RankDatabase,
)


# ──────────────────────────────────────────────────────────────────────────────
# Example 1: Basic Keyword Tracking
# ──────────────────────────────────────────────────────────────────────────────

async def example_basic_tracking():
    """Simple example: track a few keywords"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Keyword Tracking")
    print("="*60)
    
    domain = "github.com"
    keywords = ["github", "git version control", "source code hosting"]
    
    async with RankTracker(
        domain=domain,
        keywords=keywords,
        search_engines=[SearchEngine.GOOGLE],
    ) as tracker:
        # Check each keyword
        for keyword in keywords:
            record, alert = await tracker.check_keyword(keyword, SearchEngine.GOOGLE)
            
            if record:
                if record.position:
                    print(f"✓ {keyword}: #{record.position}")
                else:
                    print(f"✗ {keyword}: Not ranked")
            else:
                print(f"⚠ {keyword}: Check failed")


# ──────────────────────────────────────────────────────────────────────────────
# Example 2: Batch Tracking with Progress
# ──────────────────────────────────────────────────────────────────────────────

async def example_batch_tracking():
    """Batch tracking multiple keywords with progress callback"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Batch Tracking with Progress")
    print("="*60)
    
    domain = "stackoverflow.com"
    keywords = [
        "python programming",
        "javascript tutorials",
        "web development",
        "coding questions",
    ]
    
    async def progress_callback(progress: int, status: str):
        print(f"[{progress:3d}%] {status}")
    
    async with RankTracker(
        domain=domain,
        keywords=keywords,
        search_engines=[SearchEngine.GOOGLE, SearchEngine.BING],
        min_delay=1.0,
        max_delay=3.0,
    ) as tracker:
        results = await tracker.check_all_keywords(progress_callback)
        
        print(f"\nResults Summary:")
        print(f"  Total checks: {results['summary']['total_checks']}")
        print(f"  Successful: {results['summary']['successful_checks']}")
        print(f"  Top 10: {results['summary']['top_10_count']}")
        print(f"  Top 50: {results['summary']['top_50_count']}")
        print(f"  Unranked: {results['summary']['unranked_count']}")


# ──────────────────────────────────────────────────────────────────────────────
# Example 3: Historical Analysis
# ──────────────────────────────────────────────────────────────────────────────

async def example_historical_analysis():
    """Analyze historical ranking data"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Historical Analysis")
    print("="*60)
    
    domain = "wikipedia.org"
    keyword = "encyclopedia"
    
    async with RankTracker(
        domain=domain,
        keywords=[keyword],
    ) as tracker:
        # Get historical chart data
        chart = tracker.get_ranking_chart(
            keyword=keyword,
            search_engine=SearchEngine.GOOGLE,
            days=30
        )
        
        print(f"\nRanking History for '{keyword}':")
        print(f"Data points: {len(chart['data'])}")
        
        if chart["data"]:
            print(f"\n{'Date':<12} {'Position':<10}")
            print("-" * 22)
            for entry in chart["data"][-5:]:  # Last 5 entries
                pos = entry["position"] if entry["position"] else "N/A"
                print(f"{entry['date']:<12} {str(pos):<10}")
        
        # Get trend analysis
        trend = tracker.get_trend_analysis(
            keyword=keyword,
            search_engine=SearchEngine.GOOGLE,
            days=30
        )
        
        print(f"\nTrend Analysis:")
        print(f"  Trend: {trend['trend']}")
        print(f"  Best: #{trend['best_position']}")
        print(f"  Average: #{trend['average_position']}")
        print(f"  Worst: #{trend['worst_position']}")
        print(f"  Data points: {trend['data_points']}")


# ──────────────────────────────────────────────────────────────────────────────
# Example 4: Alert Management
# ──────────────────────────────────────────────────────────────────────────────

async def example_alerts():
    """Check for rank change alerts"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Alert Management")
    print("="*60)
    
    domain = "python.org"
    
    db = RankDatabase("rank_tracker.db")
    alerts = db.get_alerts(domain, limit=10)
    
    if alerts:
        print(f"\nRecent Alerts for {domain}:")
        print(f"{'Keyword':<30} {'Position':<15} {'Level':<10}")
        print("-" * 55)
        
        for alert in alerts[:5]:
            change = f"#{alert.previous_position or '?'} → #{alert.current_position or '?'}"
            print(f"{alert.keyword:<30} {change:<15} {alert.alert_level:<10}")
    else:
        print(f"No alerts for {domain}")


# ──────────────────────────────────────────────────────────────────────────────
# Example 5: Multiple Search Engines
# ──────────────────────────────────────────────────────────────────────────────

async def example_multi_engine():
    """Track across multiple search engines"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Multiple Search Engines")
    print("="*60)
    
    domain = "linkedin.com"
    keywords = ["professional network", "job search"]
    
    async with RankTracker(
        domain=domain,
        keywords=keywords,
        search_engines=[
            SearchEngine.GOOGLE,
            SearchEngine.BING,
            SearchEngine.DUCKDUCKGO,
        ],
    ) as tracker:
        for keyword in keywords:
            print(f"\nKeyword: {keyword}")
            
            for engine in [SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.DUCKDUCKGO]:
                record, _ = await tracker.check_keyword(keyword, engine)
                
                if record:
                    pos = f"#{record.position}" if record.position else "Not ranked"
                    print(f"  {engine.value:12} → {pos}")


# ──────────────────────────────────────────────────────────────────────────────
# Example 6: With Proxy Rotation
# ──────────────────────────────────────────────────────────────────────────────

async def example_with_proxies():
    """Track with proxy rotation"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Proxy Rotation")
    print("="*60)
    
    domain = "amazon.com"
    keywords = ["online shopping", "e-commerce"]
    
    # Example proxies (replace with real proxies)
    proxies = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        # "http://user:pass@proxy3.com:3128",  # With auth
    ]
    
    proxy_rotator = ProxyRotator(proxies)
    
    print(f"Using {len(proxies)} proxies")
    print(f"Proxy rotation: {[p.split('//')[-1].split(':')[0] for p in proxies]}")
    
    async with RankTracker(
        domain=domain,
        keywords=keywords,
        proxies=proxy_rotator.proxies,
        min_delay=3.0,
        max_delay=6.0,
    ) as tracker:
        results = await tracker.check_all_keywords()
        
        print(f"\nChecks with proxies completed:")
        print(f"  Successful: {results['summary']['successful_checks']}/{results['summary']['total_checks']}")


# ──────────────────────────────────────────────────────────────────────────────
# Example 7: Database Queries
# ──────────────────────────────────────────────────────────────────────────────

def example_database_queries():
    """Query the rank database directly"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Database Queries")
    print("="*60)
    
    db = RankDatabase("rank_tracker.db")
    
    # Query latest record
    record = db.get_latest_record("python", "python.org", "google")
    if record:
        print(f"\nLatest record for 'python' on python.org:")
        print(f"  Position: #{record.position if record.position else 'N/A'}")
        print(f"  URL: {record.url or 'N/A'}")
        print(f"  Checked: {record.checked_at}")
    
    # Get history
    history = db.get_history("python", "python.org", "google", days=30)
    print(f"\n30-day history: {len(history)} records")
    
    if history:
        print(f"  First record: {history[0].timestamp}")
        print(f"  Last record: {history[-1].timestamp}")
        positions = [r.position for r in history if r.position]
        if positions:
            print(f"  Position range: #{min(positions)} - #{max(positions)}")


# ──────────────────────────────────────────────────────────────────────────────
# Example 8: Custom Rate Limiting
# ──────────────────────────────────────────────────────────────────────────────

async def example_rate_limiting():
    """Control request rate with custom delays"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Custom Rate Limiting")
    print("="*60)
    
    domain = "medium.com"
    keywords = ["writing", "journalism", "blogging"]
    
    print("Using aggressive rate limiting (1-2s delay):")
    
    async with RankTracker(
        domain=domain,
        keywords=keywords,
        min_delay=1.0,      # 1 second minimum
        max_delay=2.0,      # 2 second maximum
    ) as tracker:
        results = await tracker.check_all_keywords()
        
        print(f"Completed: {results['summary']['successful_checks']} checks")


# ──────────────────────────────────────────────────────────────────────────────
# Main Runner
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    """Run all examples"""
    print("\n╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  RANK TRACKER - QUICK START EXAMPLES".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Run examples (uncomment which ones you want)
        await example_basic_tracking()
        # await example_batch_tracking()
        # await example_historical_analysis()
        # await example_alerts()
        # await example_multi_engine()
        # await example_with_proxies()
        # example_database_queries()
        # await example_rate_limiting()
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
