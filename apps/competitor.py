"""
Competitor Comparison - Analyze your site vs up to 3 competitors
Runs multiple audits in parallel and generates comparison matrices
"""

import asyncio
from typing import List, Dict, Any, Optional
from auditor import WebsiteAuditor
from datetime import datetime


class CompetitorAnalyzer:
    """Runs parallel audits and generates competitive intelligence"""
    
    def __init__(self, target_url: str, competitor_urls: List[str]):
        self.target_url = target_url
        self.competitor_urls = competitor_urls[:3]  # Max 3 competitors
        self.all_urls = [target_url] + self.competitor_urls
        
    async def run_comparison(self, progress_callback=None) -> Dict[str, Any]:
        """
        Run audits on all sites in parallel and compare results
        
        Args:
            progress_callback: Optional async function(progress, status) for updates
        
        Returns:
            Comprehensive comparison with winners, gaps, and recommendations
        """
        # Run all audits concurrently
        if progress_callback:
            await progress_callback(10, "Starting audits")
        
        tasks = [self._run_single_audit(url) for url in self.all_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        if progress_callback:
            await progress_callback(60, "Analyzing results")
        
        # Separate target from competitors
        target_result = results[0]
        competitor_results = [r for r in results[1:] if not isinstance(r, Exception)]
        
        # Handle errors
        if isinstance(target_result, Exception):
            raise Exception(f"Target audit failed: {str(target_result)}")
        
        # Generate comparison
        if progress_callback:
            await progress_callback(80, "Generating insights")
        
        comparison = self._generate_comparison(target_result, competitor_results)
        
        if progress_callback:
            await progress_callback(100, "Complete")
        
        return comparison
    
    async def _run_single_audit(self, url: str) -> Dict:
        """Run full audit on a single URL"""
        auditor = WebsiteAuditor(url)
        result = await auditor.run_full_audit()
        return result
    
    def _generate_comparison(self, target: Dict, competitors: List[Dict]) -> Dict:
        """Generate comprehensive comparison data"""
        
        all_sites = [target] + competitors
        
        # Overall scores comparison
        overall_scores = {
            "target": {
                "url": target["url"],
                "score": target["overall_score"],
            },
            "competitors": [
                {"url": comp["url"], "score": comp["overall_score"]}
                for comp in competitors
            ]
        }
        
        # Category-by-category comparison
        categories = self._compare_categories(all_sites)
        
        # Performance metrics comparison
        performance = self._compare_performance(all_sites)
        
        # SEO comparison
        seo = self._compare_seo(all_sites)
        
        # Content comparison
        content = self._compare_content(all_sites)
        
        # Security comparison
        security = self._compare_security(all_sites)
        
        # Technical comparison
        technical = self._compare_technical(all_sites)
        
        # Calculate competitive gaps and opportunities
        gaps = self._identify_gaps(target, competitors)
        
        # Winner analysis
        winners = self._calculate_winners(all_sites)
        
        return {
            "target_url": self.target_url,
            "competitor_urls": self.competitor_urls,
            "comparison_date": datetime.now().isoformat(),
            "overall_scores": overall_scores,
            "categories": categories,
            "performance": performance,
            "seo": seo,
            "content": content,
            "security": security,
            "technical": technical,
            "gaps": gaps,
            "winners": winners,
            "raw_results": {
                "target": target,
                "competitors": competitors
            }
        }
    
    def _compare_categories(self, sites: List[Dict]) -> Dict:
        """Compare Lighthouse category scores"""
        categories = {}
        
        # Get all category names from first site
        first_site = sites[0]
        lighthouse_cats = first_site.get("lighthouse", {}).get("categories", {})
        
        for cat_key, cat_data in lighthouse_cats.items():
            cat_name = cat_data.get("title", cat_key)
            
            scores = []
            for site in sites:
                cat = site.get("lighthouse", {}).get("categories", {}).get(cat_key, {})
                scores.append({
                    "url": site["url"],
                    "score": cat.get("score", 0),
                })
            
            # Find winner
            winner = max(scores, key=lambda x: x["score"])
            
            categories[cat_key] = {
                "name": cat_name,
                "scores": scores,
                "winner": winner["url"],
                "winner_score": winner["score"],
                "target_score": scores[0]["score"],
                "target_position": sorted(scores, key=lambda x: x["score"], reverse=True).index(scores[0]) + 1,
            }
        
        return categories
    
    def _compare_performance(self, sites: List[Dict]) -> Dict:
        """Compare Core Web Vitals and performance metrics"""
        metrics = {}
        
        # Core Web Vitals
        cwv_keys = ["lcp", "cls", "tbt", "fcp"]
        
        for key in cwv_keys:
            values = []
            for site in sites:
                cwv = site.get("lighthouse", {}).get("metrics", {}).get("coreWebVitals", {})
                if key in cwv:
                    values.append({
                        "url": site["url"],
                        "value": cwv[key].get("numericValue", 0),
                        "display": cwv[key].get("displayValue", "—"),
                        "score": cwv[key].get("score", 0),
                    })
            
            if values:
                # For CLS, lower is better; for others, lower is also better (time)
                best = min(values, key=lambda x: x["value"])
                
                metrics[key] = {
                    "values": values,
                    "winner": best["url"],
                    "best_value": best["display"],
                    "target_value": values[0]["display"],
                    "target_position": sorted(values, key=lambda x: x["value"]).index(values[0]) + 1,
                }
        
        return metrics
    
    def _compare_seo(self, sites: List[Dict]) -> Dict:
        """Compare SEO factors"""
        seo_data = {
            "structured_data": [],
            "meta_quality": [],
            "technical_seo": [],
        }
        
        for site in sites:
            url = site["url"]
            
            # Structured data
            sd = site.get("structured_data", {})
            seo_data["structured_data"].append({
                "url": url,
                "score": sd.get("score", 0),
                "has_json_ld": sd.get("has_json_ld", False),
                "has_open_graph": sd.get("has_open_graph", False),
                "has_twitter_card": sd.get("has_twitter_card", False),
            })
            
            # Meta quality
            tech_seo = site.get("technical_seo", {})
            seo_data["meta_quality"].append({
                "url": url,
                "has_title": tech_seo.get("title", {}).get("present", False),
                "has_meta_desc": tech_seo.get("meta_description", {}).get("present", False),
                "has_canonical": tech_seo.get("canonical", {}).get("present", False),
                "has_robots": tech_seo.get("robots_txt", False),
                "has_sitemap": tech_seo.get("sitemap_xml", False),
            })
            
            # Technical SEO score
            tech_score = sum([
                10 if tech_seo.get("title", {}).get("present") else 0,
                10 if tech_seo.get("meta_description", {}).get("present") else 0,
                10 if tech_seo.get("canonical", {}).get("present") else 0,
                10 if tech_seo.get("robots_txt") else 0,
                10 if tech_seo.get("sitemap_xml") else 0,
                tech_seo.get("headings", {}).get("h1", 0) == 1 and 10 or 0,
            ])
            seo_data["technical_seo"].append({
                "url": url,
                "score": tech_score,
            })
        
        # Find winners
        sd_winner = max(seo_data["structured_data"], key=lambda x: x["score"])
        tech_winner = max(seo_data["technical_seo"], key=lambda x: x["score"])
        
        return {
            "structured_data": {
                "data": seo_data["structured_data"],
                "winner": sd_winner["url"],
                "winner_score": sd_winner["score"],
            },
            "meta_quality": seo_data["meta_quality"],
            "technical_seo": {
                "data": seo_data["technical_seo"],
                "winner": tech_winner["url"],
                "winner_score": tech_winner["score"],
            },
        }
    
    def _compare_content(self, sites: List[Dict]) -> Dict:
        """Compare content quality metrics"""
        content_data = []
        
        for site in sites:
            cq = site.get("content_quality", {})
            content_data.append({
                "url": site["url"],
                "score": cq.get("score", 0),
                "word_count": cq.get("word_count", 0),
                "reading_level": cq.get("reading_level", "Unknown"),
                "content_ratio": cq.get("content_to_code_ratio", 0),
            })
        
        # Find winner by word count (more content = better for SEO)
        winner = max(content_data, key=lambda x: x["word_count"])
        
        return {
            "data": content_data,
            "winner": winner["url"],
            "winner_word_count": winner["word_count"],
            "avg_word_count": sum(d["word_count"] for d in content_data) / len(content_data),
        }
    
    def _compare_security(self, sites: List[Dict]) -> Dict:
        """Compare security features"""
        security_data = []
        
        for site in sites:
            sec = site.get("security", {})
            headers = sec.get("security_headers", {})
            
            score = sum([
                20 if sec.get("https") else 0,
                20 if headers.get("strict_transport_security") else 0,
                20 if headers.get("x_frame_options") else 0,
                20 if headers.get("x_content_type_options") else 0,
                20 if headers.get("content_security_policy") else 0,
            ])
            
            security_data.append({
                "url": site["url"],
                "score": score,
                "https": sec.get("https", False),
                "hsts": headers.get("strict_transport_security", False),
                "xfo": headers.get("x_frame_options", False),
                "xcto": headers.get("x_content_type_options", False),
                "csp": headers.get("content_security_policy", False),
            })
        
        winner = max(security_data, key=lambda x: x["score"])
        
        return {
            "data": security_data,
            "winner": winner["url"],
            "winner_score": winner["score"],
        }
    
    def _compare_technical(self, sites: List[Dict]) -> Dict:
        """Compare technical factors like broken links, image optimization"""
        technical_data = []
        
        for site in sites:
            bl = site.get("broken_links", {})
            img = site.get("image_optimization", {})
            
            technical_data.append({
                "url": site["url"],
                "broken_links": bl.get("broken_count", 0),
                "image_score": img.get("score", 0),
                "image_issues": img.get("issues", {}).get("missing_alt_count", 0),
            })
        
        # Winner = fewest broken links
        winner = min(technical_data, key=lambda x: x["broken_links"])
        
        return {
            "data": technical_data,
            "winner": winner["url"],
            "winner_broken_links": winner["broken_links"],
        }
    
    def _identify_gaps(self, target: Dict, competitors: List[Dict]) -> List[Dict]:
        """Identify specific areas where competitors are beating you"""
        gaps = []
        
        # Performance gaps
        target_lcp = target.get("lighthouse", {}).get("metrics", {}).get("coreWebVitals", {}).get("lcp", {}).get("numericValue", 9999)
        for comp in competitors:
            comp_lcp = comp.get("lighthouse", {}).get("metrics", {}).get("coreWebVitals", {}).get("lcp", {}).get("numericValue", 9999)
            if comp_lcp < target_lcp * 0.8:  # 20% faster
                diff = target_lcp - comp_lcp
                gaps.append({
                    "type": "performance",
                    "severity": "high",
                    "metric": "Largest Contentful Paint",
                    "message": f"{comp['url']} loads {diff:.0f}ms faster",
                    "recommendation": "Optimize images, reduce server response time, minimize render-blocking resources",
                })
        
        # Content depth gaps
        target_words = target.get("content_quality", {}).get("word_count", 0)
        for comp in competitors:
            comp_words = comp.get("content_quality", {}).get("word_count", 0)
            if comp_words > target_words * 1.5:  # 50% more content
                gaps.append({
                    "type": "content",
                    "severity": "medium",
                    "metric": "Content Depth",
                    "message": f"{comp['url']} has {comp_words - target_words} more words",
                    "recommendation": "Expand content to match or exceed competitor depth. Add more detailed explanations, examples, and use cases.",
                })
        
        # Security gaps
        target_https = target.get("security", {}).get("https", False)
        if not target_https:
            for comp in competitors:
                if comp.get("security", {}).get("https", False):
                    gaps.append({
                        "type": "security",
                        "severity": "critical",
                        "metric": "HTTPS",
                        "message": "Competitors use HTTPS, you don't",
                        "recommendation": "Install SSL certificate immediately. This is a ranking factor and security requirement.",
                    })
                    break
        
        # Structured data gaps
        target_sd = target.get("structured_data", {})
        target_has_json_ld = target_sd.get("has_json_ld", False)
        if not target_has_json_ld:
            for comp in competitors:
                if comp.get("structured_data", {}).get("has_json_ld", False):
                    gaps.append({
                        "type": "seo",
                        "severity": "medium",
                        "metric": "Structured Data",
                        "message": "Competitors use JSON-LD structured data",
                        "recommendation": "Add Schema.org markup to improve rich snippets in search results",
                    })
                    break
        
        # Meta description gaps
        target_has_meta = target.get("technical_seo", {}).get("meta_description", {}).get("present", False)
        if not target_has_meta:
            for comp in competitors:
                if comp.get("technical_seo", {}).get("meta_description", {}).get("present", False):
                    gaps.append({
                        "type": "seo",
                        "severity": "high",
                        "metric": "Meta Description",
                        "message": "Competitors have meta descriptions",
                        "recommendation": "Write compelling meta descriptions (150-160 chars) to improve click-through rates",
                    })
                    break
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
        return gaps
    
    def _calculate_winners(self, sites: List[Dict]) -> Dict:
        """Calculate who wins in each category"""
        winners = {
            "overall": None,
            "performance": None,
            "seo": None,
            "accessibility": None,
            "best_practices": None,
            "content": None,
            "security": None,
        }
        
        # Overall winner (highest overall_score)
        overall_winner = max(sites, key=lambda x: x.get("overall_score", 0))
        winners["overall"] = overall_winner["url"]
        
        # Performance winner
        perf_scores = [
            (site["url"], site.get("lighthouse", {}).get("categories", {}).get("performance", {}).get("score", 0))
            for site in sites
        ]
        winners["performance"] = max(perf_scores, key=lambda x: x[1])[0]
        
        # SEO winner
        seo_scores = [
            (site["url"], site.get("lighthouse", {}).get("categories", {}).get("seo", {}).get("score", 0))
            for site in sites
        ]
        winners["seo"] = max(seo_scores, key=lambda x: x[1])[0]
        
        # Accessibility winner
        a11y_scores = [
            (site["url"], site.get("lighthouse", {}).get("categories", {}).get("accessibility", {}).get("score", 0))
            for site in sites
        ]
        winners["accessibility"] = max(a11y_scores, key=lambda x: x[1])[0]
        
        # Best practices winner
        bp_scores = [
            (site["url"], site.get("lighthouse", {}).get("categories", {}).get("best-practices", {}).get("score", 0))
            for site in sites
        ]
        winners["best_practices"] = max(bp_scores, key=lambda x: x[1])[0]
        
        # Content winner (most words)
        content_scores = [
            (site["url"], site.get("content_quality", {}).get("word_count", 0))
            for site in sites
        ]
        winners["content"] = max(content_scores, key=lambda x: x[1])[0]
        
        # Security winner
        security_scores = []
        for site in sites:
            sec = site.get("security", {})
            headers = sec.get("security_headers", {})
            score = sum([
                20 if sec.get("https") else 0,
                20 if headers.get("strict_transport_security") else 0,
                20 if headers.get("x_frame_options") else 0,
                20 if headers.get("x_content_type_options") else 0,
                20 if headers.get("content_security_policy") else 0,
            ])
            security_scores.append((site["url"], score))
        winners["security"] = max(security_scores, key=lambda x: x[1])[0]
        
        # Count wins for each site
        win_counts = {}
        for url in [site["url"] for site in sites]:
            win_counts[url] = sum(1 for w in winners.values() if w == url)
        
        winners["win_counts"] = win_counts
        
        return winners


# ──────────────────────────────────────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────────────────────────────────────

async def compare_competitors(
    target_url: str,
    competitor_urls: List[str],
    progress_callback=None
) -> Dict[str, Any]:
    """
    Compare your site against up to 3 competitors
    
    Args:
        target_url: Your website URL
        competitor_urls: List of 1-3 competitor URLs
        progress_callback: Optional async function(progress, status)
    
    Returns:
        Comprehensive comparison analysis
    """
    analyzer = CompetitorAnalyzer(target_url, competitor_urls)
    results = await analyzer.run_comparison(progress_callback=progress_callback)
    return results