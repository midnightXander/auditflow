# Rank Tracking Engine

Production-ready SEO rank tracking system with daily position checks, historical analysis, trend detection, and alerts.

## Features

✅ **Daily Position Checks** - Track keyword rankings across multiple search engines
✅ **Historical Data & Charting** - Store and visualize ranking trends over time
✅ **Trend Analysis** - Automatic trend detection (improving, declining, stable, dropped)
✅ **Rank Change Alerts** - Notifications for significant position changes
✅ **Multi-Engine Support** - Google, Bing, DuckDuckGo
✅ **Proxy Rotation** - Distribute requests across proxy list
✅ **Rotating User Agents** - Avoid detection with randomized user agents
✅ **Rate Limiting** - Intelligent rate limiting to prevent blocking
✅ **CAPTCHA Detection** - Detect and handle CAPTCHA challenges
✅ **SQLite Database** - Persistent storage of all rank data
✅ **CLI Interface** - Command-line tools for easy usage
✅ **Async/Await** - High-performance concurrent requests

## Installation

1. Add to your `requirements.txt`:
```
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Python API

```python
import asyncio
from rank_tracker import RankTracker, SearchEngine

async def main():
    keywords = ["seo tools", "rank tracking", "website audit"]
    
    async with RankTracker(
        domain="example.com",
        keywords=keywords,
        search_engines=[SearchEngine.GOOGLE, SearchEngine.BING],
        db_path="rank_tracker.db",
        min_delay=2.0,
        max_delay=5.0
    ) as tracker:
        # Check all keywords
        results = await tracker.check_all_keywords(
            progress_callback=async_progress_callback
        )
        
        # Get ranking history
        chart = tracker.get_ranking_chart(
            keyword="seo tools",
            search_engine=SearchEngine.GOOGLE,
            days=30
        )
        
        # Analyze trends
        trend = tracker.get_trend_analysis(
            keyword="seo tools",
            search_engine=SearchEngine.GOOGLE
        )

asyncio.run(main())
```

### Command-Line Interface

#### Check Keywords

```bash
# Check multiple keywords on Google
python rank_tracker.py check example.com "seo tools" "rank tracking" --engines google bing

# With proxy rotation
python rank_tracker.py check example.com "seo tools" --proxies http://proxy1:8080 http://proxy2:8080

# Specify custom database
python rank_tracker.py check example.com "seo tools" --db /path/to/tracker.db
```

#### View Ranking History

```bash
# Show last 30 days of history
python rank_tracker.py history example.com "seo tools" --engine google --days 30

# Last 90 days
python rank_tracker.py history example.com "seo tools" --days 90
```

#### Show Alerts

```bash
# Show last 20 alerts for domain
python rank_tracker.py alerts example.com --limit 20

# All alerts
python rank_tracker.py alerts example.com --limit 1000
```

## Configuration

### Proxy Rotation

```python
from rank_tracker import ProxyRotator

proxy_rotator = ProxyRotator([
    "http://user:pass@proxy1.com:8080",
    "http://user:pass@proxy2.com:8080",
    "http://user:pass@proxy3.com:8080",
])

# Add proxy on the fly
proxy_rotator.add_proxy("http://user:pass@proxy4.com:8080")

# Use with tracker
async with RankTracker(..., proxies=proxy_rotator.proxies) as tracker:
    ...
```

### Rate Limiting

```python
async with RankTracker(
    domain="example.com",
    keywords=["keyword1", "keyword2"],
    min_delay=3.0,      # Minimum 3 seconds between requests
    max_delay=8.0,      # Maximum 8 seconds between requests
) as tracker:
    ...
```

### Custom Database

```bash
# Specify custom database path
python rank_tracker.py check example.com "keyword" --db /var/lib/rank_tracker/my_domain.db
```

## Data Models

### RankRecord
```python
@dataclass
class RankRecord:
    keyword: str              # The searched keyword
    domain: str              # Target domain
    search_engine: str       # google, bing, duckduckgo
    position: Optional[int]  # Position #1-100 (None if unranked)
    url: Optional[str]       # URL of ranking page
    title: Optional[str]     # Page title
    snippet: Optional[str]   # Search snippet
    timestamp: str           # ISO timestamp
    checked_at: str          # When the check was performed
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
    change: int                    # Position change (+/-)
    alert_level: str              # critical, warning, info
    timestamp: str
```

## Alert Levels

| Level | Condition | Example |
|-------|-----------|---------|
| **CRITICAL** | Lost top 10 position or dropped out completely | #8 → #15 or #5 → Unranked |
| **WARNING** | Dropped 5+ positions | #20 → #26 |
| **INFO** | Gained 5+ positions | #20 → #12 |

## Trend Types

| Trend | Meaning |
|-------|---------|
| `improving` | Position improving over time |
| `declining` | Position getting worse |
| `stable` | Position relatively unchanged |
| `dropped_out` | Keyword no longer ranking |
| `unranked` | Keyword never ranked in period |

## Search Engine Support

### Google
- Uses site-restricted search: `site:example.com keyword`
- Most reliable results
- Requires User-Agent rotation

### Bing
- Alternative search engine data
- Good for competitive analysis
- Lower blocking rate than Google

### DuckDuckGo
- Privacy-focused search engine
- Lower traffic volume
- More permissive crawling

## Performance Tips

### Optimize Request Rate
```python
# For aggressive tracking (use proxies):
async with RankTracker(..., min_delay=1.0, max_delay=2.0, proxies=[...]) as tracker:
    ...

# For conservative tracking (no proxies):
async with RankTracker(..., min_delay=5.0, max_delay=10.0) as tracker:
    ...
```

### Use Proxy Rotation
- Distribute requests across multiple proxies
- Reduces chance of IP blocking
- Increases success rate significantly

### Batch Keywords
- Track multiple keywords in one session
- More efficient than individual checks
- Results cached in database

## Error Handling

```python
try:
    async with RankTracker(...) as tracker:
        results = await tracker.check_all_keywords()
except Exception as e:
    logger.error(f"Tracking failed: {e}")
    # Retry logic, alerts, etc.
```

## Database Schema

### rank_records table
```sql
CREATE TABLE rank_records (
    id INTEGER PRIMARY KEY,
    keyword TEXT NOT NULL,
    domain TEXT NOT NULL,
    search_engine TEXT NOT NULL,
    position INTEGER,
    url TEXT,
    title TEXT,
    snippet TEXT,
    timestamp TEXT NOT NULL,
    checked_at TEXT NOT NULL
);
```

### rank_alerts table
```sql
CREATE TABLE rank_alerts (
    id INTEGER PRIMARY KEY,
    keyword TEXT NOT NULL,
    domain TEXT NOT NULL,
    search_engine TEXT NOT NULL,
    previous_position INTEGER,
    current_position INTEGER,
    change INTEGER NOT NULL,
    alert_level TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

## Scheduling Daily Checks

### Using APScheduler
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

async def scheduled_check():
    async with RankTracker(...) as tracker:
        results = await tracker.check_all_keywords()
        # Process results...

scheduler = AsyncIOScheduler()
scheduler.add_job(scheduled_check, 'cron', hour=0, minute=0)  # Run daily at midnight
scheduler.start()

asyncio.run(asyncio.sleep(86400))  # Keep running
```

### Using Cron (Linux/macOS)
```bash
# Add to crontab
0 0 * * * cd /path/to/auditor && python rank_tracker.py check example.com "keyword1" "keyword2" >> logs/rank_check.log 2>&1
```

### Using Windows Task Scheduler
```batch
# Create scheduled task
schtasks /create /tn "RankTracker" /tr "python C:\path\to\rank_tracker.py check example.com keyword1 keyword2" /sc daily /st 00:00
```

## CAPTCHA Handling

The system automatically:
1. Detects CAPTCHA responses
2. Logs a warning
3. Backs off for 30-60 seconds
4. Retries the request

If CAPTCHA persists:
- Add more proxies to rotation
- Increase delay between requests
- Use residential proxies (more expensive but effective)

## Rate Limiting Behavior

The system implements intelligent rate limiting:
- Random delay between `min_delay` and `max_delay`
- Respects HTTP 429 (Too Many Requests) responses
- Exponential backoff on repeated failures
- Automatic retry with increased delay

## Logging

Enable debug logging to monitor behavior:
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Limitations

- Only searches first ~100 results (Google SERPs typically show 10-100 results)
- Requires valid User-Agent headers (handled automatically)
- Rate limiting may cause delays on large keyword lists
- CAPTCHA can stop progress (handled with backoff)
- Search results may vary by location/language

## Future Enhancements

- [ ] Location-based ranking checks (support local SEO)
- [ ] SERP feature tracking (featured snippets, PAA, etc.)
- [ ] Competitor tracking
- [ ] Mobile vs Desktop rankings
- [ ] Email alert notifications
- [ ] Dashboard visualization
- [ ] API endpoint for web interface
- [ ] Machine learning trend forecasting

## Troubleshooting

### "Rate limited (429)"
- Increase delays: `min_delay=5, max_delay=10`
- Add more proxies
- Reduce keyword list size

### "CAPTCHA detected"
- Normal behavior, system backs off automatically
- Use residential proxies for better results
- Try different search engines (Bing is more lenient)

### "Connection timeout"
- Check internet connection
- Increase timeout: Configure `aiohttp.ClientTimeout`
- Check if target search engine is accessible

### "Unranked keyword"
- Keyword may not be indexed
- Domain may have ranking issues
- Try broader search terms

## License

MIT License - See LICENSE file

## Support

For issues, questions, or suggestions:
1. Check logs for error messages
2. Review troubleshooting section
3. Verify proxy/network connectivity
4. Check search engine availability
