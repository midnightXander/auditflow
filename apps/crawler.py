"""
Deep Site Crawler - Crawls entire websites (up to 500 pages)
Identifies: duplicate titles, thin content, orphan pages, broken links, missing meta
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from typing import Set, Dict, List, Optional
from datetime import datetime
import hashlib
import time


class SiteCrawler:
    """Asynchronous website crawler with comprehensive analysis"""
    
    def __init__(self, start_url: str, max_pages: int = 500, max_concurrent: int = 10):
        self.start_url = start_url
        self.max_pages = max_pages
        self.max_concurrent = max_concurrent
        
        parsed = urlparse(start_url)
        self.domain = parsed.netloc
        self.scheme = parsed.scheme
        
        self.visited: Set[str] = set()
        self.to_visit: Set[str] = {start_url}
        self.pages: List[Dict] = []
        self.internal_links: List[Dict] = []
        self.external_links: List[Dict] = []
        
        self.start_time = None
        self.end_time = None
        
    async def crawl(self, progress_callback=None):
        """Main crawl loop with progress updates"""
        self.start_time = time.time()
        
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            while self.to_visit and len(self.visited) < self.max_pages:
                # Get batch of URLs
                batch_size = min(self.max_concurrent, len(self.to_visit))
                batch = list(self.to_visit)[:batch_size]
                self.to_visit -= set(batch)
                
                # Crawl batch concurrently
                tasks = [self.crawl_page(session, url) for url in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Progress update
                if progress_callback:
                    progress = len(self.visited) / self.max_pages * 100
                    await progress_callback(min(progress, 100))
        
        self.end_time = time.time()
        
        # Final analysis
        return self.analyze_site()
    
    async def crawl_page(self, session: aiohttp.ClientSession, url: str):
        """Crawl a single page and extract data"""
        if url in self.visited:
            return
        
        self.visited.add(url)
        
        try:
            start_load = time.time()
            
            async with session.get(url, allow_redirects=True) as response:
                load_time = (time.time() - start_load) * 1000  # ms
                
                # Only process HTML
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    return
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract page data
                page_data = {
                    "url": str(response.url),  # Final URL after redirects
                    "original_url": url,
                    "status_code": response.status,
                    "title": self._extract_title(soup),
                    "meta_description": self._get_meta(soup, 'description'),
                    "meta_keywords": self._get_meta(soup, 'keywords'),
                    "canonical": self._get_canonical(soup),
                    "h1": [h.get_text(strip=True) for h in soup.find_all('h1')],
                    "h2": [h.get_text(strip=True) for h in soup.find_all('h2')],
                    "word_count": self._count_words(soup),
                    "images": self._analyze_images(soup),
                    "internal_links_count": 0,
                    "external_links_count": 0,
                    "load_time_ms": round(load_time, 2),
                    "size_kb": len(html) / 1024,
                    "content_hash": hashlib.md5(soup.get_text().encode()).hexdigest(),
                }
                
                self.pages.append(page_data)
                
                # Extract and process links
                await self._extract_links(soup, url, page_data)
                
        except asyncio.TimeoutError:
            self.pages.append({
                "url": url,
                "status_code": 0,
                "error": "timeout",
                "title": "",
            })
        except Exception as e:
            self.pages.append({
                "url": url,
                "status_code": 0,
                "error": str(e)[:400],
                "title": "",
            })
    
    async def _extract_links(self, soup: BeautifulSoup, current_url: str, page_data: Dict):
        """Extract and categorize all links from the page"""
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(current_url, href)
            # Remove fragment
            absolute_url, _ = urldefrag(absolute_url)
            
            anchor_text = link.get_text(strip=True)[:100]
            
            if self._is_same_domain(absolute_url):
                page_data['internal_links_count'] += 1
                self.internal_links.append({
                    "from": current_url,
                    "to": absolute_url,
                    "anchor": anchor_text,
                })
                
                # Add to crawl queue
                if absolute_url not in self.visited and absolute_url not in self.to_visit:
                    self.to_visit.add(absolute_url)
            else:
                page_data['external_links_count'] += 1
                self.external_links.append({
                    "from": current_url,
                    "to": absolute_url,
                    "anchor": anchor_text,
                })
    
    def analyze_site(self) -> Dict:
        """Post-crawl analysis - find all issues"""
        crawl_duration = self.end_time - self.start_time if self.end_time else 0
        
        return {
            "summary": {
                "start_url": self.start_url,
                "domain": self.domain,
                "total_pages_crawled": len(self.pages),
                "total_internal_links": len(self.internal_links),
                "total_external_links": len(self.external_links),
                "unique_external_domains": len(set(urlparse(l['to']).netloc for l in self.external_links)),
                "avg_word_count": round(sum(p.get('word_count', 0) for p in self.pages) / max(len(self.pages), 1)),
                "avg_load_time_ms": round(sum(p.get('load_time_ms', 0) for p in self.pages) / max(len(self.pages), 1), 2),
                "crawl_duration_sec": round(crawl_duration, 2),
                "crawl_date": datetime.now().isoformat(),
            },
            "issues": {
                "duplicate_titles": self._find_duplicate_titles(),
                "duplicate_content": self._find_duplicate_content(),
                "thin_content": self._find_thin_content(),
                "orphan_pages": self._find_orphan_pages(),
                "broken_pages": self._find_broken_pages(),
                "missing_meta_description": self._find_missing_meta(),
                "missing_h1": self._find_missing_h1(),
                "multiple_h1": self._find_multiple_h1(),
                "slow_pages": self._find_slow_pages(),
                "large_pages": self._find_large_pages(),
            },
            "site_structure": self._build_site_tree(),
            "top_pages": self._get_top_pages(),
            "pages": self.pages,
        }
    
    # ──────────────────────────────────────────────────────────────────────
    # Issue detection methods
    # ──────────────────────────────────────────────────────────────────────
    
    def _find_duplicate_titles(self) -> Dict[str, List[str]]:
        """Find pages with identical titles"""
        titles = {}
        for page in self.pages:
            title = page.get('title', '').strip()
            if title:
                if title in titles:
                    titles[title].append(page['url'])
                else:
                    titles[title] = [page['url']]
        
        return {k: v for k, v in titles.items() if len(v) > 1}
    
    def _find_duplicate_content(self) -> List[Dict]:
        """Find pages with identical content (same hash)"""
        hashes = {}
        for page in self.pages:
            content_hash = page.get('content_hash')
            if content_hash:
                if content_hash in hashes:
                    hashes[content_hash].append(page['url'])
                else:
                    hashes[content_hash] = [page['url']]
        
        duplicates = []
        for urls in hashes.values():
            if len(urls) > 1:
                duplicates.append({"urls": urls, "count": len(urls)})
        
        return duplicates
    
    def _find_thin_content(self) -> List[Dict]:
        """Pages with < 300 words"""
        return [
            {"url": p['url'], "word_count": p.get('word_count', 0)}
            for p in self.pages
            if p.get('word_count', 0) < 300 and p.get('status_code') == 200
        ]
    
    def _find_orphan_pages(self) -> List[Dict]:
        """Pages with no internal links pointing to them"""
        linked_urls = {link['to'] for link in self.internal_links}
        all_urls = {p['url'] for p in self.pages}
        orphan_urls = all_urls - linked_urls - {self.start_url}
        
        return [
            {"url": p['url'], "word_count": p.get('word_count', 0)}
            for p in self.pages
            if p['url'] in orphan_urls
        ]
    
    def _find_broken_pages(self) -> List[Dict]:
        """Pages returning 4xx or 5xx status codes"""
        return [
            {"url": p['url'], "status_code": p['status_code'], "error": p.get('error')}
            for p in self.pages
            if p.get('status_code', 0) >= 400
        ]
    
    def _find_missing_meta(self) -> List[str]:
        """Pages without meta description"""
        return [
            p['url']
            for p in self.pages
            if not p.get('meta_description') and p.get('status_code') == 200
        ]
    
    def _find_missing_h1(self) -> List[str]:
        """Pages without H1 tag"""
        return [
            p['url']
            for p in self.pages
            if not p.get('h1') and p.get('status_code') == 200
        ]
    
    def _find_multiple_h1(self) -> List[Dict]:
        """Pages with multiple H1 tags"""
        return [
            {"url": p['url'], "h1_count": len(p['h1']), "h1_tags": p['h1']}
            for p in self.pages
            if len(p.get('h1', [])) > 1
        ]
    
    def _find_slow_pages(self, threshold_ms: int = 3000) -> List[Dict]:
        """Pages loading slower than threshold"""
        return [
            {"url": p['url'], "load_time_ms": p['load_time_ms']}
            for p in self.pages
            if p.get('load_time_ms', 0) > threshold_ms
        ]
    
    def _find_large_pages(self, threshold_kb: int = 1000) -> List[Dict]:
        """Pages larger than threshold"""
        return [
            {"url": p['url'], "size_kb": round(p['size_kb'], 2)}
            for p in self.pages
            if p.get('size_kb', 0) > threshold_kb
        ]
    
    # ──────────────────────────────────────────────────────────────────────
    # Site structure analysis
    # ──────────────────────────────────────────────────────────────────────
    
    def _build_site_tree(self) -> Dict:
        """Build hierarchical site structure by URL depth"""
        tree = {}
        for page in self.pages:
            if page.get('status_code') != 200:
                continue
            
            path = urlparse(page['url']).path
            depth = path.count('/') - (1 if path.endswith('/') else 0)
            
            if depth not in tree:
                tree[depth] = []
            tree[depth].append({
                "url": page['url'],
                "title": page.get('title', ''),
                "word_count": page.get('word_count', 0),
            })
        
        return {f"depth_{k}": v for k, v in sorted(tree.items())}
    
    def _get_top_pages(self, limit: int = 10) -> Dict:
        """Get top pages by various metrics"""
        valid_pages = [p for p in self.pages if p.get('status_code') == 200]
        
        return {
            "most_linked": sorted(
                valid_pages,
                key=lambda p: sum(1 for l in self.internal_links if l['to'] == p['url']),
                reverse=True
            )[:limit],
            "longest_content": sorted(
                valid_pages,
                key=lambda p: p.get('word_count', 0),
                reverse=True
            )[:limit],
            "slowest": sorted(
                valid_pages,
                key=lambda p: p.get('load_time_ms', 0),
                reverse=True
            )[:limit],
        }
    
    # ──────────────────────────────────────────────────────────────────────
    # Helper methods
    # ──────────────────────────────────────────────────────────────────────
    
    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == f'www.{self.domain}' or parsed.netloc == self.domain.replace('www.', '')
        except:
            return False
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else ""
    
    def _get_meta(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        """Extract meta tag content"""
        meta = soup.find('meta', attrs={'name': name})
        if not meta:
            meta = soup.find('meta', attrs={'property': f'og:{name}'})
        return meta.get('content', '').strip() if meta else None
    
    def _get_canonical(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract canonical URL"""
        link = soup.find('link', attrs={'rel': 'canonical'})
        return link.get('href') if link else None
    
    def _count_words(self, soup: BeautifulSoup) -> int:
        """Count words in main content"""
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        text = soup.get_text()
        words = text.split()
        return len(words)
    
    def _analyze_images(self, soup: BeautifulSoup) -> Dict:
        """Analyze images on the page"""
        images = soup.find_all('img')
        
        return {
            "total": len(images),
            "missing_alt": sum(1 for img in images if not img.get('alt')),
            "missing_src": sum(1 for img in images if not img.get('src')),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Convenience function for external use
# ──────────────────────────────────────────────────────────────────────────────

async def crawl_website(url: str, max_pages: int = 500, progress_callback=None) -> Dict:
    """
    Crawl a website and return comprehensive analysis
    
    Args:
        url: Starting URL
        max_pages: Maximum pages to crawl
        progress_callback: Optional async function(progress) for updates
    
    Returns:
        Dictionary with crawl results and analysis
    """
    crawler = SiteCrawler(url, max_pages=max_pages)
    results = await crawler.crawl(progress_callback=progress_callback)
    return results

if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python crawler.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(crawl_website(url))
    
    print(json.dumps(results, indent=2))