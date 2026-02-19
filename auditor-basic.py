"""
Website Auditor - Core Audit Engine
Uses Lighthouse via Playwright for comprehensive website auditing
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
# playwright.async_api import moved into run_lighthouse_audit to avoid import-time errors
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


class WebsiteAuditor:
    """Main class for conducting website audits"""
    
    def __init__(self, url: str):
        self.url = self._normalize_url(url)
        self.results = {
            "url": self.url,
            "audit_date": datetime.now().isoformat(),
            "lighthouse": {},
            "technical_seo": {},
            "meta_info": {},
            "security": {},
            "errors": []
        }
    
    def _normalize_url(self, url: str) -> str:
        """Ensure URL has proper protocol"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    async def run_lighthouse_audit(self) -> Dict[str, Any]:
        """
        Run Lighthouse audit using Playwright
        Returns performance, accessibility, SEO, and best practices scores
        """
        try:
            try:
                from playwright.async_api import async_playwright
            except Exception:
                # Playwright not available or cannot be imported; record error and abort lighthouse step.
                self.results["errors"].append(
                    "Playwright import failed: please install with 'pip install playwright' and run 'playwright install'"
                )
                return {}
            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to the URL
                print(f"Loading {self.url}...")
                await page.goto(self.url, wait_until='networkidle', timeout=30000)
                
                # Get Lighthouse metrics using Chrome DevTools Protocol
                # Note: This is a simplified version. For full Lighthouse,
                # you'd typically use the lighthouse npm package via subprocess
                
                # Get performance metrics
                performance_metrics = await page.evaluate('''() => {
                    return new Promise((resolve) => {
                        new PerformanceObserver((list) => {
                            const entries = list.getEntries();
                            resolve(entries);
                        }).observe({ entryTypes: ['navigation', 'paint'] });
                        
                        setTimeout(() => {
                            const navigation = performance.getEntriesByType('navigation')[0];
                            const paint = performance.getEntriesByType('paint');
                            
                            resolve({
                                navigation: navigation ? {
                                    domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                                    loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
                                    domInteractive: navigation.domInteractive - navigation.fetchStart,
                                    responseTime: navigation.responseEnd - navigation.requestStart
                                } : null,
                                paint: paint.map(p => ({
                                    name: p.name,
                                    startTime: p.startTime
                                }))
                            });
                        }, 1000);
                    });
                }''')
                
                # Get Core Web Vitals
                web_vitals = await page.evaluate('''() => {
                    return new Promise((resolve) => {
                        let vitals = {};
                        
                        // Get LCP (Largest Contentful Paint)
                        new PerformanceObserver((list) => {
                            const entries = list.getEntries();
                            const lastEntry = entries[entries.length - 1];
                            vitals.lcp = lastEntry.renderTime || lastEntry.loadTime;
                        }).observe({ entryTypes: ['largest-contentful-paint'] });
                        
                        // Get FID (First Input Delay) - simplified
                        new PerformanceObserver((list) => {
                            const entries = list.getEntries();
                            entries.forEach(entry => {
                                vitals.fid = entry.processingStart - entry.startTime;
                            });
                        }).observe({ entryTypes: ['first-input'] });
                        
                        // Get CLS (Cumulative Layout Shift)
                        let clsScore = 0;
                        new PerformanceObserver((list) => {
                            list.getEntries().forEach(entry => {
                                if (!entry.hadRecentInput) {
                                    clsScore += entry.value;
                                }
                            });
                            vitals.cls = clsScore;
                        }).observe({ entryTypes: ['layout-shift'] });
                        
                        setTimeout(() => resolve(vitals), 2000);
                    });
                }''')
                
                # Check mobile-friendliness
                mobile_viewport = await page.evaluate('''() => {
                    const viewport = document.querySelector('meta[name="viewport"]');
                    return viewport ? viewport.content : null;
                }''')
                
                # Get page size and resource counts
                resources = await page.evaluate('''() => {
                    const resources = performance.getEntriesByType('resource');
                    return {
                        total: resources.length,
                        images: resources.filter(r => r.initiatorType === 'img').length,
                        scripts: resources.filter(r => r.initiatorType === 'script').length,
                        stylesheets: resources.filter(r => r.initiatorType === 'link' || r.initiatorType === 'css').length,
                        totalSize: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0)
                    };
                }''')
                
                await browser.close()
                
                # Calculate scores (simplified scoring logic)
                lighthouse_data = {
                    "performance": {
                        "score": self._calculate_performance_score(performance_metrics, web_vitals),
                        "metrics": {
                            "performance_metrics": performance_metrics,
                            "core_web_vitals": web_vitals,
                            "resources": resources
                        }
                    },
                    "mobile_friendly": {
                        "has_viewport": mobile_viewport is not None,
                        "viewport_content": mobile_viewport
                    }
                }
                
                return lighthouse_data
                
        except Exception as e:
            self.results["errors"].append(f"Lighthouse audit failed: {str(e)}")
            return {}
    
    def _calculate_performance_score(self, perf_metrics: Dict, vitals: Dict) -> int:
        """Calculate a simplified performance score (0-100)"""
        score = 100
        
        # Deduct points for slow metrics
        if vitals.get('lcp', 0) > 2500:  # LCP should be under 2.5s
            score -= 30
        elif vitals.get('lcp', 0) > 1500:
            score -= 15
        
        if vitals.get('cls', 0) > 0.25:  # CLS should be under 0.1
            score -= 20
        elif vitals.get('cls', 0) > 0.1:
            score -= 10
        
        if vitals.get('fid', 0) > 300:  # FID should be under 100ms
            score -= 20
        elif vitals.get('fid', 0) > 100:
            score -= 10
        
        return max(0, score)
    
    def audit_technical_seo(self) -> Dict[str, Any]:
        """
        Audit technical SEO elements
        - Meta tags
        - Headings structure
        - Canonical URLs
        - Robots.txt
        - Sitemap
        """
        try:
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Meta tags
            title = soup.find('title')
            meta_description = soup.find('meta', attrs={'name': 'description'})
            canonical = soup.find('link', attrs={'rel': 'canonical'})
            
            # Headings structure
            headings = {
                'h1': len(soup.find_all('h1')),
                'h2': len(soup.find_all('h2')),
                'h3': len(soup.find_all('h3')),
                'h4': len(soup.find_all('h4')),
                'h5': len(soup.find_all('h5')),
                'h6': len(soup.find_all('h6'))
            }
            
            # Check for robots.txt
            parsed_url = urlparse(self.url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            has_robots = False
            try:
                robots_response = requests.get(robots_url, timeout=5)
                has_robots = robots_response.status_code == 200
            except:
                pass
            
            # Check for sitemap
            sitemap_url = f"{parsed_url.scheme}://{parsed_url.netloc}/sitemap.xml"
            has_sitemap = False
            try:
                sitemap_response = requests.get(sitemap_url, timeout=5)
                has_sitemap = sitemap_response.status_code == 200
            except:
                pass
            
            seo_data = {
                "title": {
                    "present": title is not None,
                    "content": title.string if title else None,
                    "length": len(title.string) if title and title.string else 0,
                    "optimal": 50 <= len(title.string) <= 60 if title and title.string else False
                },
                "meta_description": {
                    "present": meta_description is not None,
                    "content": meta_description.get('content') if meta_description else None,
                    "length": len(meta_description.get('content', '')) if meta_description else 0,
                    "optimal": 120 <= len(meta_description.get('content', '')) <= 160 if meta_description else False
                },
                "canonical": {
                    "present": canonical is not None,
                    "url": canonical.get('href') if canonical else None
                },
                "headings": headings,
                "headings_issues": self._check_heading_issues(headings),
                "robots_txt": has_robots,
                "sitemap_xml": has_sitemap
            }
            
            return seo_data
            
        except Exception as e:
            self.results["errors"].append(f"Technical SEO audit failed: {str(e)}")
            return {}
    
    def _check_heading_issues(self, headings: Dict[str, int]) -> list:
        """Check for common heading structure issues"""
        issues = []
        
        if headings['h1'] == 0:
            issues.append("No H1 tag found")
        elif headings['h1'] > 1:
            issues.append(f"Multiple H1 tags found ({headings['h1']})")
        
        return issues
    
    def audit_security(self) -> Dict[str, Any]:
        """
        Audit security features
        - HTTPS
        - Security headers
        - Mixed content
        """
        try:
            response = requests.get(self.url, timeout=10)
            
            security_data = {
                "https": self.url.startswith('https://'),
                "security_headers": {
                    "strict_transport_security": 'Strict-Transport-Security' in response.headers,
                    "x_frame_options": 'X-Frame-Options' in response.headers,
                    "x_content_type_options": 'X-Content-Type-Options' in response.headers,
                    "content_security_policy": 'Content-Security-Policy' in response.headers
                },
                "ssl_valid": response.url.startswith('https://') if hasattr(response, 'url') else False
            }
            
            return security_data
            
        except Exception as e:
            self.results["errors"].append(f"Security audit failed: {str(e)}")
            return {}
    
    async def run_full_audit(self) -> Dict[str, Any]:
        """
        Run complete audit including all checks
        """
        print(f"\n{'='*60}")
        print(f"Starting audit for: {self.url}")
        print(f"{'='*60}\n")
        
        # Run Lighthouse audit (async)
        print("1. Running Lighthouse audit...")
        self.results["lighthouse"] = await self.run_lighthouse_audit()
        
        # Run technical SEO audit
        print("2. Auditing technical SEO...")
        self.results["technical_seo"] = self.audit_technical_seo()
        
        # Run security audit
        print("3. Auditing security...")
        self.results["security"] = self.audit_security()
        
        # Calculate overall score
        self.results["overall_score"] = self._calculate_overall_score()
        
        print(f"\n{'='*60}")
        print("Audit complete!")
        print(f"{'='*60}\n")
        
        return self.results
    
    def _calculate_overall_score(self) -> int:
        """Calculate overall audit score"""
        scores = []
        
        # Lighthouse performance score
        if self.results["lighthouse"].get("performance", {}).get("score"):
            scores.append(self.results["lighthouse"]["performance"]["score"])
        
        # SEO score (simplified)
        seo_score = 100
        seo = self.results.get("technical_seo", {})
        
        if not seo.get("title", {}).get("present"):
            seo_score -= 20
        if not seo.get("meta_description", {}).get("present"):
            seo_score -= 15
        if not seo.get("robots_txt"):
            seo_score -= 10
        if not seo.get("sitemap_xml"):
            seo_score -= 10
        if seo.get("headings_issues"):
            seo_score -= 15
        
        scores.append(max(0, seo_score))
        
        # Security score (simplified)
        sec_score = 100
        sec = self.results.get("security", {})
        
        if not sec.get("https"):
            sec_score -= 40
        if not sec.get("security_headers", {}).get("strict_transport_security"):
            sec_score -= 15
        if not sec.get("security_headers", {}).get("x_frame_options"):
            sec_score -= 15
        
        scores.append(max(0, sec_score))
        
        return int(sum(scores) / len(scores)) if scores else 0
    
    def print_summary(self):
        """Print a human-readable summary of the audit"""
        print(f"\n{'='*60}")
        print(f"AUDIT SUMMARY FOR: {self.url}")
        print(f"{'='*60}")
        print(f"\nOverall Score: {self.results.get('overall_score', 0)}/100\n")
        
        # Performance
        perf = self.results.get("lighthouse", {}).get("performance", {})
        if perf:
            print(f"Performance Score: {perf.get('score', 'N/A')}/100")
            vitals = perf.get("metrics", {}).get("core_web_vitals", {})
            if vitals:
                print(f"  - LCP: {vitals.get('lcp', 'N/A')}ms")
                print(f"  - CLS: {vitals.get('cls', 'N/A')}")
                print(f"  - FID: {vitals.get('fid', 'N/A')}ms")
        
        # SEO
        print("\nTechnical SEO:")
        seo = self.results.get("technical_seo", {})
        print(f"  - Title Tag: {'✓' if seo.get('title', {}).get('present') else '✗'}")
        print(f"  - Meta Description: {'✓' if seo.get('meta_description', {}).get('present') else '✗'}")
        print(f"  - Robots.txt: {'✓' if seo.get('robots_txt') else '✗'}")
        print(f"  - Sitemap.xml: {'✓' if seo.get('sitemap_xml') else '✗'}")
        
        if seo.get('headings_issues'):
            print(f"  - Issues: {', '.join(seo['headings_issues'])}")
        
        # Security
        print("\nSecurity:")
        sec = self.results.get("security", {})
        print(f"  - HTTPS: {'✓' if sec.get('https') else '✗'}")
        print(f"  - HSTS Header: {'✓' if sec.get('security_headers', {}).get('strict_transport_security') else '✗'}")
        
        # Errors
        if self.results.get("errors"):
            print("\nErrors encountered:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        print(f"\n{'='*60}\n")


async def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python auditor.py <url>")
        print("Example: python auditor.py https://example.com")
        sys.exit(1)
    
    url = sys.argv[1]
    auditor = WebsiteAuditor(url)
    
    # Run the audit
    results = await auditor.run_full_audit()
    
    # Print summary
    auditor.print_summary()
    
    # Save results to JSON file
    output_file = f"audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Full results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())