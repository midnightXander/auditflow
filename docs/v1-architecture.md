# Website Auditor - Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Command Line│  │  Web Browser │  │  API Client  │         │
│  │              │  │ (index.html) │  │  (curl/app)  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    auditor.py                            │  │
│  │            (Direct execution for CLI)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     api.py                               │  │
│  │              FastAPI REST Server                         │  │
│  │                                                          │  │
│  │  Endpoints:                                              │  │
│  │  • POST   /api/audit       → Start audit                │  │
│  │  • GET    /api/audit/{id}  → Get status/results         │  │
│  │  • GET    /api/audits      → List all audits            │  │
│  │  • DELETE /api/audit/{id}  → Delete audit               │  │
│  │                                                          │  │
│  │  Features:                                               │  │
│  │  • Background task processing                            │  │
│  │  • In-memory job storage                                │  │
│  │  • CORS enabled                                         │  │
│  │  • Auto-generated docs (/docs)                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AUDIT ENGINE (Core Logic)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          WebsiteAuditor Class                           │   │
│  │                                                         │   │
│  │  Main Methods:                                          │   │
│  │  • run_full_audit()          → Orchestrates all checks │   │
│  │  • run_lighthouse_audit()    → Performance metrics     │   │
│  │  • audit_technical_seo()     → SEO elements            │   │
│  │  • audit_security()          → Security checks         │   │
│  │  • _calculate_overall_score()→ Scoring algorithm       │   │
│  │  • print_summary()           → Console output          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES & TOOLS                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Playwright  │  │ BeautifulSoup│  │   Requests   │         │
│  │              │  │              │  │              │         │
│  │  • Launch    │  │  • Parse HTML│  │  • HTTP GET  │         │
│  │    Chromium  │  │  • Extract   │  │  • Headers   │         │
│  │  • Navigate  │  │    meta tags │  │  • Status    │         │
│  │  • Execute   │  │  • Find      │  │    codes     │         │
│  │    JavaScript│  │    elements  │  │              │         │
│  │  • Collect   │  │              │  │              │         │
│  │    metrics   │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TARGET WEBSITE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  https://example.com                                            │
│                                                                 │
│  Data Collected:                                                │
│  • HTML content                                                 │
│  • HTTP headers                                                 │
│  • Performance metrics                                          │
│  • Resource loading times                                       │
│  • Core Web Vitals                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. User Request
   │
   ├─ CLI:  python auditor.py <url>
   │        └─> Direct execution → Results to console + JSON file
   │
   └─ API:  POST /api/audit {"url": "..."}
            └─> Job created → Background task → Poll for results

2. Audit Execution Flow
   
   Start
    │
    ├─> 1. URL Normalization
    │    (Ensure https:// prefix)
    │
    ├─> 2. Playwright Audit
    │    │
    │    ├─> Launch Browser
    │    ├─> Navigate to URL
    │    ├─> Collect Performance Metrics
    │    │   • Navigation timing
    │    │   • Paint timing
    │    │   • Core Web Vitals (LCP, FID, CLS)
    │    │   • Resource counts
    │    ├─> Check Mobile Viewport
    │    └─> Close Browser
    │
    ├─> 3. Technical SEO Audit
    │    │
    │    ├─> Fetch HTML (requests.get)
    │    ├─> Parse with BeautifulSoup
    │    ├─> Extract Meta Tags
    │    │   • Title
    │    │   • Description
    │    │   • Canonical
    │    ├─> Analyze Headings (H1-H6)
    │    ├─> Check robots.txt
    │    └─> Check sitemap.xml
    │
    ├─> 4. Security Audit
    │    │
    │    ├─> Verify HTTPS
    │    ├─> Check Security Headers
    │    │   • Strict-Transport-Security
    │    │   • X-Frame-Options
    │    │   • X-Content-Type-Options
    │    │   • Content-Security-Policy
    │    └─> Validate SSL
    │
    ├─> 5. Score Calculation
    │    │
    │    ├─> Performance Score (0-100)
    │    ├─> SEO Score (0-100)
    │    ├─> Security Score (0-100)
    │    └─> Overall Score (average)
    │
    └─> 6. Return Results
         │
         ├─> JSON object with all data
         ├─> Console summary (if CLI)
         └─> Store in job results (if API)
```

## Storage Architecture (Current)

```
In-Memory Storage (Python Dictionary)
┌─────────────────────────────────────┐
│  audit_results = {                  │
│    "job-id-1": {                    │
│      "job_id": "...",               │
│      "url": "...",                  │
│      "status": "completed",         │
│      "progress": 100,               │
│      "results": { ... },            │
│      "created_at": "...",           │
│      "completed_at": "..."          │
│    },                               │
│    "job-id-2": { ... }              │
│  }                                  │
└─────────────────────────────────────┘

⚠️  Note: Data is lost on server restart
    For production, use PostgreSQL/Redis
```

## Recommended Production Architecture

```
┌──────────────┐
│   Frontend   │ (React/Vue/index.html)
│  (Vercel)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Load        │
│  Balancer    │
└──────┬───────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  API     │  │  API     │  │  API     │
│ Server 1 │  │ Server 2 │  │ Server 3 │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┴─────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  ┌─────────────┐    ┌──────────────┐
  │ PostgreSQL  │    │ Redis Queue  │
  │  (Jobs &    │    │  (Job Queue  │
  │   Results)  │    │   & Cache)   │
  └─────────────┘    └──────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │ Background       │
                   │ Workers (Celery) │
                   │  • Worker 1      │
                   │  • Worker 2      │
                   │  • Worker 3      │
                   └──────────────────┘
```

## Component Dependencies

```
auditor.py
├── playwright (Browser automation)
├── requests (HTTP client)
├── beautifulsoup4 (HTML parsing)
└── asyncio (Async operations)

api.py
├── fastapi (Web framework)
├── uvicorn (ASGI server)
├── pydantic (Data validation)
└── auditor.py (Core engine)

index.html
├── Fetch API (HTTP requests)
└── Vanilla JavaScript
```

## Security Considerations

```
Current Implementation:
✓ CORS enabled
✓ Input validation (Pydantic)
✗ No authentication
✗ No rate limiting
✗ No input sanitization for XSS

Production Requirements:
□ Add API key authentication
□ Implement rate limiting (per IP/user)
□ Add request size limits
□ Sanitize all inputs
□ Use HTTPS only
□ Add CSRF protection
□ Implement logging/monitoring
□ Add DDoS protection
```