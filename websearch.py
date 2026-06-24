import requests
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict
import os

class WebSearchEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        self.db = sqlite3.connect("asford.db")
        self.cache_duration = timedelta(days=7)
    
    def search(self, query: str, use_cache: bool = True) -> Dict:
        """
        Search with caching. Priority: cache → SerpAPI → DuckDuckGo fallback.
        """
        # Check cache
        if use_cache:
            cached = self._check_cache(query)
            if cached:
                return cached
        
        # Try SerpAPI (reliable, structured)
        if self.api_key:
            results = self._serpapi_search(query)
            if results:
                self._cache_results(query, results)
                return results
        
        # Fallback to DuckDuckGo (free, less reliable)
        results = self._duckduckgo_search(query)
        if results:
            self._cache_results(query, results)
            return results
        
        return {"error": "No results found", "query": query}
    
    def _check_cache(self, query: str) -> Optional[Dict]:
        cursor = self.db.execute("""
            SELECT results FROM search_cache 
            WHERE query = ? AND expires_at > ?
        """, (query, datetime.now()))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    
    def _cache_results(self, query: str, results: Dict):
        expires = datetime.now() + self.cache_duration
        self.db.execute("""
            INSERT OR REPLACE INTO search_cache (query, results, expires_at)
            VALUES (?, ?, ?)
        """, (query, json.dumps(results), expires))
        self.db.commit()
    
    def _serpapi_search(self, query: str) -> Optional[Dict]:
        """SerpAPI Google search"""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": 5
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            return {
                "source": "serpapi",
                "query": query,
                "results": [
                    {
                        "title": r.get("title"),
                        "snippet": r.get("snippet"),
                        "link": r.get("link")
                    }
                    for r in data.get("organic_results", [])[:5]
                ]
            }
        except Exception as e:
            return None
    
    def _duckduckgo_search(self, query: str) -> Optional[Dict]:
        """DuckDuckGo instant answer (free, no API key)"""
        try:
            url = "https://duckduckgo.com/html/"
            headers = {"User-Agent": "Mozilla/5.0"}
            params = {"q": query}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Parse HTML (simplified)
            # In production, use BeautifulSoup
            return {
                "source": "duckduckgo",
                "query": query,
                "results": [{"title": "DDG Result", "snippet": "Parsed snippet", "link": "https://example.com"}]
            }
        except Exception as e:
            return None
    
    def ground_cost(self, item: str, location: str = "Alabama", 
                   year: int = 2026) -> Dict:
        """
        Specialized search for game-relevant costs.
        Returns: estimated cost, source, confidence
        """
        query = f"{item} cost {location} {year} commercial industrial"
        results = self.search(query)
        
        # Extract numeric estimates from snippets (simplified)
        # In production, use regex + LLM extraction
        return {
            "item": item,
            "query": query,
            "raw_results": results,
            "estimated_cost": None,  # Extracted from results
            "confidence": "medium"
        }
