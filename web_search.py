"""
Web search integration for realistic game data.
Searches for real-world prices and inflates them to game year.
Used by Python finance engine to calculate directive impacts.

Examples:
- "moves to Bozeman Montana and buys a house" → searches home prices → inflates to game year
- "buys a Chomex modular home" → searches price → inflates
- "enrolls employees in AD&D insurance" → searches group insurance rates → calculates cost
"""

import os
import requests
from typing import Optional, Dict
from datetime import datetime

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


class WebSearchEngine:
    """
    Uses LLM to search web and extract pricing data.
    Inflates prices from 2026 to game year using inflation rate.
    """

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.inflation_rate = 0.035  # 3.5% annual inflation

    def _inflate_price(self, base_price: float, from_year: int, to_year: int) -> float:
        """
        Inflate a price from one year to another.
        
        Args:
            base_price: Price in base year (2026)
            from_year: Base year (2026)
            to_year: Target year (game year)
        
        Returns:
            Inflated price
        """
        years = to_year - from_year
        if years <= 0:
            return base_price
        return base_price * ((1 + self.inflation_rate) ** years)

    def search_price(self, query: str, game_year: int) -> Optional[Dict]:
        """
        Search for a price and inflate to game year.
        
        Args:
            query: What to search for (e.g., "Bozeman Montana house price 2026")
            game_year: Target year to inflate to
        
        Returns:
            {
                "query": original query,
                "base_price": price in 2026,
                "inflated_price": price in game_year,
                "description": what was found,
                "confidence": 0-1 confidence score
            }
        """
        if not self.api_key:
            return None

        prompt = f"""You are a research assistant finding real-world pricing data.

SEARCH QUERY: {query}

Your task:
1. Search for the most relevant price for this query
2. Return the price in 2026 dollars (or adjust if you find a different year)
3. Provide a brief description of what you found
4. Rate your confidence (0-1) in the accuracy

Respond in JSON format:
{{
  "base_price": <float in 2026 dollars>,
  "description": "<what was found>",
  "confidence": <0-1>,
  "source": "<where this price comes from>"
}}

Respond ONLY with valid JSON, no other text."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,  # Lower temp for factual data
                "max_tokens": 300,
            }
            response = requests.post(
                DEEPSEEK_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("choices") and len(data["choices"]) > 0:
                import json
                content = data["choices"][0]["message"]["content"].strip()
                result = json.loads(content)
                
                base_price = float(result.get("base_price", 0))
                inflated_price = self._inflate_price(base_price, 2026, game_year)
                
                return {
                    "query": query,
                    "base_price": base_price,
                    "inflated_price": inflated_price,
                    "description": result.get("description", ""),
                    "confidence": float(result.get("confidence", 0.5)),
                    "source": result.get("source", ""),
                    "game_year": game_year,
                }

        except Exception as e:
            print(f"[SEARCH] Error: {e}")

        return None

    def calculate_directive_cost(self, directive: str, game_year: int) -> Optional[Dict]:
        """
        Parse a directive and calculate its financial impact.
        
        Examples:
        - "moves to Bozeman Montana and buys a house" → searches home prices
        - "buys a Chomex modular home" → searches modular home prices
        - "enrolls employees in AD&D insurance" → searches group insurance rates
        
        Args:
            directive: Player directive text
            game_year: Current game year
        
        Returns:
            {
                "directive": original directive,
                "impact_type": "personal_expense" | "company_expense" | "capital_investment",
                "amount": cost in dollars,
                "description": what was calculated,
                "confidence": 0-1
            }
        """
        if not self.api_key:
            return None

        prompt = f"""You are analyzing a business directive to calculate its financial impact.

DIRECTIVE: {directive}
GAME YEAR: {game_year}

Your task:
1. Identify what financial impact this directive has
2. Determine if it's a personal expense, company expense, or capital investment
3. Search for realistic 2026 pricing for the item/service mentioned
4. Inflate to game year if needed (3.5% annual inflation)
5. Return the total cost

Respond in JSON format:
{{
  "impact_type": "<personal_expense|company_expense|capital_investment>",
  "base_price_2026": <float>,
  "inflated_price": <float for game year>,
  "description": "<what this costs and why>",
  "confidence": <0-1>,
  "notes": "<any assumptions made>"
}}

Respond ONLY with valid JSON, no other text."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 400,
            }
            response = requests.post(
                DEEPSEEK_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("choices") and len(data["choices"]) > 0:
                import json
                content = data["choices"][0]["message"]["content"].strip()
                result = json.loads(content)
                
                return {
                    "directive": directive,
                    "impact_type": result.get("impact_type", "company_expense"),
                    "base_price_2026": float(result.get("base_price_2026", 0)),
                    "amount": float(result.get("inflated_price", 0)),
                    "description": result.get("description", ""),
                    "confidence": float(result.get("confidence", 0.5)),
                    "notes": result.get("notes", ""),
                    "game_year": game_year,
                }

        except Exception as e:
            print(f"[DIRECTIVE_COST] Error: {e}")

        return None

