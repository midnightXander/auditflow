"""
Website Auditor - Core Audit Engine
Uses full Lighthouse (Node.js) for comprehensive website auditing
"""

import json
import asyncio
import subprocess
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional
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
            "broken_links": {},
            "image_optimization": {},
            "structured_data": {},
            "content_quality": {},
            "errors": []
        }
    
    def _normalize_url(self, url: str) -> str:
        """Ensure URL has proper protocol"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    async def run_lighthouse_audit(self) -> Dict[str, Any]:
        """
        Run full Lighthouse audit using Node.js Lighthouse package
        Returns comprehensive audit results including all categories
        """
        try:
            print(f"Running Lighthouse audit (this may take 30-60 seconds)...")
            
            # Create temporary file for results
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                tmp_path = tmp.name
            try:
                # Run Lighthouse via Node.js
                result = subprocess.run(
                    ['node', 'lighthouse-runner.js', self.url, tmp_path],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',   # decode subprocess output as UTF-8 (handles most cases for windows compatibility)
                    errors='replace',  # avoid decode errors by replacing invalid bytes
                    timeout=120  # 2 minute timeout
                )
                
                if result.returncode != 0:
                    print(f"Lighthouse failed: {result.stderr}")
                    raise Exception(f"Lighthouse failed: {result.stderr}")
                
                # Read the results
                with open(tmp_path, 'r',encoding='utf-8', errors='replace') as f:
                    print("Lighthouse audit succesful, saving")
                    lighthouse_data = json.load(f)
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                return lighthouse_data
                
            except subprocess.TimeoutExpired:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise Exception("Lighthouse audit timed out after 2 minutes")
            except FileNotFoundError:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise Exception("Node.js or lighthouse-runner.js not found. Make sure to run 'npm install' first.")
                
        except Exception as e:
            self.results["errors"].append(f"Lighthouse audit failed: {str(e)}")
            return {}
    
    def _calculate_performance_score(self, lighthouse_data: Dict) -> int:
        """Calculate performance score from Lighthouse results"""
        if not lighthouse_data:
            return 0
        
        # Use Lighthouse's performance score if available
        categories = lighthouse_data.get('categories', {})
        performance = categories.get('performance', {})
        return performance.get('score', 0)
    
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
    
    def audit_broken_links(self) -> Dict[str, Any]:
        """
        Check for broken links on the page
        - Internal links
        - External links
        - Images
        - Stylesheets
        - Scripts
        """
        try:
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            base_url = self.url
            parsed_base = urlparse(base_url)
            
            links_to_check = []
            broken_links = []
            working_links = []
            
            # Collect all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Skip anchors, mailto, tel, etc.
                if href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                    continue
                
                # Convert relative to absolute
                if href.startswith('/'):
                    href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                elif not href.startswith(('http://', 'https://')):
                    href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                
                links_to_check.append({
                    'url': href,
                    'type': 'link',
                    'text': link.get_text(strip=True)[:50]
                })
            
            # Collect images
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src.startswith('/'):
                    src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
                elif not src.startswith(('http://', 'https://', 'data:')):
                    src = f"{base_url.rstrip('/')}/{src.lstrip('/')}"
                
                if not src.startswith('data:'):
                    links_to_check.append({
                        'url': src,
                        'type': 'image',
                        'alt': img.get('alt', '')[:50]
                    })
            
            # Check links (limit to first 50 to avoid long processing)
            print(f"   Checking {min(len(links_to_check), 50)} links...")
            for item in links_to_check[:50]:
                try:
                    check_response = requests.head(item['url'], timeout=5, allow_redirects=True)
                    if check_response.status_code >= 400:
                        broken_links.append({
                            **item,
                            'status_code': check_response.status_code
                        })
                    else:
                        working_links.append(item)
                except Exception as e:
                    broken_links.append({
                        **item,
                        'error': str(e)
                    })
            
            return {
                "total_checked": len(links_to_check[:50]),
                "total_found": len(links_to_check),
                "broken_count": len(broken_links),
                "working_count": len(working_links),
                "broken_links": broken_links[:10],  # Show first 10 broken links
                "status": "pass" if len(broken_links) == 0 else "warning" if len(broken_links) < 5 else "fail"
            }
            
        except Exception as e:
            self.results["errors"].append(f"Broken link check failed: {str(e)}")
            return {}
    
    def audit_image_optimization(self) -> Dict[str, Any]:
        """
        Analyze image optimization opportunities
        - Image formats
        - Image sizes
        - Missing dimensions
        - Missing alt text
        - Lazy loading
        """
        try:
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            images = soup.find_all('img')
            total_images = len(images)
            
            issues = {
                'missing_alt': [],
                'missing_dimensions': [],
                'large_images': [],
                'no_lazy_loading': [],
                'old_formats': []
            }
            
            optimized_count = 0
            
            for img in images:
                src = img.get('src', '')
                
                # Check alt text
                if not img.get('alt'):
                    issues['missing_alt'].append(src[:100])
                
                # Check dimensions
                if not img.get('width') or not img.get('height'):
                    issues['missing_dimensions'].append(src[:100])
                else:
                    optimized_count += 1
                
                # Check lazy loading
                if not img.get('loading') == 'lazy':
                    issues['no_lazy_loading'].append(src[:100])
                
                # Check format (basic check from extension)
                if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    if '.gif' not in src.lower():  # GIFs might be animated
                        issues['old_formats'].append(src[:100])
            
            # Calculate score
            score = 100
            if len(issues['missing_alt']) > 0:
                score -= min(30, len(issues['missing_alt']) * 3)
            if len(issues['missing_dimensions']) > 0:
                score -= min(20, len(issues['missing_dimensions']) * 2)
            if len(issues['no_lazy_loading']) > total_images * 0.8 and total_images > 5:
                score -= 15
            
            return {
                "total_images": total_images,
                "optimized_images": optimized_count,
                "score": max(0, score),
                "issues": {
                    "missing_alt_count": len(issues['missing_alt']),
                    "missing_alt_examples": issues['missing_alt'][:5],
                    "missing_dimensions_count": len(issues['missing_dimensions']),
                    "missing_dimensions_examples": issues['missing_dimensions'][:5],
                    "no_lazy_loading_count": len(issues['no_lazy_loading']),
                    "old_format_count": len(issues['old_formats']),
                    "old_format_examples": issues['old_formats'][:5]
                },
                "recommendations": self._get_image_recommendations(issues, total_images)
            }
            
        except Exception as e:
            self.results["errors"].append(f"Image optimization audit failed: {str(e)}")
            return {}
    
    def _get_image_recommendations(self, issues: Dict, total: int) -> list:
        """Generate image optimization recommendations"""
        recommendations = []
        
        if len(issues['missing_alt']) > 0:
            recommendations.append(f"Add alt text to {len(issues['missing_alt'])} images for accessibility and SEO")
        
        if len(issues['missing_dimensions']) > 0:
            recommendations.append(f"Add width/height attributes to {len(issues['missing_dimensions'])} images to prevent layout shift")
        
        if len(issues['no_lazy_loading']) > total * 0.5 and total > 5:
            recommendations.append("Implement lazy loading for below-the-fold images")
        
        if len(issues['old_formats']) > 0:
            recommendations.append(f"Convert {len(issues['old_formats'])} images to modern formats (WebP, AVIF)")
        
        return recommendations
    
    def audit_structured_data(self) -> Dict[str, Any]:
        """
        Validate structured data (Schema.org, JSON-LD)
        - Presence of structured data
        - Valid JSON-LD
        - Schema.org types
        - Required properties
        """
        try:
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            structured_data = {
                'json_ld': [],
                'microdata': [],
                'rdfa': [],
                'open_graph': {},
                'twitter_card': {}
            }
            
            # Find JSON-LD
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    structured_data['json_ld'].append(data)
                except json.JSONDecodeError:
                    self.results["errors"].append("Invalid JSON-LD found")
            
            # Check for microdata
            items_with_itemtype = soup.find_all(attrs={'itemtype': True})
            for item in items_with_itemtype:
                structured_data['microdata'].append(item.get('itemtype'))
            
            # Check Open Graph
            og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
            for tag in og_tags:
                prop = tag.get('property', '').replace('og:', '')
                structured_data['open_graph'][prop] = tag.get('content', '')
            
            # Check Twitter Card
            twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
            for tag in twitter_tags:
                name = tag.get('name', '').replace('twitter:', '')
                structured_data['twitter_card'][name] = tag.get('content', '')
            
            # Calculate score
            score = 0
            if len(structured_data['json_ld']) > 0:
                score += 40
            if len(structured_data['microdata']) > 0:
                score += 20
            if len(structured_data['open_graph']) >= 4:  # title, type, image, url
                score += 20
            if len(structured_data['twitter_card']) >= 2:
                score += 20
            
            return {
                "score": score,
                "has_json_ld": len(structured_data['json_ld']) > 0,
                "json_ld_count": len(structured_data['json_ld']),
                "json_ld_types": [item.get('@type', 'Unknown') for item in structured_data['json_ld'] if isinstance(item, dict)],
                "has_microdata": len(structured_data['microdata']) > 0,
                "microdata_types": list(set(structured_data['microdata']))[:5],
                "has_open_graph": len(structured_data['open_graph']) > 0,
                "open_graph_properties": list(structured_data['open_graph'].keys()),
                "has_twitter_card": len(structured_data['twitter_card']) > 0,
                "twitter_card_type": structured_data['twitter_card'].get('card', 'none'),
                "status": "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "poor",
                "recommendations": self._get_structured_data_recommendations(structured_data)
            }
            
        except Exception as e:
            self.results["errors"].append(f"Structured data audit failed: {str(e)}")
            return {}
    
    def _get_structured_data_recommendations(self, data: Dict) -> list:
        """Generate structured data recommendations"""
        recommendations = []
        
        if len(data['json_ld']) == 0:
            recommendations.append("Add JSON-LD structured data for better search engine understanding")
        
        if len(data['open_graph']) < 4:
            recommendations.append("Add Open Graph tags for better social media sharing (og:title, og:type, og:image, og:url)")
        
        if len(data['twitter_card']) == 0:
            recommendations.append("Add Twitter Card meta tags for enhanced Twitter sharing")
        
        if len(data['json_ld']) > 0:
            recommendations.append("Validate your structured data with Google's Rich Results Test")
        
        return recommendations
    
    def audit_content_quality(self) -> Dict[str, Any]:
        """
        Analyze content quality
        - Word count
        - Reading level
        - Heading structure
        - Paragraph length
        - Keyword density (basic)
        - Content-to-code ratio
        """
        try:
            response = requests.get(self.url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            
            # Get main content
            main_content = soup.find('main') or soup.find('article') or soup.body
            if not main_content:
                main_content = soup
            
            text = main_content.get_text(separator=' ', strip=True)
            
            # Word count
            words = text.split()
            word_count = len(words)
            
            # Paragraph analysis
            paragraphs = main_content.find_all('p')
            paragraph_count = len(paragraphs)
            
            avg_paragraph_length = 0
            if paragraph_count > 0:
                total_p_words = sum(len(p.get_text().split()) for p in paragraphs)
                avg_paragraph_length = total_p_words / paragraph_count if paragraph_count > 0 else 0
            
            # Sentence analysis (basic)
            sentences = text.split('.')
            sentence_count = len([s for s in sentences if len(s.strip()) > 0])
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            
            # Heading structure
            headings = {
                'h1': len(main_content.find_all('h1')),
                'h2': len(main_content.find_all('h2')),
                'h3': len(main_content.find_all('h3'))
            }
            
            # Content-to-code ratio
            html_size = len(str(soup))
            text_size = len(text)
            content_ratio = (text_size / html_size * 100) if html_size > 0 else 0
            
            # Reading level (Flesch Reading Ease - simplified)
            reading_ease = 0
            if sentence_count > 0 and word_count > 0:
                # Simplified calculation
                avg_words_per_sentence = word_count / sentence_count
                # Very basic syllable estimation (chars / 3)
                avg_syllables_per_word = len(text.replace(' ', '')) / word_count / 3
                reading_ease = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
                reading_ease = max(0, min(100, reading_ease))
            
            # Calculate score
            score = 100
            
            if word_count < 300:
                score -= 30
            elif word_count < 500:
                score -= 15
            
            if headings['h2'] == 0:
                score -= 10
            
            if avg_paragraph_length > 150:
                score -= 10
            
            if content_ratio < 10:
                score -= 15
            
            # Reading level scoring
            reading_level = "Unknown"
            if reading_ease >= 60:
                reading_level = "Easy (8th-9th grade)"
            elif reading_ease >= 50:
                reading_level = "Fairly Easy (10th-12th grade)"
                score -= 5
            elif reading_ease >= 30:
                reading_level = "Difficult (College level)"
                score -= 10
            else:
                reading_level = "Very Difficult (College graduate)"
                score -= 15
            
            return {
                "score": max(0, score),
                "word_count": word_count,
                "sentence_count": sentence_count,
                "paragraph_count": paragraph_count,
                "avg_sentence_length": round(avg_sentence_length, 1),
                "avg_paragraph_length": round(avg_paragraph_length, 1),
                "heading_structure": headings,
                "content_to_code_ratio": round(content_ratio, 2),
                "reading_ease_score": round(reading_ease, 1),
                "reading_level": reading_level,
                "status": "excellent" if score >= 80 else "good" if score >= 60 else "needs_improvement",
                "recommendations": self._get_content_recommendations(word_count, headings, avg_paragraph_length, content_ratio)
            }
            
        except Exception as e:
            self.results["errors"].append(f"Content quality audit failed: {str(e)}")
            return {}
    
    def _get_content_recommendations(self, word_count: int, headings: Dict, avg_para: float, ratio: float) -> list:
        """Generate content quality recommendations"""
        recommendations = []
        
        if word_count < 300:
            recommendations.append(f"Increase content length (currently {word_count} words, aim for 500+)")
        elif word_count < 500:
            recommendations.append(f"Consider adding more content (currently {word_count} words)")
        
        if headings['h2'] == 0:
            recommendations.append("Add H2 headings to structure your content")
        
        if headings['h2'] > 0 and headings['h3'] == 0:
            recommendations.append("Consider adding H3 subheadings for better content hierarchy")
        
        if avg_para > 100:
            recommendations.append(f"Break up long paragraphs (average {round(avg_para)} words)")
        
        if ratio < 15:
            recommendations.append(f"Improve content-to-code ratio (currently {round(ratio, 1)}%)")
        
        return recommendations
    
    
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
        
        # Run broken link check
        print("4. Checking for broken links...")
        self.results["broken_links"] = self.audit_broken_links()
        
        # Run image optimization audit
        print("5. Analyzing image optimization...")
        self.results["image_optimization"] = self.audit_image_optimization()
        
        # Run structured data validation
        print("6. Validating structured data...")
        self.results["structured_data"] = self.audit_structured_data()
        
        # Run content quality analysis
        print("7. Analyzing content quality...")
        self.results["content_quality"] = self.audit_content_quality()
        
        # Calculate overall score
        self.results["overall_score"] = self._calculate_overall_score()
        
        print(f"\n{'='*60}")
        print("Audit complete!")
        print(f"{'='*60}\n")
        
        return self.results
    
    def _calculate_overall_score(self) -> int:
        """Calculate overall audit score from all categories"""
        scores = []
        
        # Lighthouse category scores (weighted more heavily)
        lighthouse = self.results.get("lighthouse", {})
        categories = lighthouse.get("categories", {})
        
        for category_name, category_data in categories.items():
            score = category_data.get("score", 0)
            scores.append(score)
        
        # Add new audit scores
        if img_opt := self.results.get("image_optimization", {}).get("score"):
            scores.append(img_opt)
        
        if struct_data := self.results.get("structured_data", {}).get("score"):
            scores.append(struct_data)
        
        if content := self.results.get("content_quality", {}).get("score"):
            scores.append(content)
        
        # Broken links affects score
        broken = self.results.get("broken_links", {})
        if broken:
            broken_score = 100
            if broken.get("status") == "fail":
                broken_score = 50
            elif broken.get("status") == "warning":
                broken_score = 75
            scores.append(broken_score)
        
        # If we have scores, calculate average
        if scores:
            return int(sum(scores) / len(scores))
        
        # Fallback to manual scoring if Lighthouse failed
        manual_scores = []
        
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
        
        manual_scores.append(max(0, seo_score))
        
        # Security score (simplified)
        sec_score = 100
        sec = self.results.get("security", {})
        
        if not sec.get("https"):
            sec_score -= 40
        if not sec.get("security_headers", {}).get("strict_transport_security"):
            sec_score -= 15
        if not sec.get("security_headers", {}).get("x_frame_options"):
            sec_score -= 15
        
        manual_scores.append(max(0, sec_score))
        
        return int(sum(manual_scores) / len(manual_scores)) if manual_scores else 0
    
    def print_summary(self):
        """Print a human-readable summary of the audit"""
        print(f"\n{'='*60}")
        print(f"AUDIT SUMMARY FOR: {self.url}")
        print(f"{'='*60}")
        print(f"\nOverall Score: {self.results.get('overall_score', 0)}/100\n")
        
        # Lighthouse categories
        lighthouse = self.results.get("lighthouse", {})
        categories = lighthouse.get("categories", {})
        
        if categories:
            print("Lighthouse Scores:")
            for category_name, category_data in categories.items():
                score = category_data.get("score", 0)
                title = category_data.get("title", category_name)
                emoji = '✅' if score >= 90 else '⚠️' if score >= 50 else '❌'
                print(f"  {emoji} {title}: {score}/100")
            
            # Core Web Vitals
            metrics = lighthouse.get("metrics", {})
            core_web_vitals = metrics.get("coreWebVitals", {})
            
            if core_web_vitals:
                print("\nCore Web Vitals:")
                if lcp := core_web_vitals.get("lcp"):
                    rating_emoji = '✅' if lcp['rating'] == 'good' else '⚠️' if lcp['rating'] == 'needs-improvement' else '❌'
                    print(f"  {rating_emoji} LCP: {lcp.get('displayValue', 'N/A')} ({lcp.get('rating', 'N/A')})")
                if cls := core_web_vitals.get("cls"):
                    rating_emoji = '✅' if cls['rating'] == 'good' else '⚠️' if cls['rating'] == 'needs-improvement' else '❌'
                    print(f"  {rating_emoji} CLS: {cls.get('displayValue', 'N/A')} ({cls.get('rating', 'N/A')})")
                if tbt := core_web_vitals.get("tbt"):
                    rating_emoji = '✅' if tbt['rating'] == 'good' else '⚠️' if tbt['rating'] == 'needs-improvement' else '❌'
                    print(f"  {rating_emoji} TBT: {tbt.get('displayValue', 'N/A')} ({tbt.get('rating', 'N/A')})")
            
            # Top opportunities
            opportunities = lighthouse.get("opportunities", [])
            if opportunities:
                print("\nTop Opportunities for Improvement:")
                for i, opp in enumerate(opportunities[:3], 1):
                    print(f"  {i}. {opp.get('title', 'N/A')}")
                    if savings_ms := opp.get('savings', {}).get('ms'):
                        print(f"     Potential savings: {int(savings_ms)}ms")
        
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
        
        # Broken Links
        broken = self.results.get("broken_links", {})
        if broken:
            print("\nBroken Links:")
            status_emoji = '✅' if broken.get('status') == 'pass' else '⚠️' if broken.get('status') == 'warning' else '❌'
            print(f"  {status_emoji} Status: {broken.get('status', 'unknown')}")
            print(f"  - Checked: {broken.get('total_checked', 0)} links")
            print(f"  - Broken: {broken.get('broken_count', 0)}")
            if broken.get('broken_count', 0) > 0:
                print(f"  - First broken link: {broken.get('broken_links', [{}])[0].get('url', 'N/A')[:60]}...")
        
        # Image Optimization
        img_opt = self.results.get("image_optimization", {})
        if img_opt:
            print("\nImage Optimization:")
            score = img_opt.get('score', 0)
            emoji = '✅' if score >= 80 else '⚠️' if score >= 50 else '❌'
            print(f"  {emoji} Score: {score}/100")
            print(f"  - Total images: {img_opt.get('total_images', 0)}")
            issues = img_opt.get('issues', {})
            if issues.get('missing_alt_count', 0) > 0:
                print(f"  - Missing alt text: {issues['missing_alt_count']}")
            if issues.get('missing_dimensions_count', 0) > 0:
                print(f"  - Missing dimensions: {issues['missing_dimensions_count']}")
        
        # Structured Data
        struct = self.results.get("structured_data", {})
        if struct:
            print("\nStructured Data:")
            score = struct.get('score', 0)
            emoji = '✅' if score >= 80 else '⚠️' if score >= 50 else '❌'
            print(f"  {emoji} Score: {score}/100 ({struct.get('status', 'unknown')})")
            print(f"  - JSON-LD: {'✓' if struct.get('has_json_ld') else '✗'} ({struct.get('json_ld_count', 0)} found)")
            print(f"  - Open Graph: {'✓' if struct.get('has_open_graph') else '✗'}")
            print(f"  - Twitter Card: {'✓' if struct.get('has_twitter_card') else '✗'}")
        
        # Content Quality
        content = self.results.get("content_quality", {})
        if content:
            print("\nContent Quality:")
            score = content.get('score', 0)
            emoji = '✅' if score >= 80 else '⚠️' if score >= 60 else '❌'
            print(f"  {emoji} Score: {score}/100 ({content.get('status', 'unknown')})")
            print(f"  - Word count: {content.get('word_count', 0)}")
            print(f"  - Reading level: {content.get('reading_level', 'Unknown')}")
            print(f"  - Content/Code ratio: {content.get('content_to_code_ratio', 0)}%")
        
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