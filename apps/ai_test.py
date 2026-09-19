import requests
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import aiohttp
import os
import asyncio
from datetime import datetime

BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "").strip()

async def check_ai_citations(url, brand_queries: List[str], perplexity_api_key: Optional[str] = None,
                                  brave_api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Send brand_queries to Perplexity and Brave Search APIs and check whether
        this site's domain shows up in the citations/results. Opt-in (Pro/Agency),
        costs real API credits, so it is never called automatically.

        Wire this up from the route/task layer once you decide where the API
        keys live (env vars vs. per-user BYO keys) - see the markdown doc.
        """
        domain = urlparse(url).netloc.replace("www.", "")
        citation_result = {
            "domain_checked": domain,
            "queries": brand_queries,
            "perplexity": {"checked": False, "cited": False, "citations": []},
            "brave": {"checked": False, "cited": False, "results": []},
        }

        async with aiohttp.ClientSession() as session:
            print(brave_api_key)
            if perplexity_api_key:
                citation_result["perplexity"] = await _check_perplexity(session, brand_queries, domain, perplexity_api_key)
            if brave_api_key:
                print("Checking brave...")
                citation_result["brave"] = await _check_brave(session, brand_queries, domain, brave_api_key)

        return citation_result

async def _check_perplexity(session, queries: List[str], domain: str, api_key: str) -> Dict[str, Any]:
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
        pass
    return {"checked": True, "cited": cited, "citations": all_citations}

async def _check_brave(session, queries: List[str], domain: str, api_key: str) -> Dict[str, Any]:
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
                print(query, resp.status)
                if resp.status != 200:
                    continue
                data = await resp.json()
                results = [r.get("url", "") for r in data.get("web", {}).get("results", [])]
                all_results.extend(results)
                if any(domain in r for r in results):
                    cited = True
    except Exception as e:
        print(f"Brave citation check failed: {str(e)}")
    return {"checked": True, "cited": cited, "results": all_results}


async def main():
    """Example usage"""
    import sys
    import json

    brand_queries = [
        "top white label reporting tools for agencies",
    ]
    
    # Run the citations check
    results = await check_ai_citations("https://www.agencyanalytics.com", brand_queries, brave_api_key=BRAVE_SEARCH_API_KEY)
    print(results)

    #Save results to JSON file
    output_file = f"audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Full results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())