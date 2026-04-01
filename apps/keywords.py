"""
Keyword Opportunities - Find quick wins and content gaps
Integrates with Google Search Console API to identify ranking opportunities
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re


class KeywordAnalyzer:
    """Analyzes keywords to find opportunities and content gaps"""
    
    def __init__(self, domain: str, gsc_data: Optional[Dict] = None):
        """
        Initialize keyword analyzer
        
        Args:
            domain: Target domain (e.g., "example.com")
            gsc_data: Optional pre-fetched Google Search Console data
        """
        self.domain = domain
        self.gsc_data = gsc_data
        
    async def analyze_opportunities(self, progress_callback=None) -> Dict[str, Any]:
        """
        Analyze keyword opportunities
        
        Returns comprehensive analysis including:
        - Quick wins (positions 11-30)
        - Keyword clusters
        - Content gaps
        - Search intent classification
        """
        if progress_callback:
            await progress_callback(10, "Analyzing keywords")
        
        # Analyze GSC data if available
        quick_wins = []
        if self.gsc_data:
            quick_wins = self._identify_quick_wins(self.gsc_data)
        
        if progress_callback:
            await progress_callback(40, "Clustering keywords")
        
        # Cluster related keywords
        clusters = self._cluster_keywords(quick_wins) if quick_wins else {}
        
        if progress_callback:
            await progress_callback(70, "Analyzing intent")
        
        # Classify search intent
        for kw in quick_wins:
            kw['intent'] = self._classify_intent(kw['keyword'])
        
        if progress_callback:
            await progress_callback(90, "Generating recommendations")
        
        # Generate content recommendations
        recommendations = self._generate_recommendations(quick_wins, clusters)
        
        if progress_callback:
            await progress_callback(100, "Complete")
        
        return {
            "domain": self.domain,
            "analysis_date": datetime.now().isoformat(),
            "quick_wins": sorted(quick_wins, key=lambda x: x.get('potential_traffic', 0), reverse=True)[:50],
            "keyword_clusters": clusters,
            "recommendations": recommendations,
            "summary": {
                "total_opportunities": len(quick_wins),
                "total_clusters": len(clusters),
                "estimated_traffic_gain": sum(kw.get('potential_traffic', 0) for kw in quick_wins),
            }
        }
    
    def _identify_quick_wins(self, gsc_data: Dict) -> List[Dict]:
        """
        Identify keywords where you rank #11-30 (page 2-3)
        -.
        ++++++++++++
        These are "quick wins" - you already have some authority,
        just need optimization to reach page 1
        """
        opportunities = []
        
        queries = gsc_data.get('queries', [])
        
        for query in queries:
            position = query.get('position', 999)
            
            # Focus on positions 11-30 (page 2-3)
            if 11 <= position <= 30:
                impressions = query.get('impressions', 0)
                clicks = query.get('clicks', 0)
                ctr = query.get('ctr', 0)
                
                # Estimate traffic gain if we move to position 5
                potential_traffic = self._estimate_traffic_gain(
                    current_position=position,
                    impressions=impressions,
                    current_ctr=ctr
                )
                
                opportunities.append({
                    "keyword": query.get('query', ''),
                    "current_position": round(position, 1),
                    "impressions": impressions,
                    "clicks": clicks,
                    "ctr": round(ctr * 100, 2),
                    "potential_traffic": round(potential_traffic),
                    "search_volume": impressions,  # Approximate
                    "difficulty": self._estimate_difficulty(query.get('query', '')),
                    "priority": self._calculate_priority(position, impressions, potential_traffic),
                })
        
        return opportunities
    
    def _estimate_traffic_gain(self, current_position: float, impressions: int, current_ctr: float) -> float:
        """
        Estimate traffic gain if we improve to position 5
        
        Uses average CTR by position data:
        - Position 1: ~28% CTR
        - Position 2: ~15% CTR
        - Position 3: ~11% CTR
        - Position 4: ~8% CTR
        - Position 5: ~7% CTR
        - Positions 11-20: ~2% CTR
        - Positions 21-30: ~1% CTR
        """
        # Target CTR for position 5
        target_ctr = 0.07
        
        # Calculate potential new clicks
        potential_clicks = impressions * target_ctr
        
        # Subtract current clicks
        current_clicks = impressions * current_ctr
        
        # Return gain
        return max(0, potential_clicks - current_clicks)
    
    def _estimate_difficulty(self, keyword: str) -> str:
        """
        Estimate keyword difficulty based on heuristics
        
        Without external API, we use:
        - Length (longer = easier, usually long-tail)
        - Question words (easier to rank for informational)
        - Commercial words (harder, more competition)
        """
        word_count = len(keyword.split())
        
        # Question keywords are typically easier
        question_words = ['how', 'what', 'why', 'when', 'where', 'who', 'which']
        is_question = any(keyword.lower().startswith(q) for q in question_words)
        
        # Commercial keywords are typically harder
        commercial_words = ['buy', 'price', 'cheap', 'best', 'review', 'vs', 'comparison']
        is_commercial = any(word in keyword.lower() for word in commercial_words)
        
        # Scoring
        if is_commercial:
            return 'high'
        elif word_count >= 4 or is_question:
            return 'low'
        elif word_count >= 3:
            return 'medium'
        else:
            return 'high'
    
    def _calculate_priority(self, position: float, impressions: int, potential_traffic: float) -> str:
        """
        Calculate priority: high/medium/low
        
        Factors:
        - Position (closer to page 1 = higher priority)
        - Search volume (more impressions = higher priority)
        - Potential traffic gain
        """
        score = 0
        
        # Position score (closer to page 1 = higher)
        if position <= 15:
            score += 3
        elif position <= 20:
            score += 2
        else:
            score += 1
        
        # Volume score
        if impressions >= 500:
            score += 3
        elif impressions >= 100:
            score += 2
        elif impressions >= 20:
            score += 1
        
        # Traffic gain score
        if potential_traffic >= 50:
            score += 3
        elif potential_traffic >= 20:
            score += 2
        elif potential_traffic >= 5:
            score += 1
        
        # Convert to priority
        if score >= 7:
            return 'high'
        elif score >= 4:
            return 'medium'
        else:
            return 'low'
    
    def _classify_intent(self, keyword: str) -> str:
        """
        Classify search intent
        
        Categories:
        - informational: Looking for information
        - commercial: Researching products/services
        - transactional: Ready to buy
        - navigational: Looking for specific site/brand
        """
        kw_lower = keyword.lower()
        
        # Transactional intent
        transactional_words = ['buy', 'purchase', 'order', 'download', 'get', 'price', 'cheap', 'discount', 'deal']
        if any(word in kw_lower for word in transactional_words):
            return 'transactional'
        
        # Commercial intent
        commercial_words = ['best', 'top', 'review', 'vs', 'versus', 'compare', 'alternative', 'better than']
        if any(word in kw_lower for word in commercial_words):
            return 'commercial'
        
        # Informational intent
        informational_words = ['how', 'what', 'why', 'when', 'where', 'guide', 'tutorial', 'tips', 'learn', 'example']
        if any(word in kw_lower for word in informational_words):
            return 'informational'
        
        # Navigational (brand/site name)
        # This would require domain knowledge
        
        # Default to informational
        return 'informational'
    
    def _cluster_keywords(self, keywords: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group related keywords into topic clusters
        
        Uses simple word matching to find related keywords
        """
        clusters = {}
        processed = set()
        
        for i, kw in enumerate(keywords):
            if i in processed:
                continue
            
            keyword_text = kw['keyword']
            words = set(keyword_text.lower().split())
            
            # Find similar keywords
            cluster = [kw]
            cluster_name = self._generate_cluster_name(keyword_text)
            
            for j, other_kw in enumerate(keywords):
                if i == j or j in processed:
                    continue
                
                other_words = set(other_kw['keyword'].lower().split())
                
                # If 50%+ words overlap, it's related
                overlap = len(words & other_words)
                total = len(words | other_words)
                
                if overlap / total >= 0.5:
                    cluster.append(other_kw)
                    processed.add(j)
            
            if len(cluster) >= 2:  # Only create cluster if 2+ keywords
                clusters[cluster_name] = cluster
                processed.add(i)
        
        return clusters
    
    def _generate_cluster_name(self, keyword: str) -> str:
        """Generate a name for a keyword cluster"""
        # Remove common words
        stop_words = {'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were'}
        words = [w for w in keyword.lower().split() if w not in stop_words]
        
        # Take first 2-3 meaningful words
        return ' '.join(words[:3]).title()
    
    def _generate_recommendations(self, quick_wins: List[Dict], clusters: Dict) -> List[Dict]:
        """
        Generate actionable recommendations based on opportunities
        """
        recommendations = []
        
        # Recommendation 1: Target high-priority quick wins
        high_priority = [kw for kw in quick_wins if kw.get('priority') == 'high']
        if high_priority:
            top_3 = high_priority[:3]
            recommendations.append({
                "type": "quick_wins",
                "priority": "high",
                "title": "Optimize for Quick Win Keywords",
                "description": f"Focus on these {len(top_3)} high-priority keywords where you rank #11-30",
                "keywords": [kw['keyword'] for kw in top_3],
                "actions": [
                    "Improve on-page SEO (title, H1, meta description)",
                    "Add more relevant content (aim for 1500+ words)",
                    "Build 3-5 quality backlinks to these pages",
                    "Optimize for user intent and engagement",
                ],
                "estimated_impact": f"+{sum(kw.get('potential_traffic', 0) for kw in top_3)} monthly visits"
            })
        
        # Recommendation 2: Create content for clusters
        if clusters:
            largest_cluster = max(clusters.items(), key=lambda x: len(x[1]))
            cluster_name, cluster_keywords = largest_cluster
            
            recommendations.append({
                "type": "content_cluster",
                "priority": "medium",
                "title": f"Create Pillar Content for '{cluster_name}'",
                "description": f"You have {len(cluster_keywords)} related keywords in this topic cluster",
                "keywords": [kw['keyword'] for kw in cluster_keywords[:5]],
                "actions": [
                    f"Create a comprehensive pillar page about '{cluster_name}'",
                    "Cover all related subtopics in one authoritative guide",
                    "Internal link all cluster pages to the pillar page",
                    "Aim for 3000+ words with clear section headers",
                ],
                "estimated_impact": f"+{sum(kw.get('potential_traffic', 0) for kw in cluster_keywords)} monthly visits"
            })
        
        # Recommendation 3: Focus on informational content
        informational = [kw for kw in quick_wins if kw.get('intent') == 'informational']
        if informational:
            top_info = informational[:5]
            recommendations.append({
                "type": "content_type",
                "priority": "medium",
                "title": "Create Educational Content",
                "description": f"{len(informational)} opportunities are informational queries",
                "keywords": [kw['keyword'] for kw in top_info],
                "actions": [
                    "Write how-to guides and tutorials",
                    "Add step-by-step instructions with images",
                    "Include FAQ sections",
                    "Create video content to complement text",
                ],
                "estimated_impact": f"+{sum(kw.get('potential_traffic', 0) for kw in top_info)} monthly visits"
            })
        
        # Recommendation 4: Target transactional keywords
        transactional = [kw for kw in quick_wins if kw.get('intent') == 'transactional']
        if transactional:
            top_trans = transactional[:3]
            recommendations.append({
                "type": "conversion",
                "priority": "high",
                "title": "Optimize for Transactional Keywords",
                "description": f"{len(transactional)} opportunities have buying intent",
                "keywords": [kw['keyword'] for kw in top_trans],
                "actions": [
                    "Add clear call-to-action buttons",
                    "Include pricing and product details",
                    "Add customer reviews and testimonials",
                    "Optimize checkout/contact forms",
                ],
                "estimated_impact": f"+{sum(kw.get('potential_traffic', 0) for kw in top_trans)} monthly visits (high conversion)"
            })
        
        return recommendations


# ──────────────────────────────────────────────────────────────────────────────
# Mock Google Search Console Data Generator (for testing without GSC API)
# ──────────────────────────────────────────────────────────────────────────────

def generate_mock_gsc_data(domain: str) -> Dict:
    """
    Generate mock GSC data for testing
    
    In production, this would be replaced with actual GSC API calls
    """
    import random
    
    # Sample keywords by industry
    sample_keywords = {
        "tech": [
            "how to optimize website performance",
            "best practices for web development",
            "react vs vue comparison",
            "what is seo optimization",
            "website security checklist",
            "mobile responsive design tips",
            "improve page load speed",
            "web accessibility guidelines",
            "best cms for blogs",
            "how to choose hosting provider",
        ],
        "ecommerce": [
            "best online payment gateway",
            "how to increase ecommerce sales",
            "shopping cart abandonment solutions",
            "product photography tips",
            "ecommerce seo best practices",
            "customer retention strategies",
            "conversion rate optimization",
            "email marketing for online stores",
            "shipping options comparison",
            "inventory management software",
        ],
        "saas": [
            "project management tools comparison",
            "best crm for small business",
            "team collaboration software",
            "cloud storage solutions",
            "video conferencing platforms",
            "accounting software for startups",
            "marketing automation tools",
            "customer support software",
            "analytics dashboard tools",
            "productivity apps for teams",
        ]
    }
    
    # Detect industry from domain (simple heuristic)
    if any(word in domain.lower() for word in ['shop', 'store', 'buy', 'cart']):
        keywords = sample_keywords["ecommerce"]
    elif any(word in domain.lower() for word in ['soft', 'app', 'cloud', 'saas']):
        keywords = sample_keywords["saas"]
    else:
        keywords = sample_keywords["tech"]
    
    queries = []
    for kw in keywords:
        # Generate random position between 11-30
        position = random.uniform(11, 30)
        
        # Generate impressions based on keyword length (longer = less volume)
        word_count = len(kw.split())
        base_impressions = 1000 if word_count <= 3 else 500 if word_count <= 4 else 200
        impressions = random.randint(base_impressions // 2, base_impressions * 2)
        
        # CTR based on position
        ctr = 0.02 if position <= 20 else 0.01
        clicks = int(impressions * ctr)
        
        queries.append({
            "query": kw,
            "position": position,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
        })
    
    return {"queries": queries}


# ──────────────────────────────────────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────────────────────────────────────

async def analyze_keywords(
    domain: str,
    gsc_data: Optional[Dict] = None,
    use_mock_data: bool = True,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Analyze keyword opportunities for a domain
    
    Args:
        domain: Target domain
        gsc_data: Optional GSC data (if None and use_mock_data=True, generates mock data)
        use_mock_data: If True and gsc_data is None, generates sample data for testing
        progress_callback: Optional async function(progress, status)
    
    Returns:
        Keyword analysis with opportunities and recommendations
    """
    # Use mock data if no real data provided
    if gsc_data is None and use_mock_data:
        gsc_data = generate_mock_gsc_data(domain)
    
    analyzer = KeywordAnalyzer(domain, gsc_data)
    results = await analyzer.analyze_opportunities(progress_callback=progress_callback)
    return results

# loop = asyncio.get_event_loop()
# results = loop.run_until_complete(analyze_keywords('https://rstipower.com'))
# print(results)