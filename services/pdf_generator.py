"""
PDF Generation Service - Create professional audit reports
Uses Playwright (headless Chromium) to render HTML template to pixel-perfect PDF
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, Any, List
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Directory where templates live
TEMPLATE_DIR = Path(__file__).parent
TEMPLATE_NAME = "audit_report_template.jinja2.html"


class PDFReportGenerator:
    """Generate professional PDF reports from audit results using Playwright HTML-to-PDF"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.output_dir = Path("uploads/pdfs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True
        )

    def generate_audit_report(
        self,
        job_id: str,
        audit_results: Dict[str, Any],
        lead_info: Dict[str, str],
        embed_token_data: Dict[str, str],
        filename: Optional[str] = None
    ) -> str:
        """
        Generate PDF audit report using Playwright HTML-to-PDF

        Args:
            job_id: Audit job ID
            audit_results: Audit results dict with score, issues, etc
            lead_info: {"first_name", "last_name", "email", "company"}
            embed_token_data: {"agency_name", "primary_color", "logo_url"}
            filename: Custom filename (auto-generated if not provided)

        Returns:
            Path to generated PDF
        """
        try:
            filename = filename or f"audit_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = self.output_dir / filename

            # Build template context from audit data
            context = self._build_template_context(
                audit_results, lead_info, embed_token_data, job_id
            )

            # Render the Jinja2 template
            template = self.jinja_env.get_template(TEMPLATE_NAME)
            html_content = template.render(**context)

            # Convert HTML to PDF via Playwright
            asyncio.run(self._html_to_pdf(html_content, str(filepath)))

            logger.info(f"[PDF] Generated report: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"[PDF] Error generating report: {e}")
            raise

    async def _html_to_pdf(self, html_content: str, output_path: str) -> None:
        """Use Playwright headless Chromium to render HTML to PDF"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Set the HTML content and wait for fonts to load
            await page.set_content(html_content, wait_until="networkidle")

            # Give Google Fonts a moment to fully render
            await page.wait_for_timeout(1500)

            # Generate PDF with A4 page size
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )

            await browser.close()

    def _build_template_context(
        self,
        results: Dict[str, Any],
        lead_info: Dict[str, str],
        branding: Dict[str, str],
        job_id: str
    ) -> Dict[str, Any]:
        """Extract and normalize all audit data into template-friendly context"""

        # ── Basic Info ──
        agency_name = branding.get("agency_name", "AuditFlow")
        target_url = results.get("url", lead_info.get("website_url", "N/A"))
        target_url_short = target_url.replace("https://", "").replace("http://", "").rstrip("/")
        audit_date = datetime.now().strftime("%B %d, %Y")
        overall_score = results.get("overall_score", results.get("score", 0))

        client_name = f"{lead_info.get('first_name', '')} {lead_info.get('last_name', '')}".strip()
        client_company = lead_info.get("company", "")

        # ── Lighthouse Categories ──
        lighthouse_categories = self._extract_lighthouse(results)

        # ── Core Web Vitals ──
        core_web_vitals = self._extract_core_web_vitals(results)

        # ── Optimization Opportunities ──
        optimization_opportunities = self._extract_opportunities(results)

        # ── Technical SEO ──
        tech_seo = self._extract_tech_seo(results)

        # ── Security ──
        security = self._extract_security(results)

        # ── Broken Links ──
        broken_links_data = results.get("broken_links", {})
        broken_links_count = broken_links_data.get("broken_count", 0)
        total_links_checked = broken_links_data.get("total_checked", broken_links_data.get("total_found", 0))
        broken_links_list = broken_links_data.get("broken_links", [])

        # ── Content Quality ──
        content = self._extract_content_quality(results)

        # ── Structured Data ──
        structured_data = self._extract_structured_data(results)

        # ── Image Optimization ──
        images, image_recommendations = self._extract_image_optimization(results)

        # ── Content Recommendations ──
        content_recommendations = results.get("content_quality", {}).get("recommendations", [])
        if not content_recommendations:
            content_recommendations = self._generate_content_recommendations(content, tech_seo)

        return {
            "agency_name": agency_name,
            "target_url": target_url,
            "target_url_short": target_url_short,
            "audit_date": audit_date,
            "overall_score": overall_score,
            "client_name": client_name,
            "client_company": client_company,
            "lighthouse_categories": lighthouse_categories,
            "core_web_vitals": core_web_vitals,
            "optimization_opportunities": optimization_opportunities,
            "tech_seo": tech_seo,
            "security": security,
            "broken_links_count": broken_links_count,
            "total_links_checked": total_links_checked,
            "broken_links_list": broken_links_list,
            "content": content,
            "structured_data": structured_data,
            "images": images,
            "image_recommendations": image_recommendations,
            "content_recommendations": content_recommendations,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Data extraction helpers
    # ─────────────────────────────────────────────────────────────────────

    def _extract_lighthouse(self, results: Dict) -> List[Dict]:
        """Extract Lighthouse category scores"""
        categories = []
        lh = results.get("lighthouse", {}).get("categories", {})

        category_map = [
            ("performance", "Performance"),
            ("accessibility", "Accessibility"),
            ("best-practices", "Best Practices"),
            ("seo", "SEO"),
        ]

        for key, title in category_map:
            raw_score = lh.get(key, {}).get("score", 0)
            # Lighthouse scores can be 0-1 or 0-100
            score = int(raw_score * 100) if isinstance(raw_score, float) and raw_score <= 1 else int(raw_score)
            categories.append({"key": key, "title": title, "score": score})

        return categories

    def _extract_core_web_vitals(self, results: Dict) -> List[Dict]:
        """Extract Core Web Vitals from lighthouse audits"""
        vitals = []
        audits = results.get("lighthouse", {}).get("audits", {})

        vital_map = [
            ("largest-contentful-paint", "LCP (Largest Contentful Paint)", "s", 2.5, 4.0),
            ("max-potential-fid", "FID (First Input Delay)", "ms", 100, 300),
            ("cumulative-layout-shift", "CLS (Cumulative Layout Shift)", "", 0.1, 0.25),
            ("first-contentful-paint", "FCP (First Contentful Paint)", "s", 1.8, 3.0),
            ("interactive", "TTI (Time to Interactive)", "s", 3.8, 7.3),
        ]

        for key, label, unit, good_threshold, poor_threshold in vital_map:
            audit = audits.get(key, {})
            numeric = audit.get("numericValue")

            if numeric is not None:
                if unit == "s":
                    display = f"{numeric / 1000:.1f}s"
                    val = numeric / 1000
                elif unit == "ms":
                    display = f"{numeric:.0f}ms"
                    val = numeric
                else:
                    display = f"{numeric:.2f}"
                    val = numeric

                if val <= good_threshold:
                    status = "good"
                elif val <= poor_threshold:
                    status = "avg"
                else:
                    status = "poor"
            else:
                display = "N/A"
                status = "avg"

            vitals.append({"label": label, "value": display, "status": status})

        return vitals

    def _extract_opportunities(self, results: Dict) -> List[Dict]:
        """Extract optimization opportunities from lighthouse audits"""
        opportunities = []
        audits = results.get("lighthouse", {}).get("audits", {})

        opp_keys = [
            "render-blocking-resources",
            "uses-responsive-images",
            "offscreen-images",
            "unminified-css",
            "unminified-javascript",
            "unused-css-rules",
            "unused-javascript",
            "uses-optimized-images",
            "modern-image-formats",
            "uses-text-compression",
            "uses-rel-preconnect",
            "server-response-time",
            "redirects",
            "uses-rel-preload",
            "efficient-animated-content",
            "duplicated-javascript",
            "legacy-javascript",
            "total-byte-weight",
            "dom-size",
        ]

        for key in opp_keys:
            audit = audits.get(key, {})
            if audit.get("score") is not None and audit["score"] < 1:
                opportunities.append({
                    "title": audit.get("title", key),
                    "description": (audit.get("description", "")[:120] + "...") if len(audit.get("description", "")) > 120 else audit.get("description", ""),
                })

        # If no lighthouse opportunities, generate from image/content data
        if not opportunities:
            img = results.get("image_optimization", {})
            if img.get("recommendations"):
                for rec in img["recommendations"][:2]:
                    opportunities.append({"title": "Image Optimization", "description": rec})

            cq = results.get("content_quality", {})
            if cq.get("recommendations"):
                for rec in cq["recommendations"][:2]:
                    opportunities.append({"title": "Content Improvement", "description": rec})

        return opportunities[:4]

    def _extract_tech_seo(self, results: Dict) -> Dict:
        """Extract technical SEO data"""
        ts = results.get("technical_seo", {})

        title_data = ts.get("title", {})
        meta_data = ts.get("meta_description", {})
        canonical_data = ts.get("canonical", {})

        if isinstance(title_data, dict):
            title_present = title_data.get("present", False)
            title_length = title_data.get("length", 0)
        else:
            title_present = bool(title_data)
            title_length = len(str(title_data)) if title_data else 0

        if isinstance(meta_data, dict):
            meta_present = meta_data.get("present", False)
            meta_length = meta_data.get("length", len(str(meta_data.get("content", ""))))
        else:
            meta_present = bool(meta_data)
            meta_length = len(str(meta_data)) if meta_data else 0

        if isinstance(canonical_data, dict):
            canonical_present = canonical_data.get("present", False)
        else:
            canonical_present = bool(canonical_data)

        return {
            "title_present": title_present,
            "title_length": title_length,
            "meta_present": meta_present,
            "meta_length": meta_length,
            "canonical_present": canonical_present,
            "robots_txt": ts.get("robots_txt", False),
            "sitemap_xml": ts.get("sitemap_xml", False),
        }

    def _extract_security(self, results: Dict) -> Dict:
        """Extract security check data"""
        sec = results.get("security", {})
        headers = sec.get("security_headers", {})

        return {
            "https": sec.get("https", False),
            "hsts": headers.get("strict_transport_security", False),
            "xcto": headers.get("x_content_type_options", False),
            "xfo": headers.get("x_frame_options", False),
            "csp": headers.get("content_security_policy", False),
        }

    def _extract_content_quality(self, results: Dict) -> Dict:
        """Extract content quality metrics"""
        cq = results.get("content_quality", {})
        headings = cq.get("heading_structure", {})

        return {
            "word_count": cq.get("word_count", 0),
            "reading_level": cq.get("reading_level", "N/A"),
            "reading_ease": cq.get("reading_ease_score", 0),
            "content_to_code_ratio": cq.get("content_to_code_ratio", 0),
            "headings": headings if headings else {"h1": 0, "h2": 0, "h3": 0},
        }

    def _extract_structured_data(self, results: Dict) -> Dict:
        """Extract structured data info"""
        sd = results.get("structured_data", {})

        return {
            "has_json_ld": sd.get("has_json_ld", False),
            "json_ld_types": sd.get("json_ld_types", []),
            "has_og": sd.get("has_open_graph", sd.get("has_og", False)),
            "has_twitter": sd.get("has_twitter_cards", sd.get("has_twitter", False)),
        }

    def _extract_image_optimization(self, results: Dict):
        """Extract image optimization data"""
        img = results.get("image_optimization", {})
        issues = img.get("issues", {})

        missing_alt = 0
        if isinstance(issues, dict):
            missing_alt = issues.get("missing_alt_count", 0)
        elif isinstance(issues, list):
            missing_alt = len([i for i in issues if "alt" in str(i).lower()])

        images = {
            "total": img.get("total_images", 0),
            "missing_alt": missing_alt,
            "score": img.get("score", 0),
        }

        recommendations = img.get("recommendations", [])

        return images, recommendations

    def _generate_content_recommendations(self, content: Dict, tech_seo: Dict) -> List[str]:
        """Generate fallback content recommendations if none provided"""
        recs = []

        if content.get("word_count", 0) < 500:
            recs.append(f"Increase content length (currently {content.get('word_count', 0)} words, aim for 500+)")
        if content.get("reading_ease", 100) < 40:
            recs.append("Simplify content language for broader audience readability")
        if content.get("content_to_code_ratio", 100) < 10:
            recs.append(f"Improve content-to-code ratio (currently {content.get('content_to_code_ratio', 0)}%)")

        headings = content.get("headings", {})
        if headings.get("h1", 0) != 1:
            recs.append("Ensure exactly one H1 heading per page")
        if headings.get("h2", 0) == 0:
            recs.append("Add H2 subheadings for better content structure")

        if not recs:
            recs.append("Content quality looks good — maintain current standards")

        return recs