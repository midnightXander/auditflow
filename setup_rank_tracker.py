#!/usr/bin/env python3
"""
Rank Tracker Setup & Configuration Script

Run this to set up the rank tracking system for your domain.
"""

import os
import json
import argparse
from pathlib import Path


def setup_config(domain: str, keywords_file: str = None, output_file: str = "rank_tracker_config.json"):
    """Create a configuration file"""
    
    keywords = []
    
    if keywords_file and os.path.exists(keywords_file):
        with open(keywords_file, 'r') as f:
            keywords = [line.strip() for line in f if line.strip()]
    else:
        print(f"\nEnter keywords to track (one per line, empty line to finish):")
        while True:
            kw = input("  > ").strip()
            if not kw:
                break
            keywords.append(kw)
    
    if not keywords:
        print("No keywords provided. Exiting.")
        return
    
    config = {
        "domain": domain,
        "keywords": keywords,
        "search_engines": ["google"],
        "min_delay": 2.0,
        "max_delay": 5.0,
        "proxies": [],
        "db_path": f"rank_tracker_{domain.replace('.', '_')}.db",
    }
    
    print("\nSearch engines available:")
    print("  1. google (default)")
    print("  2. bing")
    print("  3. duckduckgo")
    print("  4. all")
    
    choice = input("Select engines (comma-separated numbers or 'google'): ").strip().lower()
    
    engine_map = {
        "1": "google",
        "2": "bing",
        "3": "duckduckgo",
        "4": ["google", "bing", "duckduckgo"],
        "google": "google",
        "bing": "bing",
        "duckduckgo": "duckduckgo",
        "all": ["google", "bing", "duckduckgo"],
    }
    
    if choice in engine_map:
        engines = engine_map[choice]
        if isinstance(engines, list):
            config["search_engines"] = engines
        else:
            config["search_engines"] = [engines]
    
    print("\nRequest delays (to avoid blocking):")
    min_delay = input("  Min delay (seconds) [2.0]: ").strip()
    max_delay = input("  Max delay (seconds) [5.0]: ").strip()
    
    if min_delay:
        config["min_delay"] = float(min_delay)
    if max_delay:
        config["max_delay"] = float(max_delay)
    
    # Proxies (optional)
    print("\nSetup proxies (optional):")
    add_proxies = input("  Add proxies? (y/n) [n]: ").strip().lower()
    
    if add_proxies == "y":
        print("  Enter proxies (format: http://host:port or http://user:pass@host:port)")
        print("  Empty line to finish:")
        while True:
            proxy = input("  > ").strip()
            if not proxy:
                break
            config["proxies"].append(proxy)
    
    # Save config
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Configuration saved to {output_file}")
    print(f"\nRun tracking with:")
    print(f"  python rank_tracker.py check {domain} {' '.join(keywords[:3])} {'...' if len(keywords) > 3 else ''}")
    
    return config


def validate_install():
    """Validate dependencies"""
    print("\nValidating installation...")
    
    required = ["aiohttp", "bs4"]
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n✗ Missing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("\n✓ All dependencies installed!")
    return True


def generate_keywords_file(domain: str, output_file: str = None):
    """Generate a keywords file from user input"""
    if not output_file:
        output_file = f"keywords_{domain.replace('.', '_')}.txt"
    
    print(f"\nGenerating keywords file: {output_file}")
    print("Enter keywords (one per line, empty line to finish):")
    
    keywords = []
    while True:
        kw = input("  > ").strip()
        if not kw:
            break
        keywords.append(kw)
    
    if keywords:
        with open(output_file, 'w') as f:
            f.write('\n'.join(keywords))
        
        print(f"✓ Saved {len(keywords)} keywords to {output_file}")
        return output_file
    
    return None


def show_examples():
    """Show usage examples"""
    print("""
RANK TRACKER - QUICK START GUIDE
═══════════════════════════════════════════════════════════

1. CHECK KEYWORDS
   python rank_tracker.py check example.com "keyword1" "keyword2"

2. WITH PROXIES
   python rank_tracker.py check example.com "keyword" \\
     --proxies http://proxy1:8080 http://proxy2:8080

3. MULTIPLE ENGINES
   python rank_tracker.py check example.com "keyword" \\
     --engines google bing duckduckgo

4. VIEW HISTORY
   python rank_tracker.py history example.com "keyword" --days 30

5. VIEW ALERTS
   python rank_tracker.py alerts example.com

PYTHON API EXAMPLES
═══════════════════════════════════════════════════════════

    import asyncio
    from rank_tracker import RankTracker, SearchEngine
    
    async def main():
        async with RankTracker(
            domain="example.com",
            keywords=["keyword1", "keyword2"]
        ) as tracker:
            results = await tracker.check_all_keywords()
            print(results)
    
    asyncio.run(main())

FASTAPI INTEGRATION
═══════════════════════════════════════════════════════════

Add to api.py:
    from rank_tracker_api import router
    app.include_router(router)

Then access:
    POST   /api/rank-tracker/check
    GET    /api/rank-tracker/history/{domain}/{keyword}
    GET    /api/rank-tracker/trend/{domain}/{keyword}
    GET    /api/rank-tracker/alerts/{domain}

═══════════════════════════════════════════════════════════
For more info, see RANK_TRACKER_README.md
""")


def main():
    parser = argparse.ArgumentParser(
        description="Rank Tracker Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python setup_rank_tracker.py --domain example.com
  python setup_rank_tracker.py --keywords keywords.txt --output config.json
  python setup_rank_tracker.py --validate
  python setup_rank_tracker.py --examples
        """)
    
    parser.add_argument("--domain", help="Domain to track")
    parser.add_argument("--keywords", help="Keywords file (one per line)")
    parser.add_argument("--output", default="rank_tracker_config.json", help="Output config file")
    parser.add_argument("--validate", action="store_true", help="Validate dependencies")
    parser.add_argument("--examples", action="store_true", help="Show examples")
    parser.add_argument("--gen-keywords", metavar="DOMAIN", help="Generate keywords file")
    
    args = parser.parse_args()
    
    if args.validate:
        validate_install()
    elif args.examples:
        show_examples()
    elif args.gen_keywords:
        generate_keywords_file(args.gen_keywords)
    elif args.domain:
        if not validate_install():
            return
        
        config = setup_config(args.domain, args.keywords, args.output)
        
        if config:
            print("\n" + "="*60)
            print("CONFIGURATION SUMMARY")
            print("="*60)
            print(f"Domain: {config['domain']}")
            print(f"Keywords: {len(config['keywords'])} loaded")
            print(f"Search engines: {', '.join(config['search_engines'])}")
            print(f"Request delay: {config['min_delay']}-{config['max_delay']}s")
            print(f"Proxies: {len(config['proxies'])} configured")
            print(f"Database: {config['db_path']}")
            print("="*60)
    else:
        # Interactive mode
        print("""
╔════════════════════════════════════════════════════════╗
║                RANK TRACKER SETUP                      ║
╚════════════════════════════════════════════════════════╝
        """)
        
        print("Choose an option:")
        print("  1. Setup new tracking configuration")
        print("  2. Generate keywords file")
        print("  3. Validate installation")
        print("  4. Show examples")
        print("  5. Exit")
        
        choice = input("\nSelect (1-5): ").strip()
        
        if choice == "1":
            domain = input("Enter domain: ").strip()
            if domain:
                setup_config(domain)
        elif choice == "2":
            domain = input("Enter domain: ").strip()
            if domain:
                generate_keywords_file(domain)
        elif choice == "3":
            validate_install()
        elif choice == "4":
            show_examples()


if __name__ == "__main__":
    main()
