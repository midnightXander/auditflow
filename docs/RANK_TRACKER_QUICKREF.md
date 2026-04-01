# Rank Tracker - Quick Reference

## Installation

```bash
pip install aiohttp beautifulsoup4
```

## CLI Commands

### Check Keywords

```bash
# Basic check
python rank_tracker.py check example.com "keyword1" "keyword2"

# With Bing
python rank_tracker.py check example.com "keyword" --engines bing

# With proxies
python rank_tracker.py check example.com "keyword" --proxies http://proxy1:8080 http://proxy2:8080

# Custom database
python rank_tracker.py check example.com "keyword" --db /path/to/db.db
```

### View History

```bash
# Last 30 days
python rank_tracker.py history example.com "keyword"

# Last 90 days
python rank_tracker.py history example.com "keyword" --days 90

# Different engine
python rank_tracker.py history example.com "keyword" --engine bing
```

### View Alerts

```bash
# Recent alerts
python rank_tracker.py alerts example.com

# Specific limit
python rank_tracker.py alerts example.com --limit 50
```

## Python API

### Basic Usage

```python
import asyncio
from rank_tracker import RankTracker, SearchEngine

async def main():
    async with RankTracker(
        domain="example.com",
        keywords=["keyword1", "keyword2"]
    ) as tracker:
        # Check all keywords
        results = await tracker.check_all_keywords()
        
        # Get history
        chart = tracker.get_ranking_chart(
            keyword="keyword1",
            search_engine=SearchEngine.GOOGLE,
            days=30
        )
        
        # Get trend
        trend = tracker.get_trend_analysis(
            keyword="keyword1",
            search_engine=SearchEngine.GOOGLE
        )

asyncio.run(main())
```

### With Proxies

```python
async with RankTracker(
    domain="example.com",
    keywords=["keyword"],
    proxies=[
        "http://proxy1:8080",
        "http://proxy2:8080",
    ]
) as tracker:
    results = await tracker.check_all_keywords()
```

### With Custom Delays

```python
async with RankTracker(
    domain="example.com",
    keywords=["keyword"],
    min_delay=3.0,      # 3 seconds
    max_delay=8.0,      # 8 seconds
) as tracker:
    results = await tracker.check_all_keywords()
```

### Multiple Engines

```python
async with RankTracker(
    domain="example.com",
    keywords=["keyword"],
    search_engines=[
        SearchEngine.GOOGLE,
        SearchEngine.BING,
        SearchEngine.DUCKDUCKGO,
    ]
) as tracker:
    results = await tracker.check_all_keywords()
```

### Progress Callback

```python
async def progress_callback(progress: int, status: str):
    print(f"[{progress}%] {status}")

async with RankTracker(...) as tracker:
    results = await tracker.check_all_keywords(
        progress_callback=progress_callback
    )
```

## FastAPI Integration

### Add Routes

```python
# api.py
from fastapi import FastAPI
from rank_tracker_api import router

app = FastAPI()
app.include_router(router)
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rank-tracker/check` | Start async rank check |
| GET | `/api/rank-tracker/check/{job_id}` | Get job status |
| POST | `/api/rank-tracker/check-sync` | Check keywords (blocking) |
| GET | `/api/rank-tracker/history/{domain}/{keyword}` | Get ranking history |
| GET | `/api/rank-tracker/trend/{domain}/{keyword}` | Get trend analysis |
| GET | `/api/rank-tracker/alerts/{domain}` | Get recent alerts |
| GET | `/api/rank-tracker/summary/{domain}` | Get domain summary |

### Start Async Check

```bash
curl -X POST http://localhost:8000/api/rank-tracker/check \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "keywords": ["keyword1", "keyword2"],
    "search_engines": ["google"]
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Started tracking 2 keywords"
}
```

### Check Job Status

```bash
curl http://localhost:8000/api/rank-tracker/check/550e8400-e29b-41d4-a716-446655440000
```

### Get History

```bash
curl http://localhost:8000/api/rank-tracker/history/example.com/keyword1?days=30
```

### Get Trend

```bash
curl http://localhost:8000/api/rank-tracker/trend/example.com/keyword1
```

### Get Alerts

```bash
curl http://localhost:8000/api/rank-tracker/alerts/example.com
```

## Common Patterns

### Daily Check

```python
import schedule
import asyncio

async def daily_check():
    async with RankTracker(
        domain="example.com",
        keywords=["keyword1", "keyword2"]
    ) as tracker:
        results = await tracker.check_all_keywords()
        print(results)

schedule.every().day.at("00:00").do(daily_check)

while True:
    schedule.run_pending()
    await asyncio.sleep(60)
```

### Handle Alerts

```python
from rank_tracker import RankDatabase

db = RankDatabase()
alerts = db.get_alerts("example.com")

for alert in alerts:
    if alert.alert_level == "critical":
        send_email(f"CRITICAL: {alert.keyword} dropped to {alert.current_position}")
    elif alert.alert_level == "warning":
        send_slack(f"WARNING: {alert.keyword} changed position")
```

### Export Results

```python
import json
import csv

# Export to JSON
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

# Export to CSV
with open("rankings.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=["keyword", "position", "url"])
    writer.writeheader()
    for record in results["records"]:
        writer.writerow(record)
```

## Data Models

### RankRecord

```python
@dataclass
class RankRecord:
    keyword: str              # Searched keyword
    domain: str              # Target domain
    search_engine: str       # google/bing/duckduckgo
    position: Optional[int]  # Position #1-100 or None
    url: Optional[str]       # Ranking URL
    title: Optional[str]     # Page title
    snippet: Optional[str]   # Search snippet
    timestamp: str           # ISO timestamp
    checked_at: str          # When checked
```

### RankAlert

```python
@dataclass
class RankAlert:
    keyword: str
    domain: str
    search_engine: str
    previous_position: Optional[int]
    current_position: Optional[int]
    change: int              # Position delta
    alert_level: str         # critical/warning/info
    timestamp: str           # ISO timestamp
```

## Alert Levels

| Level | Trigger | Example |
|-------|---------|---------|
| CRITICAL | Lost top 10 or dropped out | #8 → #15 or #5 → Unranked |
| WARNING | Dropped 5+ positions | #20 → #26 |
| INFO | Gained 5+ positions | #20 → #12 |

## Trends

| Trend | Meaning |
|-------|---------|
| improving | Position getting better |
| declining | Position getting worse |
| stable | Position relatively unchanged |
| dropped_out | Keyword no longer ranks |
| unranked | Never ranked in period |

## Database

```python
from rank_tracker import RankDatabase

db = RankDatabase("rank_tracker.db")

# Get latest record
record = db.get_latest_record("keyword", "example.com", "google")

# Get history
history = db.get_history("keyword", "example.com", "google", days=30)

# Get alerts
alerts = db.get_alerts("example.com", limit=50)

# Save record
db.save_record(rank_record)

# Save alert
db.save_alert(rank_alert)
```

## Setup

```bash
# Interactive setup
python setup_rank_tracker.py

# Setup specific domain
python setup_rank_tracker.py --domain example.com

# Generate keywords file
python setup_rank_tracker.py --gen-keywords example.com

# Validate installation
python setup_rank_tracker.py --validate

# Show examples
python setup_rank_tracker.py --examples
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Rate limited (429)" | Increase delays, add proxies |
| "CAPTCHA detected" | Normal - system backs off automatically |
| "Connection timeout" | Check internet, increase timeout |
| "Keyword not ranking" | Check if indexed, try broader terms |
| Missing module | Run `pip install aiohttp beautifulsoup4` |

## Performance

| Configuration | Speed | Cost |
|---------------|-------|------|
| No proxies, 5-10s delay | Slow | Free |
| No proxies, 2-5s delay | Medium | High blocking risk |
| Proxies, 2-5s delay | Fast | Proxy cost |
| Proxies, 1-2s delay | Very fast | Higher proxy cost |

## Files

| File | Purpose |
|------|---------|
| `rank_tracker.py` | Main engine (1500+ lines) |
| `rank_tracker_api.py` | FastAPI routes |
| `examples_rank_tracker.py` | Usage examples |
| `setup_rank_tracker.py` | Setup wizard |
| `RANK_TRACKER_README.md` | Full documentation |
| `RANK_TRACKER_INTEGRATION.md` | Integration guide |
| `rank_tracker.db` | SQLite database |

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Run setup: `python setup_rank_tracker.py`
3. Check keywords: `python rank_tracker.py check example.com keyword`
4. View results: `python rank_tracker.py history example.com keyword`
5. Integrate with FastAPI: Add router to api.py
6. Schedule checks: Use scheduler/cron
7. Monitor alerts: Set up notifications

---

**For more info**: See `RANK_TRACKER_README.md` and `RANK_TRACKER_INTEGRATION.md`
