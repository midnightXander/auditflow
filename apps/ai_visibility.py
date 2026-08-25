"""
AI Visibility Auditor - AI Answer-Engine Citability Audit Engine
Scores how likely a site is to be parsed, understood, and cited by AI
systems (ChatGPT, Perplexity, Gemini, Claude, AI Overviews, etc.)

Follows the same conventions as auditor.py (WebsiteAuditor):
  - self.results dict accumulates every category
  - self.results["errors"] collects non-fatal failures
  - each audit_* method returns a dict with its own "score"
  - run_full_audit() orchestrates everything and returns self.results

LAYER 1 (static analysis) - implemented here, zero external dependencies
beyond fetching the target site's own pages. Runs in a few seconds.
  1. Entity clarity        -> audit_entity_clarity()
  2. E-E-A-T signals        -> audit_eeat_signals()
  3. Content structure      -> audit_content_structure()
  4. AI bot crawlability    -> audit_crawlability()

LAYER 2 (live citation check) - implemented here but NOT called by
run_full_audit() by default. Opt-in only (Pro/Agency), requires
PERPLEXITY_API_KEY / BRAVE_SEARCH_API_KEY. See check_ai_citations().

NOTE on scope (read this before wiring it in):
  - Google Knowledge Graph lookup (mentioned in the original spec as part
    of "entity clarity") is NOT implemented here. It's a live external API
    call, so it belongs in Layer 2, not the zero-dependency Layer 1 engine.
    A stub + TODO is left in audit_entity_clarity() for when you add it.
  - Page speed is approximated from a single response-timing sample, not a
    full Lighthouse run. If you want closer numbers, this can pull the
    "performance" score straight off the sibling Audit row for the same
    domain instead of re-measuring - see the routes file for a TODO on this.
  - NAP (name/address/phone) consistency is checked for *presence* in
    schema, not cross-referenced against the visible page text word-for-word
    (that needs NLP/entity matching to do reliably - flagged as a fast-follow
    in the docs).
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
import extruct
from bs4 import BeautifulSoup

# ── Reference data ──────────────────────────────────────────────────────

# AI crawler user-agent tokens we check for in robots.txt.
# Key = exact token the bot identifies itself with, value = human label.
AI_BOTS = {
    "GPTBot": "OpenAI (ChatGPT)",
    "OAI-SearchBot": "OpenAI (ChatGPT Search)",
    "ChatGPT-User": "OpenAI (ChatGPT browsing plugin)",
    "ClaudeBot": "Anthropic (Claude)",
    "Claude-Web": "Anthropic (Claude browsing)",
    "anthropic-ai": "Anthropic (training crawler)",
    "PerplexityBot": "Perplexity",
    "Perplexity-User": "Perplexity (user-triggered browsing)",
    "Google-Extended": "Google (Gemini / AI Overviews training)",
    "Bingbot": "Microsoft (Copilot)",
    "cohere-ai": "Cohere",
}

# Schema.org @type values that materially help an AI system recognise
# what an entity/page *is*. Used to score schema coverage.
HIGH_VALUE_SCHEMA_TYPES = {
    "Organization", "LocalBusiness", "Corporation", "Person", "Product",
    "Article", "NewsArticle", "BlogPosting", "FAQPage", "HowTo",
    "Review", "AggregateRating", "BreadcrumbList", "WebSite", "WebPage",
}

# sameAs domains that connect an entity to a recognised knowledge source.
SAMEAS_DOMAINS = {
    "wikidata.org": "Wikidata",
    "wikipedia.org": "Wikipedia",
    "crunchbase.com": "Crunchbase",
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "github.com": "GitHub",
}

# Candidate paths checked for E-E-A-T trust pages. First 200 wins.
ABOUT_PATHS = ["/about", "/about-us", "/company", "/who-we-are"]
CONTACT_PATHS = ["/contact", "/contact-us", "/get-in-touch"]
PRIVACY_PATHS = ["/privacy", "/privacy-policy"]
TERMS_PATHS = ["/terms", "/terms-of-service", "/terms-and-conditions", "/tos"]

DEFINITION_PATTERN = re.compile(
    r"[A-Z][\w\s\-']{2,60}\s+(is|are|refers to|means)\s+(a|an|the)\s+\w+", re.MULTILINE
)
STAT_PATTERN = re.compile(r"\b\d{1,3}(\.\d+)?\s?%|\baccording to\b|\bstudy (found|shows)\b", re.IGNORECASE)
QUESTION_HEADING_PATTERN = re.compile(r"^(what|how|why|when|where|who|which|can|is|does)\b.{0,100}\?", re.IGNORECASE)

DEFAULT_UA = "Mozilla/5.0 (compatible; OutauditsBot/1.0; +https://outaudits.com/bot)"


class AIVisibilityAuditor:
    """Layer 1 (static) + Layer 2 (optional live citation check) AI-visibility audit."""

    def __init__(self, url: str, industry: Optional[str] = None):
        self.url = self._normalize_url(url)
        self.industry = industry  # reserved for future industry-specific schema recommendations
        self.results: Dict[str, Any] = {
            "url": self.url,
            "audit_date": datetime.utcnow().isoformat(),
            "entity_clarity": {},
            "eeat_signals": {},
            "content_structure": {},
            "crawlability": {},
            "ai_citations": None,  # only populated if Layer 2 is run
            "errors": [],
        }
        self._html: Optional[str] = None
        self._soup: Optional[BeautifulSoup] = None
        self._headers: Dict[str, str] = {}
        self._response_time_ms: Optional[float] = None
        self._schema_nodes: List[Dict[str, Any]] = []  # flattened JSON-LD nodes

    def _normalize_url(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url.rstrip("/")

    # ── fetching helpers ────────────────────────────────────────────────

    async def _fetch(self, session: aiohttp.ClientSession, url: str, timeout: int = 10):
        try:
            start = time.monotonic()
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": DEFAULT_UA},
                allow_redirects=True,
            ) as resp:
                text = await resp.text(errors="replace")
                elapsed_ms = (time.monotonic() - start) * 1000
                return resp.status, resp.headers, text, elapsed_ms
        except Exception as e:
            self.results["errors"].append(f"Fetch failed for {url}: {str(e)}")
            return None, {}, "", None

    async def _page_exists(self, session: aiohttp.ClientSession, candidate_paths: List[str]) -> Optional[str]:
        """Return the first candidate path that resolves with a 200, else None."""
        parsed = urlparse(self.url)
        for path in candidate_paths:
            target = f"{parsed.scheme}://{parsed.netloc}{path}"
            try:
                async with session.get(
                    target,
                    timeout=aiohttp.ClientTimeout(total=6),
                    headers={"User-Agent": DEFAULT_UA},
                    allow_redirects=True,
                ) as resp:
                    if resp.status == 200:
                        return path
            except Exception:
                continue
        return None

    async def _fetch_page_and_robots(self, session: aiohttp.ClientSession) -> str:
        """Fetch the target page and robots.txt. Returns the raw robots.txt text."""
        status, headers, html, elapsed_ms = await self._fetch(session, self.url)
        self._headers = headers
        self._html = html
        self._response_time_ms = elapsed_ms
        self._soup = BeautifulSoup(html, "html.parser") if html else None

        parsed = urlparse(self.url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        robots_status, _, robots_text, _ = await self._fetch(session, robots_url, timeout=5)
        return robots_text if robots_status == 200 else ""

    def _extract_schema(self) -> None:
        """Parse JSON-LD (+ microdata/opengraph) with extruct and flatten into self._schema_nodes."""
        if not self._html:
            return
        try:
            data = extruct.extract(
                self._html,
                base_url=self.url,
                syntaxes=["json-ld", "microdata", "opengraph"],
                uniform=True,
            )
        except Exception as e:
            self.results["errors"].append(f"extruct parsing failed: {str(e)}")
            data = {"json-ld": [], "microdata": [], "opengraph": []}

        self._extruct_data = data

        def flatten(node):
            if isinstance(node, dict):
                self._schema_nodes.append(node)
                graph = node.get("@graph")
                if isinstance(graph, list):
                    for g in graph:
                        flatten(g)
            elif isinstance(node, list):
                for n in node:
                    flatten(n)

        for entry in data.get("json-ld", []):
            flatten(entry)

    def _types_for_node(self, node: Dict[str, Any]) -> List[str]:
        t = node.get("@type")
        if isinstance(t, str):
            return [t]
        if isinstance(t, list):
            return [x for x in t if isinstance(x, str)]
        return []

    # ── 1. entity clarity (30%) ─────────────────────────────────────────

    def audit_entity_clarity(self) -> Dict[str, Any]:
        """
        Schema.org coverage, sameAs links to knowledge sources, and basic
        NAP (name/address/phone) presence in structured data.
        """
        try:
            found_types = set()
            sameas_found = []
            has_address = False
            has_telephone = False
            has_name = False

            for node in self._schema_nodes:
                for t in self._types_for_node(node):
                    found_types.add(t)

                same_as = node.get("sameAs")
                same_as_list = same_as if isinstance(same_as, list) else ([same_as] if same_as else [])
                for link in same_as_list:
                    if not isinstance(link, str):
                        continue
                    for domain, label in SAMEAS_DOMAINS.items():
                        if domain in link:
                            sameas_found.append({"domain": label, "url": link})

                if node.get("address"):
                    has_address = True
                if node.get("telephone"):
                    has_telephone = True
                if node.get("name"):
                    has_name = True

            high_value_found = found_types & HIGH_VALUE_SCHEMA_TYPES

            # scoring: JSON-LD presence (30) + type coverage (30, capped) +
            # sameAs links (25, capped) + NAP presence in schema (15)
            score = 0
            if self._schema_nodes:
                score += 30
            score += min(30, len(high_value_found) * 10)
            score += min(25, len(sameas_found) * 5)
            if has_address and has_telephone:
                score += 15
            elif has_name:
                score += 5

            return {
                "score": min(100, score),
                "has_json_ld": bool(self._schema_nodes),
                "json_ld_node_count": len(self._schema_nodes),
                "schema_types_found": sorted(found_types),
                "high_value_types_found": sorted(high_value_found),
                "high_value_types_missing": sorted(HIGH_VALUE_SCHEMA_TYPES - found_types),
                "sameas_links": sameas_found,
                "nap_signals": {
                    "name_in_schema": has_name,
                    "address_in_schema": has_address,
                    "telephone_in_schema": has_telephone,
                },
                # Live Knowledge Graph lookup is a Layer 2 concern (external API) -
                # not run here. See module docstring.
                "knowledge_graph_checked": False,
                "status": "excellent" if score >= 80 else "good" if score >= 55 else "fair" if score >= 30 else "poor",
                "recommendations": self._entity_clarity_recommendations(
                    bool(self._schema_nodes), high_value_found, sameas_found, has_address, has_telephone
                ),
            }
        except Exception as e:
            self.results["errors"].append(f"Entity clarity audit failed: {str(e)}")
            return {}

    def _entity_clarity_recommendations(self, has_json_ld, high_value_found, sameas_found, has_address, has_telephone) -> List[str]:
        recs = []
        if not has_json_ld:
            recs.append("Add JSON-LD structured data - AI systems rely on it far more than visible text to identify what an entity is.")
        if "Organization" not in high_value_found and "LocalBusiness" not in high_value_found:
            recs.append("Add an Organization or LocalBusiness schema block so AI systems can anchor the brand as a distinct entity.")
        if not sameas_found:
            recs.append("Add sameAs links (Wikidata, Crunchbase, LinkedIn, official social profiles) to connect the entity to sources AI systems already trust.")
        if not (has_address and has_telephone):
            recs.append("Include address and telephone in Organization/LocalBusiness schema for consistent NAP signals.")
        return recs

    # ── 2. E-E-A-T signals (30%) ────────────────────────────────────────

    async def audit_eeat_signals(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Experience, Expertise, Authoritativeness, Trust signals: author
        schema, about/contact/privacy/terms pages, HTTPS + security headers.
        """
        try:
            has_author_schema = False
            for node in self._schema_nodes:
                if "author" in node or set(self._types_for_node(node)) & {"Person"}:
                    has_author_schema = True
                    break

            about_path, contact_path, privacy_path, terms_path = await self._gather_trust_pages(session)

            https = self.url.startswith("https://")
            headers = self._headers or {}
            security_headers = {
                "strict_transport_security": "Strict-Transport-Security" in headers,
                "x_frame_options": "X-Frame-Options" in headers,
                "x_content_type_options": "X-Content-Type-Options" in headers,
                "content_security_policy": "Content-Security-Policy" in headers,
            }
            security_header_count = sum(1 for v in security_headers.values() if v)

            score = 0
            if has_author_schema:
                score += 20
            if about_path:
                score += 15
            if contact_path:
                score += 15
            if https:
                score += 15
            score += min(10, security_header_count * 3)
            if privacy_path:
                score += 12
            if terms_path:
                score += 13

            return {
                "score": min(100, score),
                "author_schema_present": has_author_schema,
                "about_page": {"found": bool(about_path), "path": about_path},
                "contact_page": {"found": bool(contact_path), "path": contact_path},
                "privacy_policy": {"found": bool(privacy_path), "path": privacy_path},
                "terms_of_service": {"found": bool(terms_path), "path": terms_path},
                "https": https,
                "security_headers": security_headers,
                "status": "excellent" if score >= 80 else "good" if score >= 55 else "fair" if score >= 30 else "poor",
                "recommendations": self._eeat_recommendations(
                    has_author_schema, about_path, contact_path, https, security_header_count, privacy_path, terms_path
                ),
            }
        except Exception as e:
            self.results["errors"].append(f"E-E-A-T audit failed: {str(e)}")
            return {}

    async def _gather_trust_pages(self, session: aiohttp.ClientSession):
        # sequential on purpose - keeps concurrent connections to the target
        # site low and polite; adds ~1-2s total, acceptable for Layer 1.
        about = await self._page_exists(session, ABOUT_PATHS)
        contact = await self._page_exists(session, CONTACT_PATHS)
        privacy = await self._page_exists(session, PRIVACY_PATHS)
        terms = await self._page_exists(session, TERMS_PATHS)
        return about, contact, privacy, terms

    def _eeat_recommendations(self, has_author_schema, about_path, contact_path, https, sec_header_count, privacy_path, terms_path) -> List[str]:
        recs = []
        if not has_author_schema:
            recs.append("Add Person/author schema with jobTitle and url to bylines - AI systems weigh authored content more heavily when the author is a verifiable entity.")
        if not about_path:
            recs.append("Add a clear About page - it's one of the strongest, cheapest trust signals for both search and AI answer engines.")
        if not contact_path:
            recs.append("Add a Contact page with verifiable business details.")
        if not https:
            recs.append("Move the site to HTTPS - a baseline trust requirement for citation.")
        if sec_header_count < 2:
            recs.append("Add standard security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP).")
        if not privacy_path:
            recs.append("Add a Privacy Policy page.")
        if not terms_path:
            recs.append("Add a Terms of Service page.")
        return recs

    # ── 3. content structure for LLM extraction (25%) ───────────────────

    def audit_content_structure(self) -> Dict[str, Any]:
        """
        FAQ patterns, heading hierarchy, definition-style sentences,
        stats/citations, and freshness signals.
        """
        try:
            if not self._soup:
                return {}

            # FAQ: schema-based or visible question-style headings
            has_faq_schema = any("FAQPage" in self._types_for_node(n) for n in self._schema_nodes)
            question_headings = [
                h.get_text(strip=True) for h in self._soup.find_all(["h2", "h3", "h4"])
                if QUESTION_HEADING_PATTERN.match(h.get_text(strip=True))
            ]
            has_faq_pattern = has_faq_schema or len(question_headings) >= 2

            # Heading hierarchy
            headings = {f"h{i}": len(self._soup.find_all(f"h{i}")) for i in range(1, 7)}
            heading_issues = []
            if headings["h1"] == 0:
                heading_issues.append("No H1 tag found")
            elif headings["h1"] > 1:
                heading_issues.append(f"Multiple H1 tags found ({headings['h1']})")
            if headings["h2"] == 0 and (headings["h3"] > 0 or headings["h4"] > 0):
                heading_issues.append("Heading levels are skipped (H3/H4 used without H2)")

            # Definition-style sentences ("X is a Y that...")
            body_text = self._soup.get_text(separator=" ", strip=True)
            definition_matches = DEFINITION_PATTERN.findall(body_text)
            has_definitions = len(definition_matches) > 0

            # Stats / citations
            stat_matches = STAT_PATTERN.findall(body_text)
            external_links = [
                a.get("href") for a in self._soup.find_all("a", href=True)
                if a.get("href", "").startswith("http") and urlparse(self.url).netloc not in a.get("href", "")
            ]
            has_citations = len(stat_matches) > 0 or len(external_links) >= 3

            # Freshness: dates in schema, or <time>/meta tags
            has_freshness = any(
                node.get("datePublished") or node.get("dateModified") for node in self._schema_nodes
            )
            if not has_freshness:
                has_freshness = bool(self._soup.find("time")) or bool(
                    self._soup.find("meta", attrs={"property": "article:modified_time"})
                )

            score = 0
            if has_faq_pattern:
                score += 25
            score += max(0, 20 - len(heading_issues) * 10)
            if has_definitions:
                score += 20
            if has_citations:
                score += 15
            if has_freshness:
                score += 20

            return {
                "score": min(100, score),
                "has_faq_schema": has_faq_schema,
                "question_style_headings": question_headings[:10],
                "has_faq_pattern": has_faq_pattern,
                "heading_structure": headings,
                "heading_issues": heading_issues,
                "has_definition_patterns": has_definitions,
                "definition_examples": [m[0] if isinstance(m, tuple) else m for m in definition_matches[:3]],
                "has_stats_or_citations": has_citations,
                "external_link_count": len(external_links),
                "has_freshness_signals": has_freshness,
                "status": "excellent" if score >= 80 else "good" if score >= 55 else "fair" if score >= 30 else "poor",
                "recommendations": self._content_structure_recommendations(
                    has_faq_pattern, heading_issues, has_definitions, has_citations, has_freshness
                ),
            }
        except Exception as e:
            self.results["errors"].append(f"Content structure audit failed: {str(e)}")
            return {}

    def _content_structure_recommendations(self, has_faq, heading_issues, has_definitions, has_citations, has_freshness) -> List[str]:
        recs = []
        if not has_faq:
            recs.append("Add an FAQ section (with FAQPage schema) - Q&A format maps directly to how people phrase questions to AI assistants.")
        if heading_issues:
            recs.append("Fix heading hierarchy so content can be reliably sectioned and extracted (" + "; ".join(heading_issues) + ").")
        if not has_definitions:
            recs.append("Open key sections with a plain definition sentence (\"X is a Y that...\") - this is the exact shape LLMs lift as an extractable fact.")
        if not has_citations:
            recs.append("Back claims with statistics and links to sources - citation-backed content is preferred for AI answers.")
        if not has_freshness:
            recs.append("Add publish/modified dates (visible and in schema) so AI systems can judge content freshness.")
        return recs

    # ── 4. AI bot crawlability (15%) ─────────────────────────────────────

    def audit_crawlability(self, robots_txt: str) -> Dict[str, Any]:
        """Which AI crawlers are allowed by robots.txt, plus a response-time proxy for speed."""
        try:
            bot_status = {}
            if robots_txt:
                blocks = self._parse_robots_blocks(robots_txt)
                for bot, label in AI_BOTS.items():
                    disallowed = self._bot_is_disallowed(blocks, bot)
                    bot_status[bot] = {"label": label, "allowed": not disallowed}
            else:
                # No robots.txt at all = nothing is blocked
                for bot, label in AI_BOTS.items():
                    bot_status[bot] = {"label": label, "allowed": True}

            allowed_count = sum(1 for v in bot_status.values() if v["allowed"])
            total_bots = len(bot_status)

            score = 0
            score += 10 if robots_txt else 5  # having a robots.txt at all is a mild positive (explicit > implicit)
            score += round((allowed_count / total_bots) * 60) if total_bots else 0

            if self._response_time_ms is not None:
                if self._response_time_ms < 800:
                    score += 30
                elif self._response_time_ms < 2000:
                    score += 15
            else:
                score += 15  # unknown - don't fully penalise

            blocked = [v["label"] for v in bot_status.values() if not v["allowed"]]

            return {
                "score": min(100, score),
                "robots_txt_found": bool(robots_txt),
                "bot_status": bot_status,
                "blocked_bots": blocked,
                "response_time_ms": round(self._response_time_ms) if self._response_time_ms else None,
                "status": "excellent" if score >= 80 else "good" if score >= 55 else "fair" if score >= 30 else "poor",
                "recommendations": self._crawlability_recommendations(blocked),
            }
        except Exception as e:
            self.results["errors"].append(f"Crawlability audit failed: {str(e)}")
            return {}

    def _parse_robots_blocks(self, robots_txt: str) -> Dict[str, List[str]]:
        """Very small robots.txt parser: {user-agent: [disallow paths]}. Good enough for bot-level allow/block checks."""
        blocks: Dict[str, List[str]] = {}
        current_agents: List[str] = []
        for raw_line in robots_txt.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                if current_agents and blocks.get(current_agents[0]) is None:
                    pass
                current_agents = [value]
                blocks.setdefault(value, [])
            elif key == "disallow" and current_agents:
                for agent in current_agents:
                    blocks.setdefault(agent, [])
                    if value:
                        blocks[agent].append(value)
        return blocks

    def _bot_is_disallowed(self, blocks: Dict[str, List[str]], bot: str) -> bool:
        # Specific bot rule wins; otherwise fall back to wildcard "*" rule.
        if bot in blocks:
            return "/" in blocks[bot]
        if "*" in blocks:
            return "/" in blocks["*"]
        return False

    def _crawlability_recommendations(self, blocked: List[str]) -> List[str]:
        recs = []
        if blocked:
            recs.append(f"robots.txt currently blocks: {', '.join(blocked)}. Allow these if you want the site eligible for AI citations.")
        return recs

    # ── scoring + findings ───────────────────────────────────────────────

    def _calculate_scores(self) -> Dict[str, Any]:
        entity = self.results["entity_clarity"].get("score", 0)
        eeat = self.results["eeat_signals"].get("score", 0)
        content = self.results["content_structure"].get("score", 0)
        crawl = self.results["crawlability"].get("score", 0)

        overall = round(entity * 0.30 + eeat * 0.30 + content * 0.25 + crawl * 0.15)
        return {
            "overall_score": overall,
            "sub_scores": {
                "entity_clarity": entity,
                "eeat_signals": eeat,
                "content_structure": content,
                "crawlability": crawl,
            },
            "weights": {
                "entity_clarity": 0.30,
                "eeat_signals": 0.30,
                "content_structure": 0.25,
                "crawlability": 0.15,
            },
        }

    def _build_findings(self) -> List[Dict[str, Any]]:
        """Collect every recommendation across categories into one impact-ranked list."""
        weight_by_category = {
            "entity_clarity": 9,
            "eeat_signals": 8,
            "content_structure": 7,
            "crawlability": 6,
        }
        findings = []
        for category, weight in weight_by_category.items():
            for rec in self.results.get(category, {}).get("recommendations", []):
                findings.append({
                    "category": category,
                    "recommendation": rec,
                    "impact": weight,
                })
        findings.sort(key=lambda f: f["impact"], reverse=True)
        return findings

    # ── orchestration ────────────────────────────────────────────────────

    async def run_full_audit(self) -> Dict[str, Any]:
        """Run the full Layer 1 static AI-visibility audit."""
        
        async with aiohttp.ClientSession() as session:
            print("Session: ",session)
            robots_txt = await self._fetch_page_and_robots(session)

            if not self._html:
                self.results["errors"].append("Could not fetch target page - audit aborted.")
                self.results["overall_score"] = 0
                return self.results

            self._extract_schema()

            self.results["entity_clarity"] = self.audit_entity_clarity()
            self.results["eeat_signals"] = await self.audit_eeat_signals(session)
            self.results["content_structure"] = self.audit_content_structure()
            self.results["crawlability"] = self.audit_crawlability(robots_txt)

        scoring = self._calculate_scores()
        self.results["overall_score"] = scoring["overall_score"]
        self.results["sub_scores"] = scoring["sub_scores"]
        self.results["score_weights"] = scoring["weights"]
        self.results["findings"] = self._build_findings()
        self.results["top_fixes"] = [f["recommendation"] for f in self.results["findings"][:5]]

        return self.results

    # ── Layer 2: live AI citation check (optional, NOT called by run_full_audit) ──

    async def check_ai_citations(self, brand_queries: List[str], perplexity_api_key: Optional[str] = None,
                                  brave_api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Send brand_queries to Perplexity and Brave Search APIs and check whether
        this site's domain shows up in the citations/results. Opt-in (Pro/Agency),
        costs real API credits, so it is never called automatically.

        Wire this up from the route/task layer once you decide where the API
        keys live (env vars vs. per-user BYO keys) - see the markdown doc.
        """
        domain = urlparse(self.url).netloc.replace("www.", "")
        citation_result = {
            "domain_checked": domain,
            "queries": brand_queries,
            "perplexity": {"checked": False, "cited": False, "citations": []},
            "brave": {"checked": False, "cited": False, "results": []},
        }

        async with aiohttp.ClientSession() as session:
            if perplexity_api_key:
                citation_result["perplexity"] = await self._check_perplexity(session, brand_queries, domain, perplexity_api_key)
            if brave_api_key:
                citation_result["brave"] = await self._check_brave(session, brand_queries, domain, brave_api_key)

        self.results["ai_citations"] = citation_result
        return citation_result

    async def _check_perplexity(self, session, queries: List[str], domain: str, api_key: str) -> Dict[str, Any]:
        cited = False
        all_citations = []
        try:
            for query in queries[:5]:
                async with session.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "sonar", "messages": [{"role": "user", "content": query}]},
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    citations = data.get("citations", [])
                    all_citations.extend(citations)
                    if any(domain in c for c in citations):
                        cited = True
        except Exception as e:
            self.results["errors"].append(f"Perplexity citation check failed: {str(e)}")
        return {"checked": True, "cited": cited, "citations": all_citations}

    async def _check_brave(self, session, queries: List[str], domain: str, api_key: str) -> Dict[str, Any]:
        cited = False
        all_results = []
        try:
            for query in queries[:5]:
                async with session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                    params={"q": query},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    results = [r.get("url", "") for r in data.get("web", {}).get("results", [])]
                    all_results.extend(results)
                    if any(domain in r for r in results):
                        cited = True
        except Exception as e:
            self.results["errors"].append(f"Brave citation check failed: {str(e)}")
        return {"checked": True, "cited": cited, "results": all_results}


async def main():
    """Example usage: python ai_visibility.py <url>"""
    import sys
    import json as json_mod

    if len(sys.argv) < 2:
        print("Usage: python ai_visibility.py <url>")
        sys.exit(1)

    auditor = AIVisibilityAuditor(sys.argv[1])
    results = await auditor.run_full_audit()
    print(json_mod.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())