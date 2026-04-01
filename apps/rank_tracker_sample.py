"""
Rank Tracking Engine - Production-ready SEO rank tracking system

Features:
- Daily position checks for target keywords
- Historical data storage and trend analysis
- Multi-engine support (Google, Bing, DuckDuckGo)
- Rotating user agents and proxies
- Rate limiting and CAPTCHA detection
- Alerts for position changes
- CLI interface for command-line usage
"""

import asyncio
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
import time
import os
from pathlib import Path
from abc import ABC, abstractmethod
import re

import aiohttp
from bs4 import BeautifulSoup


# ──────────────────────────────────────────────────────────────────────────────
# Setup logging
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# ──────────────────────────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────────────────────────

class SearchEngine(str, Enum):
    """Supported search engines"""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"


class RankChangeAlertLevel(str, Enum):
    """Alert levels for rank changes"""
    CRITICAL = "critical"      # Lost top 10 position
    WARNING = "warning"        # Dropped 5+ positions
    INFO = "info"              # Position changed


@dataclass
class RankRecord:
    """Single rank record"""
    keyword: str
    domain: str
    search_engine: str
    position: Optional[int]
    url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    timestamp: str
    checked_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RankAlert:
    """Alert for significant rank changes"""
    keyword: str
    domain: str
    search_engine: str
    previous_position: Optional[int]
    current_position: Optional[int]
    change: int
    alert_level: str
    timestamp: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────────────
# User Agents and Proxies
# ──────────────────────────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class ProxyRotator:
    """Rotate through proxy list"""
    
    def __init__(self, proxies: Optional[List[str]] = None):
        """
        Initialize proxy rotator
        
        Args:
            proxies: List of proxy URLs (format: http://user:pass@host:port)
                    If None, no proxies are used
        """
        self.proxies = proxies or []
        self.current_index = 0
    
    def get_proxy(self) -> Optional[str]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def add_proxy(self, proxy: str):
        """Add proxy to rotation"""
        self.proxies.append(proxy)
    
    def clear_proxies(self):
        """Clear all proxies"""
        self.proxies.clear()
        self.current_index = 0


# ──────────────────────────────────────────────────────────────────────────────
# Search Engine Fetchers (Abstract)
# ──────────────────────────────────────────────────────────────────────────────

class SearchEngineFetcher(ABC):
    """Abstract base for search engine fetchers"""
    
    def __init__(self, session: aiohttp.ClientSession, proxy_rotator: ProxyRotator, rate_limiter: 'RateLimiter'):
        self.session = session
        self.proxy_rotator = proxy_rotator
        self.rate_limiter = rate_limiter
    
    @abstractmethod
    async def search(self, query: str, domain: str) -> Optional[RankRecord]:
        """
        Search for domain ranking for a query
        
        Returns RankRecord if found, None otherwise
        """
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with rotating user agent"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch page with error handling and CAPTCHA detection
        
        Returns HTML content or None if failed
        """
        proxy = self.proxy_rotator.get_proxy()
        
        try:
            await self.rate_limiter.wait()  # Rate limiting
            
            async with self.session.get(
                url,
                headers=self.get_headers(),
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30),
                ssl=False
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    
                    # Detect CAPTCHA
                    if self._detect_captcha(html):
                        logger.warning("CAPTCHA detected, waiting before retry...")
                        await asyncio.sleep(random.uniform(30, 60))
                        return None
                    
                    return html
                elif resp.status == 429:
                    logger.warning("Rate limited (429), backing off...")
                    await asyncio.sleep(random.uniform(10, 20))
                    return None
                elif resp.status in [403, 401]:
                    logger.warning(f"Access forbidden ({resp.status})")
                    return None
                else:
                    logger.warning(f"Unexpected status {resp.status}")
                    return None
        
        except asyncio.TimeoutError:
            logger.warning("Request timeout")
            return None
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return None
    
    def _detect_captcha(self, html: str) -> bool:
        """Detect CAPTCHA in response"""
        captcha_indicators = [
            "g-recaptcha",
            "captcha",
            "unusual traffic",
            "bot check",
            "security challenge",
            "please verify",
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in captcha_indicators)


class GoogleFetcher(SearchEngineFetcher):
    """Google search fetcher"""
    
    async def search(self, query: str, domain: str) -> Optional[RankRecord]:
        """Search Google for domain ranking"""
        search_url = f"https://www.google.com/search?q=site:{domain}+{query.replace(' ', '+')}"
        
        html = await self._fetch_page(search_url)
        if not html:
            return None
        
        return self._parse_results(html, query, domain)
    
    def _parse_results(self, html: str, query: str, domain: str) -> Optional[RankRecord]:
        """Parse Google search results"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all result divs
            results = soup.find_all('div', {'class': 'g'})
            
            for idx, result in enumerate(results, 1):
                # Extract URL
                link = result.find('a', href=True)
                if not link:
                    continue
                
                url = link['href']
                
                # Check if it's from the target domain
                if domain not in url:
                    continue
                
                # Extract title
                title_elem = result.find('h3')
                title = title_elem.text if title_elem else ""
                
                # Extract snippet
                snippet_elem = result.find('span', {'class': 's'})
                snippet = snippet_elem.text if snippet_elem else ""
                
                return RankRecord(
                    keyword=query,
                    domain=domain,
                    search_engine=SearchEngine.GOOGLE.value,
                    position=idx,
                    url=url,
                    title=title,
                    snippet=snippet,
                    timestamp=datetime.now().isoformat(),
                    checked_at=datetime.now().isoformat()
                )
            
            # Not found in results
            return RankRecord(
                keyword=query,
                domain=domain,
                search_engine=SearchEngine.GOOGLE.value,
                position=None,
                url=None,
                title=None,
                snippet=None,
                timestamp=datetime.now().isoformat(),
                checked_at=datetime.now().isoformat()
            )
        
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None


class BingFetcher(SearchEngineFetcher):
    """Bing search fetcher"""
    
    async def search(self, query: str, domain: str) -> Optional[RankRecord]:
        """Search Bing for domain ranking"""
        search_url = f"https://www.bing.com/search?q=site:{domain}+{query.replace(' ', '+')}"
        
        html = await self._fetch_page(search_url)
        if not html:
            return None
        
        return self._parse_results(html, query, domain)
    
    def _parse_results(self, html: str, query: str, domain: str) -> Optional[RankRecord]:
        """Parse Bing search results"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all result items
            results = soup.find_all('li', {'class': 'b_algo'})
            
            for idx, result in enumerate(results, 1):
                # Extract URL
                link = result.find('a', href=True)
                if not link:
                    continue
                
                url = link['href']
                
                # Check if it's from the target domain
                if domain not in url:
                    continue
                
                # Extract title
                title = link.text
                
                # Extract snippet
                snippet_elem = result.find('p')
                snippet = snippet_elem.text if snippet_elem else ""
                
                return RankRecord(
                    keyword=query,
                    domain=domain,
                    search_engine=SearchEngine.BING.value,
                    position=idx,
                    url=url,
                    title=title,
                    snippet=snippet,
                    timestamp=datetime.now().isoformat(),
                    checked_at=datetime.now().isoformat()
                )
            
            # Not found
            return RankRecord(
                keyword=query,
                domain=domain,
                search_engine=SearchEngine.BING.value,
                position=None,
                url=None,
                title=None,
                snippet=None,
                timestamp=datetime.now().isoformat(),
                checked_at=datetime.now().isoformat()
            )
        
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None


class DuckDuckGoFetcher(SearchEngineFetcher):
    """DuckDuckGo search fetcher"""
    
    async def search(self, query: str, domain: str) -> Optional[RankRecord]:
        """Search DuckDuckGo for domain ranking"""
        search_url = f"https://duckduckgo.com/search?q=site:{domain}+{query.replace(' ', '+')}"
        
        html = await self._fetch_page(search_url)
        if not html:
            return None
        
        return self._parse_results(html, query, domain)
    
    def _parse_results(self, html: str, query: str, domain: str) -> Optional[RankRecord]:
        """Parse DuckDuckGo search results"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all result items
            results = soup.find_all('article')
            
            for idx, result in enumerate(results, 1):
                # Extract URL
                link = result.find('a', {'data-testid': 'result-title-a'})
                if not link:
                    continue
                
                url = link.get('href', '')
                
                # Check if it's from the target domain
                if domain not in url:
                    continue
                
                # Extract title
                title = link.text
                
                # Extract snippet
                snippet_elem = result.find('span', {'data-testid': 'result-snippet'})
                snippet = snippet_elem.text if snippet_elem else ""
                
                return RankRecord(
                    keyword=query,
                    domain=domain,
                    search_engine=SearchEngine.DUCKDUCKGO.value,
                    position=idx,
                    url=url,
                    title=title,
                    snippet=snippet,
                    timestamp=datetime.now().isoformat(),
                    checked_at=datetime.now().isoformat()
                )
            
            # Not found
            return RankRecord(
                keyword=query,
                domain=domain,
                search_engine=SearchEngine.DUCKDUCKGO.value,
                position=None,
                url=None,
                title=None,
                snippet=None,
                timestamp=datetime.now().isoformat(),
                checked_at=datetime.now().isoformat()
            )
        
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None


# ──────────────────────────────────────────────────────────────────────────────
# Rate Limiter
# ──────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Rate limiter to prevent blocking"""
    
    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """
        Initialize rate limiter
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
    
    async def wait(self):
        """Wait before next request"""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        wait_time = max(0, delay - elapsed)
        
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()


# ──────────────────────────────────────────────────────────────────────────────
# Database Management
# ──────────────────────────────────────────────────────────────────────────────

class RankDatabase:
    """SQLite database for rank records and alerts"""
    
    def __init__(self, db_path: str = "rank_tracker.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Rank records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rank_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    position INTEGER,
                    url TEXT,
                    title TEXT,
                    snippet TEXT,
                    timestamp TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    UNIQUE(keyword, domain, search_engine, timestamp)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_keyword_domain 
                ON rank_records(keyword, domain)
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rank_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    previous_position INTEGER,
                    current_position INTEGER,
                    change INTEGER NOT NULL,
                    alert_level TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            conn.commit()
    
    def save_record(self, record: RankRecord) -> bool:
        """Save rank record to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO rank_records
                    (keyword, domain, search_engine, position, url, title, snippet, timestamp, checked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.keyword,
                    record.domain,
                    record.search_engine,
                    record.position,
                    record.url,
                    record.title,
                    record.snippet,
                    record.timestamp,
                    record.checked_at
                ))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug("Record already exists")
            return False
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False
    
    def save_alert(self, alert: RankAlert) -> bool:
        """Save rank alert to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO rank_alerts
                    (keyword, domain, search_engine, previous_position, current_position, change, alert_level, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert.keyword,
                    alert.domain,
                    alert.search_engine,
                    alert.previous_position,
                    alert.current_position,
                    alert.change,
                    alert.alert_level,
                    alert.timestamp
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False
    
    def get_latest_record(self, keyword: str, domain: str, search_engine: str) -> Optional[RankRecord]:
        """Get latest rank record for keyword"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT keyword, domain, search_engine, position, url, title, snippet, timestamp, checked_at
                    FROM rank_records
                    WHERE keyword = ? AND domain = ? AND search_engine = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (keyword, domain, search_engine))
                
                row = cursor.fetchone()
                if row:
                    return RankRecord(*row)
        
        except Exception as e:
            logger.error(f"Database error: {e}")
        
        return None
    
    def get_history(
        self,
        keyword: str,
        domain: str,
        search_engine: str,
        days: int = 30
    ) -> List[RankRecord]:
        """Get rank history for keyword"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT keyword, domain, search_engine, position, url, title, snippet, timestamp, checked_at
                    FROM rank_records
                    WHERE keyword = ? AND domain = ? AND search_engine = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                ''', (keyword, domain, search_engine, cutoff_date))
                
                rows = cursor.fetchall()
                return [RankRecord(*row) for row in rows]
        
        except Exception as e:
            logger.error(f"Database error: {e}")
        
        return []
    
    def get_alerts(self, domain: str, limit: int = 50) -> List[RankAlert]:
        """Get recent alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT keyword, domain, search_engine, previous_position, current_position, change, alert_level, timestamp
                    FROM rank_alerts
                    WHERE domain = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (domain, limit))
                
                rows = cursor.fetchall()
                return [RankAlert(*row) for row in rows]
        
        except Exception as e:
            logger.error(f"Database error: {e}")
        
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Main Rank Tracker
# ──────────────────────────────────────────────────────────────────────────────

class RankTracker:
    """Main rank tracking engine"""
    
    def __init__(
        self,
        domain: str,
        keywords: List[str],
        search_engines: Optional[List[SearchEngine]] = None,
        proxies: Optional[List[str]] = None,
        db_path: str = "rank_tracker.db",
        min_delay: float = 2.0,
        max_delay: float = 5.0
    ):
        """
        Initialize rank tracker
        
        Args:
            domain: Target domain to track
            keywords: List of keywords to track
            search_engines: List of search engines to check (default: all)
            proxies: List of proxy URLs for rotation
            db_path: Path to SQLite database
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
        """
        self.domain = domain
        self.keywords = keywords
        self.search_engines = search_engines or list(SearchEngine)
        self.db = RankDatabase(db_path)
        self.proxy_rotator = ProxyRotator(proxies)
        self.rate_limiter = RateLimiter(min_delay, max_delay)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_fetcher(self, search_engine: SearchEngine) -> SearchEngineFetcher:
        """Get fetcher for search engine"""
        fetchers = {
            SearchEngine.GOOGLE: GoogleFetcher,
            SearchEngine.BING: BingFetcher,
            SearchEngine.DUCKDUCKGO: DuckDuckGoFetcher,
        }
        
        fetcher_class = fetchers.get(search_engine)
        if not fetcher_class:
            raise ValueError(f"Unsupported search engine: {search_engine}")
        
        return fetcher_class(self.session, self.proxy_rotator, self.rate_limiter)
    
    async def check_keyword(
        self,
        keyword: str,
        search_engine: SearchEngine
    ) -> Tuple[RankRecord, Optional[RankAlert]]:
        """
        Check ranking for a keyword
        
        Returns: (current_record, alert_if_any)
        """
        fetcher = self._get_fetcher(search_engine)
        
        logger.info(f"Checking: {keyword} on {search_engine.value}")
        current_record = await fetcher.search(keyword, self.domain)
        
        if not current_record:
            return None, None
        
        # Save to database
        self.db.save_record(current_record)
        
        # Check for alerts
        alert = self._check_for_alert(keyword, search_engine, current_record)
        if alert:
            self.db.save_alert(alert)
        
        return current_record, alert
    
    def _check_for_alert(
        self,
        keyword: str,
        search_engine: SearchEngine,
        current_record: RankRecord
    ) -> Optional[RankAlert]:
        """Check if rank change warrants an alert"""
        previous_record = self.db.get_latest_record(keyword, self.domain, search_engine.value)
        
        if not previous_record or previous_record.position is None:
            return None
        
        if current_record.position is None:
            # Fell out of results
            change = 999  # Large number to indicate dropped out
            alert_level = RankChangeAlertLevel.CRITICAL.value
        else:
            change = current_record.position - previous_record.position
            
            # Determine alert level
            if previous_record.position <= 10 and current_record.position > 10:
                # Lost top 10
                alert_level = RankChangeAlertLevel.CRITICAL.value
            elif change >= 5:
                # Dropped 5+ positions
                alert_level = RankChangeAlertLevel.WARNING.value
            elif change <= -5:
                # Gained 5+ positions
                alert_level = RankChangeAlertLevel.INFO.value
            else:
                return None  # No alert
        
        if change == 0:
            return None  # No change
        
        return RankAlert(
            keyword=keyword,
            domain=self.domain,
            search_engine=search_engine.value,
            previous_position=previous_record.position,
            current_position=current_record.position,
            change=change,
            alert_level=alert_level,
            timestamp=datetime.now().isoformat()
        )
    
    async def check_all_keywords(
        self,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Check all keywords across all search engines
        
        Returns: Summary of results and alerts
        """
        results = {
            "domain": self.domain,
            "timestamp": datetime.now().isoformat(),
            "records": [],
            "alerts": [],
            "summary": {
                "total_keywords": len(self.keywords),
                "total_checks": len(self.keywords) * len(self.search_engines),
                "successful_checks": 0,
                "top_10_count": 0,
                "top_50_count": 0,
                "unranked_count": 0,
            }
        }
        
        total_checks = len(self.keywords) * len(self.search_engines)
        check_count = 0
        
        for keyword in self.keywords:
            for search_engine in self.search_engines:
                check_count += 1
                
                if progress_callback:
                    progress = int((check_count / total_checks) * 100)
                    await progress_callback(progress, f"Checking {keyword} ({search_engine.value})")
                
                record, alert = await self.check_keyword(keyword, search_engine)
                
                if record:
                    results["records"].append(record.to_dict())
                    results["summary"]["successful_checks"] += 1
                    
                    if record.position:
                        if record.position <= 10:
                            results["summary"]["top_10_count"] += 1
                        if record.position <= 50:
                            results["summary"]["top_50_count"] += 1
                    else:
                        results["summary"]["unranked_count"] += 1
                    
                    if alert:
                        results["alerts"].append(alert.to_dict())
        
        return results
    
    def get_ranking_chart(
        self,
        keyword: str,
        search_engine: SearchEngine,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get historical ranking data for charting"""
        history = self.db.get_history(keyword, self.domain, search_engine.value, days)
        
        if not history:
            return {"keyword": keyword, "data": []}
        
        chart_data = {
            "keyword": keyword,
            "search_engine": search_engine.value,
            "domain": self.domain,
            "data": [
                {
                    "date": record.timestamp[:10],
                    "position": record.position or 0,
                    "url": record.url,
                    "title": record.title,
                }
                for record in history
            ]
        }
        
        return chart_data
    
    def get_trend_analysis(self, keyword: str, search_engine: SearchEngine, days: int = 30) -> Dict[str, Any]:
        """Analyze ranking trends"""
        history = self.db.get_history(keyword, self.domain, search_engine.value, days)
        
        if len(history) < 2:
            return {"keyword": keyword, "trend": "insufficient_data"}
        
        positions = [r.position for r in history if r.position]
        if not positions:
            return {"keyword": keyword, "trend": "unranked"}
        
        first_position = positions[0]
        last_position = positions[-1]
        avg_position = sum(positions) / len(positions)
        best_position = min(positions)
        worst_position = max(positions)
        
        # Determine trend
        if last_position is None:
            trend = "dropped_out"
        elif last_position < first_position - 2:
            trend = "improving"
        elif last_position > first_position + 2:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "keyword": keyword,
            "search_engine": search_engine.value,
            "trend": trend,
            "first_position": first_position,
            "last_position": last_position,
            "best_position": best_position,
            "worst_position": worst_position,
            "average_position": round(avg_position, 1),
            "data_points": len(positions),
        }


# ──────────────────────────────────────────────────────────────────────────────
# CLI Interface
# ──────────────────────────────────────────────────────────────────────────────

async def cli_check_keywords(
    domain: str,
    keywords: List[str],
    search_engines: Optional[List[str]] = None,
    proxies: Optional[List[str]] = None,
    db_path: str = "rank_tracker.db"
):
    """CLI: Check keywords"""
    engines = [SearchEngine(e) for e in (search_engines or ["google", "bing"])]
    
    async with RankTracker(domain, keywords, engines, proxies, db_path) as tracker:
        results = await tracker.check_all_keywords()
        
        print(f"\n{'='*60}")
        print(f"RANK TRACKING RESULTS - {domain}")
        print(f"{'='*60}\n")
        
        # Print summary
        summary = results["summary"]
        print(f"Total Keywords: {summary['total_keywords']}")
        print(f"Successful Checks: {summary['successful_checks']}/{summary['total_checks']}")
        print(f"Top 10 Rankings: {summary['top_10_count']}")
        print(f"Top 50 Rankings: {summary['top_50_count']}")
        print(f"Unranked: {summary['unranked_count']}\n")
        
        # Print records
        if results["records"]:
            print(f"{'Keyword':<30} {'Engine':<12} {'Position':<10} {'URL':<40}")
            print(f"{'-'*92}")
            for record in sorted(results["records"], key=lambda x: (x["keyword"], x["search_engine"]))[:20]:
                pos = record["position"] if record["position"] else "N/A"
                url = (record["url"][:37] + "...") if record["url"] else "N/A"
                print(f"{record['keyword']:<30} {record['search_engine']:<12} {str(pos):<10} {url:<40}")
        
        # Print alerts
        if results["alerts"]:
            print(f"\n{'='*60}")
            print("ALERTS")
            print(f"{'='*60}\n")
            
            for alert in results["alerts"]:
                level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
                emoji = level_emoji.get(alert["alert_level"], "")
                change = alert["change"]
                change_str = f"↓{change}" if change > 0 else f"↑{abs(change)}"
                
                print(f"{emoji} {alert['keyword']} ({alert['search_engine']})")
                print(f"   {alert['previous_position']} → {alert['current_position']} {change_str}")
                print()
        
        return results


async def cli_show_history(
    domain: str,
    keyword: str,
    search_engine: str = "google",
    days: int = 30,
    db_path: str = "rank_tracker.db"
):
    """CLI: Show ranking history"""
    async with RankTracker(domain, [keyword], db_path=db_path) as tracker:
        chart_data = tracker.get_ranking_chart(keyword, SearchEngine(search_engine), days)
        trend_analysis = tracker.get_trend_analysis(keyword, SearchEngine(search_engine), days)
        
        print(f"\n{'='*60}")
        print(f"RANKING HISTORY - {keyword}")
        print(f"{'='*60}\n")
        
        print(f"Trend: {trend_analysis['trend'].upper()}")
        print(f"Best Position: #{trend_analysis['best_position']}")
        print(f"Average Position: #{trend_analysis['average_position']}")
        print(f"Data Points: {trend_analysis['data_points']}\n")
        
        if chart_data["data"]:
            print(f"{'Date':<15} {'Position':<12} {'Title':<50}")
            print(f"{'-'*77}")
            for entry in chart_data["data"][-10:]:  # Last 10 records
                title = (entry["title"][:47] + "...") if entry["title"] else "N/A"
                pos = entry["position"] if entry["position"] else "N/A"
                print(f"{entry['date']:<15} {str(pos):<12} {title:<50}")


async def cli_show_alerts(
    domain: str,
    limit: int = 20,
    db_path: str = "rank_tracker.db"
):
    """CLI: Show recent alerts"""
    db = RankDatabase(db_path)
    alerts = db.get_alerts(domain, limit)
    
    print(f"\n{'='*60}")
    print(f"RECENT ALERTS - {domain}")
    print(f"{'='*60}\n")
    
    if not alerts:
        print("No alerts found.")
        return
    
    for alert in alerts:
        level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        emoji = level_emoji.get(alert.alert_level, "")
        change = alert.change
        change_str = f"↓{change}" if change > 0 else f"↑{abs(change)}"
        
        print(f"{emoji} {alert.keyword} ({alert.search_engine})")
        print(f"   {alert.previous_position or 'N/A'} → {alert.current_position or 'N/A'} {change_str}")
        print(f"   {alert.timestamp[:10]}\n")


# ──────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     import argparse
    
#     parser = argparse.ArgumentParser(description="SEO Rank Tracking Engine")
#     subparsers = parser.add_subparsers(dest="command", help="Commands")
    
#     # Check command
#     check_parser = subparsers.add_parser("check", help="Check keyword rankings")
#     check_parser.add_argument("domain", help="Target domain")
#     check_parser.add_argument("keywords", nargs="+", help="Keywords to track")
#     check_parser.add_argument("--engines", nargs="+", default=["google"], help="Search engines (google, bing, duckduckgo)")
#     check_parser.add_argument("--proxies", nargs="+", help="Proxy URLs")
#     check_parser.add_argument("--db", default="rank_tracker.db", help="Database path")
    
#     # History command
#     history_parser = subparsers.add_parser("history", help="Show ranking history")
#     history_parser.add_argument("domain", help="Target domain")
#     history_parser.add_argument("keyword", help="Keyword")
#     history_parser.add_argument("--engine", default="google", help="Search engine")
#     history_parser.add_argument("--days", type=int, default=30, help="Days of history")
#     history_parser.add_argument("--db", default="rank_tracker.db", help="Database path")
    
#     # Alerts command
#     alerts_parser = subparsers.add_parser("alerts", help="Show recent alerts")
#     alerts_parser.add_argument("domain", help="Target domain")
#     alerts_parser.add_argument("--limit", type=int, default=20, help="Limit alerts")
#     alerts_parser.add_argument("--db", default="rank_tracker.db", help="Database path")
    
#     args = parser.parse_args()
    
#     if args.command == "check":
#         asyncio.run(cli_check_keywords(
#             args.domain,
#             args.keywords,
#             args.engines,
#             args.proxies,
#             args.db
#         ))
#     elif args.command == "history":
#         asyncio.run(cli_show_history(
#             args.domain,
#             args.keyword,
#             args.engine,
#             args.days,
#             args.db
#         ))
#     elif args.command == "alerts":
#         asyncio.run(cli_show_alerts(
#             args.domain,
#             args.limit,
#             args.db
#         ))
#     else:
#         parser.print_help()


fetcher = GoogleFetcher()
# fetcher_class(self.session, self.proxy_rotator, self.rate_limiter)

# loop = asyncio.get_event_loop()
# results = loop.run_until_complete(fetcher.search('rstipower','https://rstipower.com'))
# print(results)