# Rank Tracker - Visual Guide & Commands

## 🎯 Start Here

```
┌─────────────────────────────────────────────────────┐
│ RANK TRACKER QUICK START                            │
└─────────────────────────────────────────────────────┘

STEP 1: Install (2 min)
  $ pip install aiohttp beautifulsoup4
  ✓ Done

STEP 2: Setup (5 min)
  $ python setup_rank_tracker.py
  ✓ Configuration saved

STEP 3: First Check (5 min)
  $ python rank_tracker.py check example.com "keyword1" "keyword2"
  ✓ Results shown

STEP 4: View History (2 min)
  $ python rank_tracker.py history example.com "keyword1"
  ✓ 30-day chart

STEP 5: Integration (20 min)
  Add to api.py: from rank_tracker_api import router
  ✓ API ready

TOTAL TIME: ~1 HOUR TO FULL INTEGRATION
```

## 🔧 All Commands

### Check Rankings

```bash
# Basic check
python rank_tracker.py check example.com "keyword1" "keyword2" "keyword3"

# With Bing
python rank_tracker.py check example.com "keyword1" --engines bing

# With all engines
python rank_tracker.py check example.com "keyword1" --engines google bing duckduckgo

# With proxies
python rank_tracker.py check example.com "keyword1" \
  --proxies http://proxy1:8080 http://proxy2:8080

# Custom database
python rank_tracker.py check example.com "keyword1" --db /path/to/db.db

# All options
python rank_tracker.py check example.com "keyword1" "keyword2" \
  --engines google bing \
  --proxies http://proxy1:8080 \
  --db rank_data.db
```

### View History

```bash
# Last 30 days (default)
python rank_tracker.py history example.com "keyword1"

# Last 90 days
python rank_tracker.py history example.com "keyword1" --days 90

# Different engine
python rank_tracker.py history example.com "keyword1" --engine bing

# Custom database
python rank_tracker.py history example.com "keyword1" --db /path/to/db.db
```

### View Alerts

```bash
# Last 20 alerts (default)
python rank_tracker.py alerts example.com

# More alerts
python rank_tracker.py alerts example.com --limit 100

# Custom database
python rank_tracker.py alerts example.com --db /path/to/db.db
```

### Setup & Utilities

```bash
# Interactive setup wizard
python setup_rank_tracker.py

# Setup specific domain
python setup_rank_tracker.py --domain example.com

# Generate keywords file
python setup_rank_tracker.py --gen-keywords example.com

# Validate dependencies
python setup_rank_tracker.py --validate

# Show examples
python setup_rank_tracker.py --examples
```

## 🐍 Python API Quick Commands

### Basic Usage

```python
import asyncio
from rank_tracker import RankTracker, SearchEngine

async def main():
    # Simple check
    async with RankTracker(
        domain="example.com",
        keywords=["keyword1", "keyword2"]
    ) as tracker:
        results = await tracker.check_all_keywords()
        print(results)

asyncio.run(main())
```

### With Progress

```python
async def progress(prog, status):
    print(f"[{prog}%] {status}")

async with RankTracker(...) as tracker:
    results = await tracker.check_all_keywords(
        progress_callback=progress
    )
```

### Get History

```python
async with RankTracker(...) as tracker:
    chart = tracker.get_ranking_chart(
        keyword="keyword1",
        search_engine=SearchEngine.GOOGLE,
        days=30
    )
    for entry in chart["data"]:
        print(f"{entry['date']}: #{entry['position']}")
```

### Get Trends

```python
async with RankTracker(...) as tracker:
    trend = tracker.get_trend_analysis(
        keyword="keyword1",
        search_engine=SearchEngine.GOOGLE,
        days=30
    )
    print(f"Trend: {trend['trend']}")
    print(f"Best: #{trend['best_position']}")
    print(f"Average: #{trend['average_position']}")
```

### Database Queries

```python
from rank_tracker import RankDatabase

db = RankDatabase()

# Get latest record
record = db.get_latest_record("keyword", "domain.com", "google")

# Get history
history = db.get_history("keyword", "domain.com", "google", days=30)

# Get alerts
alerts = db.get_alerts("domain.com", limit=50)
```

## 🌐 REST API Commands

### Check Keywords (Async)

```bash
curl -X POST http://localhost:8000/api/rank-tracker/check \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "keywords": ["keyword1", "keyword2"],
    "search_engines": ["google"],
    "min_delay": 2.0,
    "max_delay": 5.0
  }'

# Returns:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "processing"
# }
```

### Check Job Status

```bash
curl http://localhost:8000/api/rank-tracker/check/550e8400-e29b-41d4-a716-446655440000

# Returns:
# {
#   "job_id": "...",
#   "status": "completed",
#   "progress": 100,
#   "results": {...}
# }
```

### Check Keywords (Sync)

```bash
curl -X POST http://localhost:8000/api/rank-tracker/check-sync \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "keywords": ["keyword1"]
  }'

# Returns full results immediately
```

### Get Ranking History

```bash
curl "http://localhost:8000/api/rank-tracker/history/example.com/keyword1?days=30"

# Returns:
# {
#   "keyword": "keyword1",
#   "search_engine": "google",
#   "data": [
#     {"date": "2026-03-15", "position": 8, "title": "...", "url": "..."},
#     ...
#   ]
# }
```

### Get Trend Analysis

```bash
curl "http://localhost:8000/api/rank-tracker/trend/example.com/keyword1"

# Returns:
# {
#   "keyword": "keyword1",
#   "trend": "improving",
#   "best_position": 5,
#   "average_position": 12.5,
#   "data_points": 30
# }
```

### Get Alerts

```bash
curl "http://localhost:8000/api/rank-tracker/alerts/example.com?limit=20"

# Returns:
# {
#   "domain": "example.com",
#   "alerts": [
#     {
#       "keyword": "keyword1",
#       "previous_position": 8,
#       "current_position": 15,
#       "change": 7,
#       "alert_level": "warning"
#     },
#     ...
#   ]
# }
```

### Get Domain Summary

```bash
curl "http://localhost:8000/api/rank-tracker/summary/example.com"

# Returns:
# {
#   "domain": "example.com",
#   "summary": {
#     "total_keywords": 50,
#     "top_10_count": 12,
#     "top_50_count": 35,
#     "unranked_count": 3
#   }
# }
```

## 📊 Output Examples

### CLI Check Output

```
$ python rank_tracker.py check example.com "seo tools" "rank tracking"

============================================================
RANK TRACKING RESULTS - example.com
============================================================

Total Keywords: 2
Successful Checks: 2/2
Top 10 Rankings: 1
Top 50 Rankings: 2
Unranked: 0

Keyword                        Engine       Position   URL
------------------------------------
seo tools                      google       8          https://example.com/tools
rank tracking                  google       22         https://example.com/tracking
```

### CLI History Output

```
$ python rank_tracker.py history example.com "seo tools"

============================================================
RANKING HISTORY - seo tools
============================================================

Trend: IMPROVING
Best Position: #5
Average Position: 10.2
Data Points: 30

Date            Position     Title
...........................................................................
2026-03-05      15           SEO Tools - Best Solutions
2026-03-10      12           SEO Tools for Your Website
2026-03-15      8            Top SEO Tools for 2026
```

### CLI Alerts Output

```
$ python rank_tracker.py alerts example.com

============================================================
RECENT ALERTS - example.com
============================================================

🔴 seo tools (google)
   8 → 15 ↓7
   2026-03-15

🟡 rank tracking (google)
   10 → 20 ↓10
   2026-03-14

🔵 web audit (google)
   35 → 30 ↑5
   2026-03-13
```

## 📈 Performance Benchmarks

```
Test Configuration: 100 keywords, Google only

WITHOUT PROXIES:
  Min Delay: 5s
  Max Delay: 10s
  Time: ~45-60 minutes
  Requests/minute: 1-2
  Success Rate: 70-80%

WITH 3 PROXIES:
  Min Delay: 2s
  Max Delay: 5s
  Time: ~15-20 minutes
  Requests/minute: 5-8
  Success Rate: 95-98%

WITH 10 PROXIES:
  Min Delay: 1s
  Max Delay: 2s
  Time: ~5-10 minutes
  Requests/minute: 10-15
  Success Rate: 98-99%
```

## 🔄 Scheduling Examples

### Cron (Linux/macOS)

```bash
# Daily at midnight
0 0 * * * /usr/bin/python3 /opt/auditor/rank_tracker.py check example.com keyword1 keyword2

# Every 6 hours
0 */6 * * * /usr/bin/python3 /opt/auditor/rank_tracker.py check example.com keyword1

# Every Monday at 9 AM
0 9 * * 1 /usr/bin/python3 /opt/auditor/rank_tracker.py check example.com keyword1
```

### Windows Task Scheduler

```batch
# Create task
schtasks /create /tn "RankTracker_Daily" /tr "python C:\auditor\rank_tracker.py check example.com keyword1" /sc daily /st 00:00

# Delete task
schtasks /delete /tn "RankTracker_Daily" /f

# Run task manually
schtasks /run /tn "RankTracker_Daily"
```

### Python APScheduler

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

async def daily_check():
    async with RankTracker(...) as tracker:
        results = await tracker.check_all_keywords()

scheduler = AsyncIOScheduler()
scheduler.add_job(daily_check, 'cron', hour=0, minute=0)
scheduler.start()

asyncio.run(asyncio.Event().wait())
```

## 🎨 Data Visualization

### Ranking Chart

```
Position
   10  |  ●
        | ╱╲
   15  |●   ●─────●
        │       ╱
   20  |      ╱
        │
   25  |
      └─────────────────────────
        Mar 05  Mar 10  Mar 15
        
Trend: IMPROVING ⬆
```

### Alert Timeline

```
Mar 15: 🔴 CRITICAL - keyword1: #8→#15 (lost top 10)
Mar 14: 🟡 WARNING - keyword2: #20→#26 (dropped 6)
Mar 13: 🔵 INFO - keyword3: #30→#25 (improved 5)
Mar 12: 🔵 INFO - keyword4: #50→#45 (improved 5)
```

## 📋 File Locations

After setup, you'll have:

```
backend/
├── rank_tracker.py                 # Main engine
├── rank_tracker_api.py             # API routes
├── rank_tracker.db                 # SQLite database
├── rank_tracker_config.json        # Configuration
├── keywords.txt                    # Keywords list
└── rank_tracker.log                # Log file
```

## 🚨 Troubleshooting Quick Fixes

```bash
# Validate everything is installed
python setup_rank_tracker.py --validate

# Clear database (start fresh)
rm rank_tracker.db

# Check logs for errors
tail -f rank_tracker.log

# Test proxy connectivity
curl -x http://proxy1:8080 https://www.google.com

# Database maintenance
sqlite3 rank_tracker.db "VACUUM;"
sqlite3 rank_tracker.db "ANALYZE;"
```

## 💡 Pro Tips

1. **Batch keywords** - Track 50+ keywords at once, not one by one
2. **Use proxies** - Dramatically improves success rate
3. **Set appropriate delays** - Balance speed vs. blocking risk
4. **Schedule daily** - Automatic checks for trending data
5. **Monitor alerts** - Catch ranking drops early
6. **Export regularly** - Keep backup of ranking data
7. **Test locally** - Always test configuration before production

---

**For more commands**: `python rank_tracker.py --help`

**For more details**: Read `INDEX.md`
