# Rank Tracker - Complete Documentation Index

## 📚 Documentation Files

### Quick Start (START HERE!)
- **[RANK_TRACKER_QUICKREF.md](RANK_TRACKER_QUICKREF.md)** - Quick reference guide
  - CLI commands
  - Python API examples
  - FastAPI integration
  - Common patterns

### Installation & Setup
- **[setup_rank_tracker.py](setup_rank_tracker.py)** - Interactive setup wizard
  - Run: `python setup_rank_tracker.py`
  - Options: `--domain`, `--validate`, `--examples`, `--gen-keywords`

### Core Documentation
- **[RANK_TRACKER_README.md](RANK_TRACKER_README.md)** - Comprehensive documentation
  - Features overview
  - Installation instructions
  - Usage patterns
  - Configuration options
  - Troubleshooting
  - Performance tips
  - Scheduling guide

- **[RANK_TRACKER_INTEGRATION.md](RANK_TRACKER_INTEGRATION.md)** - Integration guide
  - Architecture overview
  - FastAPI integration
  - Database considerations
  - Advanced topics
  - Distributed tracking
  - Production deployment
  - Systemd/Docker setup

### Implementation Details
- **[RANK_TRACKER_SUMMARY.md](RANK_TRACKER_SUMMARY.md)** - Implementation summary
  - What was created
  - Architecture diagram
  - Quick start guide
  - Feature overview
  - Data models
  - API endpoints
  - Use cases

### Deployment
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Production checklist
  - Pre-deployment checks
  - Setup verification
  - Optimization steps
  - Scheduling configuration
  - API integration testing
  - Monitoring setup
  - Emergency procedures

## 💻 Code Files

### Main Implementation (1500+ lines)
```
rank_tracker.py
├── Core Classes:
│   ├── RankTracker (main orchestrator)
│   ├── RankDatabase (SQLite management)
│   ├── ProxyRotator (proxy management)
│   ├── RateLimiter (request throttling)
│   └── SearchEngineFetcher (abstract base)
│
├── Search Engine Implementations:
│   ├── GoogleFetcher
│   ├── BingFetcher
│   └── DuckDuckGoFetcher
│
├── Data Models:
│   ├── RankRecord
│   ├── RankAlert
│   └── Enums (SearchEngine, RankChangeAlertLevel)
│
├── CLI Interface:
│   ├── check command
│   ├── history command
│   └── alerts command
│
└── Utilities:
    ├── USER_AGENTS list
    └── CAPTCHA detection
```

### FastAPI Integration (250+ lines)
```
rank_tracker_api.py
├── API Models:
│   ├── TrackingRequest
│   ├── RankCheckResponse
│   ├── RankAlertResponse
│   └── TrendAnalysisResponse
│
├── Endpoints:
│   ├── POST /api/rank-tracker/check (async)
│   ├── GET /api/rank-tracker/check/{job_id}
│   ├── POST /api/rank-tracker/check-sync
│   ├── GET /api/rank-tracker/history/{domain}/{keyword}
│   ├── GET /api/rank-tracker/trend/{domain}/{keyword}
│   ├── GET /api/rank-tracker/alerts/{domain}
│   └── GET /api/rank-tracker/summary/{domain}
│
└── Background Tasks:
    └── _run_tracking_job
```

### Examples & Setup (300+ lines combined)
```
examples_rank_tracker.py          - 8 complete working examples
setup_rank_tracker.py             - Interactive configuration wizard
```

## 🚀 Getting Started

### 1. Installation (5 minutes)
```bash
# Install dependencies
pip install aiohttp beautifulsoup4

# Validate installation
python setup_rank_tracker.py --validate
```

### 2. Setup (5-10 minutes)
```bash
# Interactive setup
python setup_rank_tracker.py

# Or with specific domain
python setup_rank_tracker.py --domain example.com
```

### 3. First Test (5 minutes)
```bash
# Test with 2-3 keywords
python rank_tracker.py check example.com "keyword1" "keyword2"

# View results
python rank_tracker.py history example.com "keyword1"
```

### 4. Integration (15-30 minutes)
```python
# Add to api.py
from rank_tracker_api import router
app.include_router(router)

# Then test endpoints
curl -X POST http://localhost:8000/api/rank-tracker/check \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "keywords": ["keyword1"]}'
```

### 5. Scheduling (15 minutes)
```bash
# Option 1: Cron
0 0 * * * python rank_tracker.py check example.com keyword1 keyword2

# Option 2: Windows Task Scheduler
schtasks /create /tn "RankTracker" /tr "python rank_tracker.py check example.com keyword1" /sc daily /st 00:00

# Option 3: Python APScheduler (see examples)
```

## 📖 Usage Guide by Use Case

### I want to check keywords once
```bash
python rank_tracker.py check example.com "keyword1" "keyword2"
```
👉 See: **RANK_TRACKER_QUICKREF.md** → CLI Commands

### I want to check keywords daily
```python
# See: examples_rank_tracker.py → Example: Daily Check Pattern
schedule.every().day.at("00:00").do(daily_check)
```
👉 See: **RANK_TRACKER_INTEGRATION.md** → Scheduling

### I want to analyze ranking trends
```python
tracker.get_trend_analysis(keyword, search_engine, days=30)
```
👉 See: **RANK_TRACKER_README.md** → Trend Analysis

### I want to get alerts for rank changes
```python
db.get_alerts(domain)
```
👉 See: **examples_rank_tracker.py** → Example: Alert Management

### I want to use with my FastAPI app
```python
from rank_tracker_api import router
app.include_router(router)
```
👉 See: **rank_tracker_api.py** & **RANK_TRACKER_INTEGRATION.md**

### I want to track 100+ keywords
```python
# Use proxy rotation
async with RankTracker(..., proxies=[...]) as tracker:
    pass
```
👉 See: **RANK_TRACKER_INTEGRATION.md** → Performance Tips

### I want to deploy to production
1. Follow **DEPLOYMENT_CHECKLIST.md**
2. Review **RANK_TRACKER_INTEGRATION.md** → Production Deployment
3. Use **setup_rank_tracker.py** to generate config

### I'm getting "Rate limited" errors
1. Increase delays: `min_delay=5.0, max_delay=10.0`
2. Add proxies: `--proxies http://...`
3. See: **RANK_TRACKER_README.md** → Troubleshooting

### I'm getting "CAPTCHA detected"
- This is normal! System automatically handles it
- Add more proxies for better results
- See: **RANK_TRACKER_README.md** → CAPTCHA Handling

## 🔍 API Reference

### CLI Commands
```bash
python rank_tracker.py check <domain> <keywords...> [options]
python rank_tracker.py history <domain> <keyword> [options]
python rank_tracker.py alerts <domain> [options]
```
👉 Run: `python rank_tracker.py --help`

### Python Classes

#### RankTracker
Main orchestrator for tracking operations
```python
async with RankTracker(domain, keywords, ...) as tracker:
    results = await tracker.check_all_keywords()
```

#### RankDatabase
SQLite database management
```python
db = RankDatabase("rank_tracker.db")
records = db.get_history(keyword, domain, engine)
```

#### ProxyRotator
Proxy rotation
```python
rotator = ProxyRotator(proxies)
proxy = rotator.get_proxy()
```

#### RateLimiter
Request rate limiting
```python
limiter = RateLimiter(min_delay=2.0, max_delay=5.0)
await limiter.wait()
```

### REST API Endpoints
```
POST   /api/rank-tracker/check               - Start async check
GET    /api/rank-tracker/check/{job_id}      - Get job status
POST   /api/rank-tracker/check-sync          - Synchronous check
GET    /api/rank-tracker/history/{domain}/{keyword}
GET    /api/rank-tracker/trend/{domain}/{keyword}
GET    /api/rank-tracker/alerts/{domain}
GET    /api/rank-tracker/summary/{domain}
```

## 📊 Database Schema

### rank_records table
Stores all ranking checks
```sql
keyword, domain, search_engine, position, url, title, snippet, timestamp
```

### rank_alerts table
Stores significant rank changes
```sql
keyword, domain, search_engine, previous_position, current_position, change, alert_level, timestamp
```

## ⚙️ Configuration

### Basic Configuration
```python
RankTracker(
    domain="example.com",
    keywords=["keyword1", "keyword2"],
    search_engines=[SearchEngine.GOOGLE],
    min_delay=2.0,
    max_delay=5.0
)
```

### With Proxies
```python
RankTracker(
    domain="example.com",
    keywords=["keyword1"],
    proxies=["http://proxy1:8080", "http://proxy2:8080"],
    min_delay=1.0,
    max_delay=2.0
)
```

### Multiple Engines
```python
RankTracker(
    domain="example.com",
    keywords=["keyword1"],
    search_engines=[
        SearchEngine.GOOGLE,
        SearchEngine.BING,
        SearchEngine.DUCKDUCKGO
    ]
)
```

## 📈 Performance Expectations

| Configuration | Speed | Keywords/Hour |
|---------------|-------|---------------|
| No proxy, 5-10s delay | Slow | 6-12 |
| No proxy, 2-5s delay | Medium | 12-30 |
| 3 proxies, 2-5s delay | Fast | 30-60 |
| 10 proxies, 1-2s delay | Very fast | 60-100 |

## 🔧 Troubleshooting Quick Links

| Problem | Solution |
|---------|----------|
| "Rate limited (429)" | [RANK_TRACKER_README.md](RANK_TRACKER_README.md#troubleshooting) |
| "CAPTCHA detected" | [RANK_TRACKER_README.md](RANK_TRACKER_README.md#captcha-handling) |
| "Connection timeout" | [RANK_TRACKER_README.md](RANK_TRACKER_README.md#troubleshooting) |
| "Module not found" | [setup_rank_tracker.py](setup_rank_tracker.py) --validate |
| Missing dependencies | `pip install aiohttp beautifulsoup4` |

## 📋 Common Tasks

### Start tracking a new domain
```bash
python setup_rank_tracker.py --domain newdomain.com
python rank_tracker.py check newdomain.com keyword1 keyword2
```

### View ranking trends
```bash
python rank_tracker.py history domain.com keyword --days 30
```

### Export to CSV
```python
import csv
db = RankDatabase()
records = db.get_history("keyword", "domain.com", "google", 30)
# Export to CSV (see RANK_TRACKER_INTEGRATION.md)
```

### Set up daily checks
```bash
# Cron
0 0 * * * python /opt/auditor/rank_tracker.py check domain.com keywords

# Windows Task Scheduler
schtasks /create /tn "RankTracker" /tr "python rank_tracker.py check domain.com keywords" /sc daily /st 00:00
```

### View recent alerts
```bash
python rank_tracker.py alerts domain.com --limit 20
```

## 🎯 Implementation Checklist

- [ ] Install dependencies
- [ ] Run setup wizard
- [ ] Test CLI with 5 keywords
- [ ] View ranking history
- [ ] Check API endpoints
- [ ] Set up daily schedule
- [ ] Configure proxies (optional)
- [ ] Set up alerts/notifications
- [ ] Deploy to production
- [ ] Monitor for 48 hours

## 📞 Support

1. **Check Documentation**: Start with RANK_TRACKER_QUICKREF.md
2. **Run Examples**: `python examples_rank_tracker.py`
3. **Validate Setup**: `python setup_rank_tracker.py --validate`
4. **Check Logs**: `tail -f rank_tracker.log`
5. **Review Troubleshooting**: RANK_TRACKER_README.md → Troubleshooting

## 📝 File Overview

| File | Lines | Purpose |
|------|-------|---------|
| rank_tracker.py | 1500+ | Main engine |
| rank_tracker_api.py | 250+ | FastAPI integration |
| examples_rank_tracker.py | 300+ | Usage examples |
| setup_rank_tracker.py | 250+ | Setup wizard |
| RANK_TRACKER_README.md | Comprehensive | Full documentation |
| RANK_TRACKER_INTEGRATION.md | Advanced | Integration guide |
| RANK_TRACKER_QUICKREF.md | Quick | Quick reference |
| RANK_TRACKER_SUMMARY.md | Overview | Implementation summary |
| DEPLOYMENT_CHECKLIST.md | Checklist | Production checklist |

**Total: 2000+ lines of production-ready code**

---

## 🚀 Next Steps

1. **Start with Quick Reference**: Open [RANK_TRACKER_QUICKREF.md](RANK_TRACKER_QUICKREF.md)
2. **Run Setup**: `python setup_rank_tracker.py`
3. **Test CLI**: `python rank_tracker.py check example.com keyword1`
4. **Read Full Docs**: [RANK_TRACKER_README.md](RANK_TRACKER_README.md)
5. **Integrate with API**: [RANK_TRACKER_INTEGRATION.md](RANK_TRACKER_INTEGRATION.md)
6. **Deploy**: Follow [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

**Happy Rank Tracking!** 🎉
