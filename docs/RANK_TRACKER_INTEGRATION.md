# Rank Tracker - Complete Integration Guide

## Overview

The Rank Tracker is a production-ready SEO rank tracking system that integrates seamlessly with your website auditor. It provides:

- **Daily Position Checks** - Automatically track keyword rankings
- **Historical Data** - Store and analyze ranking trends over time
- **Multi-Engine Support** - Check Google, Bing, DuckDuckGo rankings
- **Smart Proxy Rotation** - Distribute requests across proxies
- **Rate Limiting** - Intelligent delays to prevent blocking
- **CAPTCHA Handling** - Automatic detection and backoff
- **Alerts** - Notifications for significant rank changes
- **CLI & API** - Both command-line and REST API interfaces

## Files Created

| File | Purpose |
|------|---------|
| `rank_tracker.py` | Main rank tracking engine (1500+ lines) |
| `rank_tracker_api.py` | FastAPI integration endpoints |
| `examples_rank_tracker.py` | Usage examples and quick start |
| `RANK_TRACKER_README.md` | Detailed documentation |

## Quick Start

### 1. Installation

Ensure dependencies are in `requirements.txt`:
```
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
```

Install:
```bash
pip install -r requirements.txt
```

### 2. Command-Line Usage

```bash
# Check keywords
python rank_tracker.py check example.com "keyword1" "keyword2" --engines google bing

# View history
python rank_tracker.py history example.com "keyword1" --days 30

# Show alerts
python rank_tracker.py alerts example.com --limit 20
```

### 3. Python API

```python
import asyncio
from rank_tracker import RankTracker, SearchEngine

async def main():
    async with RankTracker(
        domain="example.com",
        keywords=["seo tools", "rank tracking"],
        search_engines=[SearchEngine.GOOGLE, SearchEngine.BING]
    ) as tracker:
        results = await tracker.check_all_keywords()
        print(results)

asyncio.run(main())
```

### 4. FastAPI Integration

Add to your `api.py`:

```python
from fastapi import FastAPI
from rank_tracker_api import router

app = FastAPI()
app.include_router(router)
```

Then use the API endpoints:

```bash
# Check keywords (async)
curl -X POST http://localhost:8000/api/rank-tracker/check \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "keywords": ["seo tools"],
    "search_engines": ["google"]
  }'

# Get ranking history
curl http://localhost:8000/api/rank-tracker/history/example.com/seo%20tools

# Get trend analysis
curl http://localhost:8000/api/rank-tracker/trend/example.com/seo%20tools

# Get recent alerts
curl http://localhost:8000/api/rank-tracker/alerts/example.com
```

## Architecture

### Core Components

```
RankTracker (Main class)
├── ProxyRotator (Proxy management)
├── RateLimiter (Request throttling)
├── SearchEngineFetcher (Abstract base)
│   ├── GoogleFetcher
│   ├── BingFetcher
│   └── DuckDuckGoFetcher
├── RankDatabase (SQLite storage)
│   └── rank_records table
│   └── rank_alerts table
└── CLI Interface (argparse)
```

### Data Flow

```
1. User initiates check
   ↓
2. RankTracker loads keywords
   ↓
3. For each keyword + search engine:
   - ProxyRotator selects proxy
   - RateLimiter waits appropriate delay
   - Fetcher makes search request
   - Parser extracts ranking position
   - RankDatabase saves record
   - Alert logic checks for changes
   ↓
4. Results returned to user
```

## Configuration Options

### Rate Limiting

```python
# Conservative (safer)
async with RankTracker(..., min_delay=5.0, max_delay=10.0) as tracker:
    pass

# Aggressive (faster, needs proxies)
async with RankTracker(..., min_delay=1.0, max_delay=2.0, proxies=[...]) as tracker:
    pass
```

### Proxy Rotation

```python
proxies = [
    "http://proxy1.com:8080",
    "http://proxy2.com:8080",
    "http://user:pass@proxy3.com:3128",
]

async with RankTracker(..., proxies=proxies) as tracker:
    pass
```

### Search Engines

```python
# Single engine
engines = [SearchEngine.GOOGLE]

# Multiple engines
engines = [SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.DUCKDUCKGO]

async with RankTracker(..., search_engines=engines) as tracker:
    pass
```

## Database Schema

### rank_records table

Stores all ranking checks:

```sql
CREATE TABLE rank_records (
    id INTEGER PRIMARY KEY,
    keyword TEXT NOT NULL,
    domain TEXT NOT NULL,
    search_engine TEXT NOT NULL,
    position INTEGER,              -- Position #1-100 or NULL
    url TEXT,                      -- Ranking URL
    title TEXT,                    -- Page title
    snippet TEXT,                  -- Search snippet
    timestamp TEXT NOT NULL,       -- ISO timestamp
    checked_at TEXT NOT NULL
);

-- Index for fast lookups
CREATE INDEX idx_keyword_domain ON rank_records(keyword, domain);
```

### rank_alerts table

Stores significant rank changes:

```sql
CREATE TABLE rank_alerts (
    id INTEGER PRIMARY KEY,
    keyword TEXT NOT NULL,
    domain TEXT NOT NULL,
    search_engine TEXT NOT NULL,
    previous_position INTEGER,     -- Old position
    current_position INTEGER,      -- New position
    change INTEGER NOT NULL,       -- Position delta
    alert_level TEXT NOT NULL,     -- critical, warning, info
    timestamp TEXT NOT NULL
);
```

## Features Deep Dive

### 1. Rotating User Agents

The system automatically rotates through realistic user agents to avoid detection:

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...",
    # ... more agents
]

# Automatically used in each request
headers = fetcher.get_headers()  # Returns random user agent
```

### 2. Proxy Rotation

Distributes requests across multiple proxies:

```python
proxy_rotator = ProxyRotator([
    "http://proxy1:8080",
    "http://proxy2:8080",
    "http://proxy3:8080",
])

# Each request gets next proxy in rotation
proxy = proxy_rotator.get_proxy()  # Returns proxy1, then proxy2, etc.
```

### 3. Rate Limiting

Intelligent delays between requests:

```python
rate_limiter = RateLimiter(min_delay=2.0, max_delay=5.0)

for request in requests:
    await rate_limiter.wait()  # Waits random time between 2-5 seconds
    await make_request()
```

### 4. CAPTCHA Detection

Automatically detects CAPTCHA challenges:

```python
async def _fetch_page(self, url: str):
    html = await resp.text()
    
    if self._detect_captcha(html):
        logger.warning("CAPTCHA detected, backing off...")
        await asyncio.sleep(random.uniform(30, 60))
        return None  # Retry later
```

### 5. Alerts

Automatic alerts for significant rank changes:

```python
# Alert Levels
- CRITICAL: Lost top 10 position or dropped out completely
- WARNING: Dropped 5+ positions
- INFO: Improved 5+ positions

# Example
Alert: "seo tools" on google dropped from #8 to #15 [WARNING]
```

### 6. Trend Analysis

Analyzes historical data for trends:

```python
trend = tracker.get_trend_analysis(keyword, engine, days=30)
# Returns:
# - trend: "improving", "declining", "stable", "dropped_out"
# - first_position, last_position, best_position, worst_position
# - average_position, data_points
```

## Usage Patterns

### Pattern 1: Daily Automated Check

```python
# scheduler.py
import schedule
import time

async def daily_check():
    async with RankTracker(
        domain="example.com",
        keywords=["kw1", "kw2", "kw3"]
    ) as tracker:
        results = await tracker.check_all_keywords()
        # Process results...

schedule.every().day.at("00:00").do(daily_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Pattern 2: On-Demand Check

```python
# In FastAPI endpoint
@app.post("/api/check")
async def check_keywords(domain: str, keywords: List[str]):
    async with RankTracker(domain, keywords) as tracker:
        results = await tracker.check_all_keywords()
    return results
```

### Pattern 3: Monitor with Alerts

```python
db = RankDatabase()

# Run check
async with RankTracker(...) as tracker:
    results = await tracker.check_all_keywords()

# Check alerts
alerts = db.get_alerts(domain)
for alert in alerts:
    if alert.alert_level == "critical":
        send_email_alert(alert)
    elif alert.alert_level == "warning":
        send_slack_notification(alert)
```

### Pattern 4: Historical Analysis

```python
async with RankTracker(domain, [keyword]) as tracker:
    # Get 30-day chart
    chart = tracker.get_ranking_chart(keyword, SearchEngine.GOOGLE, days=30)
    
    # Get trend
    trend = tracker.get_trend_analysis(keyword, SearchEngine.GOOGLE, days=30)
    
    # Plot data
    dates = [d["date"] for d in chart["data"]]
    positions = [d["position"] for d in chart["data"]]
    
    plt.plot(dates, positions)
    plt.show()
```

## Troubleshooting

### Issue: "Rate limited (429)"

**Solution**: Increase delays and/or add more proxies

```python
# Option 1: Longer delays
async with RankTracker(..., min_delay=5.0, max_delay=10.0) as tracker:
    pass

# Option 2: Add proxies
async with RankTracker(..., proxies=[...]) as tracker:
    pass
```

### Issue: "CAPTCHA detected"

**Expected behavior** - System automatically backs off

- System waits 30-60 seconds
- Automatically retries
- Uses proxy rotation if available

If persistent:
- Add more/better proxies (residential proxies better than datacenter)
- Increase delays
- Try DuckDuckGo instead of Google

### Issue: "Connection timeout"

**Solution**: Check internet, increase timeout

```python
# Increase session timeout in fetcher
async with self.session.get(
    url,
    timeout=aiohttp.ClientTimeout(total=60),  # Increased from 30
) as resp:
    pass
```

### Issue: "Keyword not ranking"

- Keyword might not be indexed
- Domain might have ranking issues
- Try broader search terms
- Check if keyword is in Google Search Console

## Performance Tips

### 1. Batch Keywords

Track multiple keywords in one session for efficiency:

```python
# Good
async with RankTracker(domain, ["kw1", "kw2", "kw3"]) as tracker:
    results = await tracker.check_all_keywords()

# Inefficient
async with RankTracker(domain, ["kw1"]) as tracker:
    results1 = await tracker.check_all_keywords()
async with RankTracker(domain, ["kw2"]) as tracker:
    results2 = await tracker.check_all_keywords()
```

### 2. Use Proxy Rotation

With proxies, can use shorter delays:

```python
# Without proxies: 5-10 second delays
async with RankTracker(..., min_delay=5.0, max_delay=10.0) as tracker:
    pass

# With proxies: 2-5 second delays
async with RankTracker(..., proxies=[...], min_delay=2.0, max_delay=5.0) as tracker:
    pass
```

### 3. Limit Search Engines

Only track engines you care about:

```python
# Faster: only Google
async with RankTracker(
    domain,
    keywords,
    search_engines=[SearchEngine.GOOGLE]
) as tracker:
    pass

# Slower: all engines
async with RankTracker(
    domain,
    keywords,
    search_engines=[SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.DUCKDUCKGO]
) as tracker:
    pass
```

## Integration with Website Auditor

### Adding to FastAPI

```python
# api.py
from fastapi import FastAPI
from rank_tracker_api import router as rank_tracker_router

app = FastAPI()

# Existing routes...
@app.get("/api/audits")
async def list_audits():
    pass

# Add rank tracker routes
app.include_router(rank_tracker_router)

# Now available at /api/rank-tracker/*
```

### Database Considerations

The rank tracker uses its own SQLite database (`rank_tracker.db`). You can:

1. **Keep separate** - Different database for rank data
2. **Migrate to PostgreSQL** - For production
3. **Consolidate** - Merge into main auditor database

```python
# Use custom database path
async with RankTracker(
    domain,
    keywords,
    db_path="/var/lib/auditor/rank_data.db"
) as tracker:
    pass
```

### API Response Format

All responses follow standard format:

```json
{
  "status": "success|error|processing",
  "data": {...},
  "error": null,
  "timestamp": "2026-03-15T10:30:00Z"
}
```

## Scheduling

### Using APScheduler

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Daily at midnight
scheduler.add_job(
    daily_check,
    'cron',
    hour=0,
    minute=0
)

# Every 6 hours
scheduler.add_job(
    check_critical_keywords,
    'interval',
    hours=6
)

scheduler.start()
```

### Using Cron (Linux/macOS)

```bash
# Add to crontab -e
0 0 * * * /usr/bin/python3 /opt/auditor/rank_tracker.py check example.com "kw1" "kw2" >> /var/log/rank_check.log 2>&1
0 */6 * * * /usr/bin/python3 /opt/auditor/rank_tracker.py check example.com "kw3" >> /var/log/rank_check.log 2>&1
```

### Using Windows Task Scheduler

```batch
schtasks /create /tn "RankTracker_Daily" /tr "python C:\auditor\rank_tracker.py check example.com keyword" /sc daily /st 00:00
```

## Monitoring & Logging

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Log Levels

- **DEBUG**: Detailed info (rate limiting, retries, etc.)
- **INFO**: General info (keyword checked, position found)
- **WARNING**: Potential issues (CAPTCHA detected, rate limited)
- **ERROR**: Errors (connection failed, parse error)

### Example Output

```
2026-03-15 10:30:00 - rank_tracker - INFO - Checking: seo tools on google
2026-03-15 10:30:02 - rank_tracker - DEBUG - Rate limiting: waiting 2.45s
2026-03-15 10:30:05 - rank_tracker - INFO - Found at position 8
2026-03-15 10:30:05 - rank_tracker - INFO - Saved to database
```

## Advanced Topics

### Custom Search Engine Implementation

```python
from rank_tracker import SearchEngineFetcher

class CustomSearchFetcher(SearchEngineFetcher):
    async def search(self, query: str, domain: str):
        # Your custom implementation
        pass
    
    def _parse_results(self, html: str, query: str, domain: str):
        # Your custom parser
        pass
```

### Distributed Tracking

For large keyword lists, distribute across multiple workers:

```python
# worker.py
import asyncio
from rank_tracker import RankTracker

async def worker(domain, keywords_chunk, worker_id):
    async with RankTracker(domain, keywords_chunk) as tracker:
        results = await tracker.check_all_keywords()
    return results

# main.py
import asyncio

domain = "example.com"
keywords = [...]  # 1000 keywords
chunk_size = 100

chunks = [keywords[i:i+chunk_size] for i in range(0, len(keywords), chunk_size)]
tasks = [worker(domain, chunk, i) for i, chunk in enumerate(chunks)]

results = await asyncio.gather(*tasks)
```

### Export to CSV/JSON

```python
import csv
import json

# Export to CSV
db = RankDatabase()
records = db.get_history("example.com", "keyword", "google", days=30)

with open("ranking_history.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "Position", "URL"])
    for record in records:
        writer.writerow([record.timestamp[:10], record.position, record.url])

# Export to JSON
data = [r.to_dict() for r in records]
with open("ranking_history.json", "w") as f:
    json.dump(data, f, indent=2)
```

## Production Deployment

### Requirements

- Python 3.7+
- SQLite (built-in) or PostgreSQL
- 100MB+ disk space for database
- Network access to search engines

### Environment Variables

```bash
# .env
RANK_TRACKER_DB=/var/lib/auditor/rank_tracker.db
RANK_TRACKER_PROXIES=http://proxy1:8080,http://proxy2:8080
RANK_TRACKER_MIN_DELAY=3.0
RANK_TRACKER_MAX_DELAY=8.0
```

### Docker Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY rank_tracker.py .

# Volume for persistent database
VOLUME ["/data"]

# Run via CLI
ENTRYPOINT ["python", "rank_tracker.py"]
```

```bash
docker run -v rank_data:/data rank-tracker check example.com keyword1 keyword2
```

### Systemd Service

```ini
[Unit]
Description=Rank Tracker Service
After=network.target

[Service]
Type=simple
User=auditor
WorkingDirectory=/opt/auditor
ExecStart=/usr/bin/python3 /opt/auditor/rank_tracker.py check example.com keywords
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

## Next Steps

1. **Install & Test** - Run examples with your domain
2. **Schedule Daily Checks** - Set up cron/scheduler
3. **Monitor Alerts** - Set up email/Slack notifications
4. **Analyze Trends** - Use historical data for insights
5. **Optimize SEO** - Act on recommendations
6. **Scale** - Distribute across multiple workers if needed

## Support & Documentation

- **Main Docs**: See `RANK_TRACKER_README.md`
- **Examples**: Run `examples_rank_tracker.py`
- **CLI Help**: `python rank_tracker.py --help`
- **API Docs**: FastAPI auto-docs at `/docs`

---

**Happy Rank Tracking!** 🚀

For questions or issues, refer to the troubleshooting section or check the source code comments.
