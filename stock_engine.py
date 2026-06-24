"""
Stock market engine for Asford Materials game.
LLM determines stock prices based on market conditions.
Tracks portfolio, dividends, DRIP, capital gains.
"""
import os
import json
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


@dataclass
class StockPosition:
    """A stock holding."""
    ticker: str
    shares: float
    avg_cost: float
    current_price: float
    dividend_per_share: float = 0.0
    drip_enabled: bool = True


@dataclass
class StockPrice:
    """Stock price and dividend info."""
    ticker: str
    price: float
    dividend_per_share: float
    dividend_yield: float
    market_sentiment: str  # bullish, neutral, bearish


class StockEngine:
    """
    Determines stock prices using LLM + web search.
    Tracks portfolio, dividends, DRIP.
    """

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY

    def _web_search(self, query: str) -> str:
        """
        Search the web for stock information.
        Uses DuckDuckGo via DeepSeek's web search capability.
        """
        # For now, return a placeholder. In production, use actual web search.
        return f"Market data for {query}"

    def _determine_stock_price(
        self,
        ticker: str,
        year: int,
        company_financials: Dict,
        market_context: str = "",
    ) -> StockPrice:
        """
        Use LLM to determine stock price based on market conditions.
        
        Args:
            ticker: Stock ticker (e.g., "ASFD" for Asford Materials)
            year: Game year
            company_financials: Current year financials
            market_context: Optional market context
        
        Returns:
            StockPrice with price, dividend, sentiment
        """
        if not self.api_key:
            # Fallback: simple calculation
            return self._fallback_price(ticker, year, company_financials)

        prompt = f"""You are a stock market analyst for a business simulation game.

COMPANY: {ticker}
YEAR: {year}

CURRENT FINANCIALS:
- Revenue: ${company_financials.get('revenue', 0):,.0f}
- EBITDA Margin: {company_financials.get('ebitda_margin', 0):.1f}%
- Net Income: ${company_financials.get('net_income', 0):,.0f}
- Cash: ${company_financials.get('cash', 0):,.0f}
- Debt: ${company_financials.get('debt', 0):,.0f}
- DSCR: {company_financials.get('dscr', 0):.2f}x

{market_context}

Based on these financials and market conditions, determine:
1. Stock price (realistic for a heavy industrial company)
2. Annual dividend per share (if any)
3. Market sentiment (bullish, neutral, or bearish)

Respond in JSON format:
{{
  "price": <float>,
  "dividend_per_share": <float>,
  "sentiment": "<bullish|neutral|bearish>",
  "reasoning": "<brief explanation>"
}}

Respond ONLY with valid JSON, no other text."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
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
                content = data["choices"][0]["message"]["content"].strip()
                result = json.loads(content)
                
                return StockPrice(
                    ticker=ticker,
                    price=float(result.get("price", 50.0)),
                    dividend_per_share=float(result.get("dividend_per_share", 0.0)),
                    dividend_yield=float(result.get("dividend_per_share", 0.0)) / float(result.get("price", 50.0)) * 100,
                    market_sentiment=result.get("sentiment", "neutral"),
                )

        except Exception as e:
            print(f"[STOCK] LLM error: {e}")

        return self._fallback_price(ticker, year, company_financials)

    def _fallback_price(
        self, ticker: str, year: int, company_financials: Dict
    ) -> StockPrice:
        """Fallback price calculation if LLM fails."""
        # Base price on DSCR and margin
        dscr = company_financials.get("dscr", 1.5)
        margin = company_financials.get("ebitda_margin", 10.0)
        
        # Price formula: base * dscr_multiplier * margin_multiplier
        base_price = 50.0
        dscr_mult = min(2.0, max(0.5, dscr / 1.5))  # 1.5x DSCR = 1.0x price
        margin_mult = 1.0 + (margin - 10.0) / 100.0  # 10% margin = 1.0x
        
        price = base_price * dscr_mult * margin_mult
        dividend = price * 0.03 if dscr > 2.0 else 0.0  # 3% yield if healthy
        
        sentiment = "bullish" if dscr > 2.0 else "neutral" if dscr > 1.5 else "bearish"
        
        return StockPrice(
            ticker=ticker,
            price=round(price, 2),
            dividend_per_share=round(dividend, 2),
            dividend_yield=round(dividend / price * 100, 2) if price > 0 else 0.0,
            market_sentiment=sentiment,
        )

    def buy_stock(
        self,
        position: Optional[StockPosition],
        stock_price: StockPrice,
        shares: float,
        cash_available: float,
    ) -> tuple[Optional[StockPosition], float, str]:
        """
        Buy shares of a stock.
        
        Returns:
            (updated_position, remaining_cash, message)
        """
        cost = shares * stock_price.price
        
        if cost > cash_available:
            return position, cash_available, f"Insufficient cash. Need ${cost:,.2f}, have ${cash_available:,.2f}"
        
        if position is None:
            # New position
            position = StockPosition(
                ticker=stock_price.ticker,
                shares=shares,
                avg_cost=stock_price.price,
                current_price=stock_price.price,
                dividend_per_share=stock_price.dividend_per_share,
                drip_enabled=True,
            )
        else:
            # Add to existing position
            total_cost = (position.shares * position.avg_cost) + cost
            position.shares += shares
            position.avg_cost = total_cost / position.shares
            position.current_price = stock_price.price
            position.dividend_per_share = stock_price.dividend_per_share
        
        return position, cash_available - cost, f"Bought {shares} shares of {stock_price.ticker} at ${stock_price.price:.2f}"

    def sell_stock(
        self,
        position: Optional[StockPosition],
        stock_price: StockPrice,
        shares: float,
    ) -> tuple[Optional[StockPosition], float, str]:
        """
        Sell shares of a stock.
        
        Returns:
            (updated_position, proceeds, message)
        """
        if position is None or position.shares < shares:
            return position, 0.0, "Insufficient shares to sell"
        
        proceeds = shares * stock_price.price
        gain = (stock_price.price - position.avg_cost) * shares
        
        position.shares -= shares
        position.current_price = stock_price.price
        
        if position.shares == 0:
            position = None
        
        message = f"Sold {shares} shares at ${stock_price.price:.2f}. Gain/Loss: ${gain:,.2f}"
        return position, proceeds, message

    def apply_dividends(
        self,
        position: Optional[StockPosition],
        stock_price: StockPrice,
    ) -> tuple[Optional[StockPosition], float]:
        """
        Apply annual dividends.
        If DRIP enabled, reinvest dividends.
        
        Returns:
            (updated_position, cash_dividend)
        """
        if position is None or position.shares == 0:
            return position, 0.0
        
        dividend_amount = position.shares * stock_price.dividend_per_share
        
        if position.drip_enabled and stock_price.dividend_per_share > 0:
            # Reinvest: buy more shares with dividend
            new_shares = dividend_amount / stock_price.price
            position.shares += new_shares
            return position, 0.0  # No cash paid out
        else:
            # Pay dividend in cash
            return position, dividend_amount

    def update_position_price(
        self,
        position: Optional[StockPosition],
        stock_price: StockPrice,
    ) -> Optional[StockPosition]:
        """Update position with current market price."""
        if position is None:
            return None
        position.current_price = stock_price.price
        position.dividend_per_share = stock_price.dividend_per_share
        return position

    def get_position_value(self, position: Optional[StockPosition]) -> float:
        """Get current market value of position."""
        if position is None or position.shares == 0:
            return 0.0
        return position.shares * position.current_price

    def get_position_gain(self, position: Optional[StockPosition]) -> float:
        """Get unrealized gain/loss."""
        if position is None or position.shares == 0:
            return 0.0
        return (position.current_price - position.avg_cost) * position.shares

