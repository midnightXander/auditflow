import asyncio
import aiohttp
from aiohttp_socks import SocksConnector
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv

load_dotenv()

# User Agent rotation pool
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# Shadowsocks SOCKS5 proxy configuration
SOCKS5_PROXY = os.getenv("SOCKS5_PROXY", "socks5://127.0.0.1:1080")
USE_SOCKS5 = os.getenv("USE_SOCKS5", "true").lower() == "true"

# Fallback HTTP proxies (optional)
HTTP_PROXY_LIST = os.getenv("HTTP_PROXY_LIST", "").split(",") if os.getenv("HTTP_PROXY_LIST") else []


class ProxyRotator:
    """Manage proxy rotation (SOCKS5 + HTTP fallback)"""
    
    def __init__(self, socks5_url: str = SOCKS5_PROXY, http_proxies: List[str] = None):
        self.socks5_url = socks5_url
        self.http_proxies = http_proxies or []
        self.current_proxy_index = 0
    
    def get_next_proxy(self) -> Optional[str]:
        """Rotate between HTTP proxies (SOCKS5 is primary)"""
        if not self.http_proxies:
            return None
        proxy = self.http_proxies[self.current_proxy_index % len(self.http_proxies)]
        self.current_proxy_index += 1
        return proxy
    
    def get_socks5_connector(self) -> SocksConnector:
        """Create SOCKS5 connector for aiohttp"""
        return SocksConnector.from_url(self.socks5_url, ssl=False)


class SearchEngine:
    """Base class for search engine scrapers"""
    
    def __init__(self, name: str):
        self.name = name
        self.results_per_page = 10
    
    def get_search_url(self, keyword: str, page: int = 0) -> str:
        raise NotImplementedError
    
    def parse_results(self, html: str) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    def _get_random_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
        }


class GoogleScraper(SearchEngine):
    def __init__(self):
        super().__init__("google")
    
    def get_search_url(self, keyword: str, page: int = 0) -> str:
        start = page * self.results_per_page
        return f"https://www.google.com/search?q={quote_plus(keyword)}&start={start}&num={self.results_per_page}&hl=en&gl=us"
    
    def parse_results(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        result_divs = soup.select('div.g') or soup.select('div.tF2Cxc')
        
        position = 1
        for div in result_divs:
            try:
                link = div.select_one('a')
                if not link or not link.get('href'):
                    continue
                url = link['href']
                if url.startswith('/search') or 'google.com' in url:
                    continue
                title = div.select_one('h3').get_text() if div.select_one('h3') else ""
                results.append({
                    'position': position,
                    'url': url,
                    'title': title,
                    'domain': urlparse(url).netloc
                })
                position += 1
            except:
                continue
        return results


class BingScraper(SearchEngine):
    def __init__(self):
        super().__init__("bing")
    
    def get_search_url(self, keyword: str, page: int = 0) -> str:
        first = page * self.results_per_page + 1
        return f"https://www.bing.com/search?q={quote_plus(keyword)}&first={first}"
    
    def parse_results(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        position = 1
        for item in soup.select('li.b_algo'):
            try:
                link = item.select_one('h2 a')
                if not link:
                    continue
                results.append({
                    'position': position,
                    'url': link['href'],
                    'title': link.get_text(),
                    'domain': urlparse(link['href']).netloc
                })
                position += 1
            except:
                continue
        return results


class RateLimiter:
    """Rate limiting to avoid hitting servers too hard"""
    
    def __init__(self, requests_per_second: float = 0.5):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
    
    async def wait(self):
        """Wait if necessary to respect rate limit"""
        elapsed = asyncio.get_event_loop().time() - self.last_request_time
        wait_time = (1.0 / self.requests_per_second) - elapsed
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self.last_request_time = asyncio.get_event_loop().time()


class RankTracker:
    def __init__(self, domain: str, use_socks5: bool = USE_SOCKS5):
        self.domain = domain
        self.engines = {'google': GoogleScraper(), 'bing': BingScraper()}
        self.max_retries = 3
        self.use_socks5 = use_socks5
        self.proxy_rotator = ProxyRotator(SOCKS5_PROXY, HTTP_PROXY_LIST)
        self.rate_limiter = RateLimiter(requests_per_second=0.33)  # ~3 sec between requests
    
    async def check_rankings(self, keywords: List[str], engines: List[str] = ['google'], progress_callback=None):
        results = {}
        total = len(keywords) * len(engines)
        completed = 0
        
        for keyword in keywords:
            results[keyword] = {}
            for engine_name in engines:
                if engine_name not in self.engines:
                    continue
                engine = self.engines[engine_name]
                ranking_data = await self._check_keyword_ranking(keyword, engine, 100)
                results[keyword][engine_name] = ranking_data
                completed += 1
                if progress_callback:
                    await progress_callback((completed / total) * 100, f"Checked {keyword} on {engine_name}")
                
                # Random delay between requests
                await asyncio.sleep(random.uniform(2, 5))
        
        return {
            'domain': self.domain,
            'checked_at': datetime.utcnow().isoformat(),
            'results': results,
            'summary': self._generate_summary(results)
        }
    
    async def _check_keyword_ranking(self, keyword: str, engine: SearchEngine, max_position: int = 100):
        max_pages = (max_position + engine.results_per_page - 1) // engine.results_per_page
        for page in range(max_pages):
            try:
                html = await self._fetch_serp(engine, keyword, page)
                if not html:
                    continue
                results = engine.parse_results(html)
                for result in results:
                    if self.domain.replace('https://', '').replace('http://', '').replace('www.', '') in result['domain']:
                        return {
                            'found': True,
                            'position': page * engine.results_per_page + result['position'],
                            'url': result['url'],
                            'title': result['title']
                        }
            except Exception as e:
                print(f"[ERROR] Keyword check error: {e}")
        return {'found': False, 'position': None, 'url': None, 'title': None}
    
    async def _fetch_serp(self, engine: SearchEngine, keyword: str, page: int):
        for attempt in range(self.max_retries):
            try:
                await self.rate_limiter.wait()
                
                url = engine.get_search_url(keyword, page)
                headers = engine._get_random_headers()
                
                print(f"[FETCH] {engine.name.upper()} - {keyword} (page {page + 1}, attempt {attempt + 1})")
                
                # Use SOCKS5 connector if enabled
                if self.use_socks5:
                    connector = self.proxy_rotator.get_socks5_connector()
                    timeout = aiohttp.ClientTimeout(total=30)
                    print("Using SOCKS5 proxy:", self.proxy_rotator.socks5_url)
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        async with session.get(url, headers=headers, ssl=False) as response:
                            print(f"[RESPONSE] Status: {response.status}")
                            
                            if response.status == 429:
                                print("[RATE_LIMITED] Waiting 60 seconds...")
                                await asyncio.sleep(60)
                                continue
                            
                            if response.status != 200:
                                print(f"[ERROR] Status {response.status}")
                                continue
                            
                            html = await response.text()
                            
                            if 'captcha' in html.lower() or 'challenge' in html.lower():
                                print("[CAPTCHA] Detected, waiting 120 seconds...")
                                await asyncio.sleep(120)
                                continue
                            
                            return html
                
                # Fallback: HTTP proxy without SOCKS5
                else:
                    http_proxy = self.proxy_rotator.get_next_proxy()
                    timeout = aiohttp.ClientTimeout(total=30)
                    
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, headers=headers, proxy=http_proxy, ssl=False) as response:
                            print(f"[RESPONSE] Status: {response.status}")
                            
                            if response.status == 429:
                                print("[RATE_LIMITED] Waiting 60 seconds...")
                                await asyncio.sleep(60)
                                continue
                            
                            if response.status != 200:
                                continue
                            
                            html = await response.text()
                            
                            if 'captcha' in html.lower():
                                print("[CAPTCHA] Detected, waiting 120 seconds...")
                                await asyncio.sleep(120)
                                continue
                            
                            return html
            
            except Exception as e:
                print(f"[EXCEPTION] Attempt {attempt + 1}: {str(e)}")
                await asyncio.sleep(2 * (attempt + 1))
        
        print(f"[FAILED] Could not fetch SERP after {self.max_retries} attempts")
        return None
    
    def _generate_summary(self, results: Dict):
        total = len(results)
        found = 0
        positions = []
        
        for kw, engines in results.items():
            for eng, data in engines.items():
                if data.get('found'):
                    found += 1
                    if data.get('position'):
                        positions.append(data['position'])
        
        return {
            'total_keywords': total,
            'found_count': found,
            'found_percentage': round((found / (total * len(self.engines)) * 100), 1) if total > 0 else 0,
            'avg_position': round(sum(positions) / len(positions), 1) if positions else None,
            'best_position': min(positions) if positions else None,
            'worst_position': max(positions) if positions else None,
        }


async def track_rankings(domain: str, keywords: List[str], engines: List[str] = ['google'], progress_callback=None):
    tracker = RankTracker(domain)
    return await tracker.check_rankings(keywords, engines, progress_callback)


# Example usage
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    
    # Test with your domain
    results = loop.run_until_complete(
        track_rankings(
            'nike.com',
            ['nike shoes', 'running shoes', 'nike sportswear'],
            engines=['google', 'bing']
        )
    )
    
    import json
    print(json.dumps(results, indent=2))