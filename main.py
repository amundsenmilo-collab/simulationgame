"""
Asford Materials Hyperrealism Empire Builder
Backend API for business simulation game

ARCHITECTURE:
1. Python Finance Engine - Pure math, deterministic
2. LLM Game Master - Narrative only, minimal context
3. PostgreSQL - State persistence (handles 15+ years)

Flow:
- User enters directive
- Python runs FinanceEngine (arithmetic)
- Backend queries PostgreSQL for prior narrative
- Backend calls DeepSeek with: current financials + prior narrative only
- DeepSeek generates narrative
- Backend saves to PostgreSQL
- Frontend displays results
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import os

# Import engines
from textfile_1 import FinanceEngine
from narrative_engine import NarrativeEngine, FinancialSnapshot
from stock_engine import StockEngine, StockPosition
from database import GameDatabase

app = FastAPI(title="Asford Materials Hyperrealism Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
db = GameDatabase()
db.init_schema()
narrative_engine = NarrativeEngine()
stock_engine = StockEngine()
finance_engine = FinanceEngine()


# ===== REQUEST MODELS =====

class CreateGameRequest(BaseModel):
    player_name: str = "Connor Asford"


class FastForwardRequest(BaseModel):
    game_id: str
    year: int
    directives: List[str] = []


class ChatRequest(BaseModel):
    game_id: str
    year: int
    message: str


class StockActionRequest(BaseModel):
    game_id: str
    year: int
    action: str  # "buy", "sell", "toggle_drip"
    ticker: str
    shares: Optional[float] = None


# ===== ENDPOINTS =====

@app.get("/")
async def root():
    return {
        "status": "ok",
        "app": "Asford Materials Hyperrealism Engine",
        "endpoints": {
            "POST /game": "Create new game session",
            "POST /fastforward": "Advance one year (run finance model + generate narrative)",
            "POST /chat": "Chat with advisor between moves",
            "POST /stock/price": "Get stock price for ticker",
            "POST /stock/action": "Buy/sell/toggle DRIP",
            "GET /game/{game_id}": "Get full game state",
            "GET /game/{game_id}/year/{year}": "Get specific year state",
        }
    }


@app.post("/game")
async def create_game(req: CreateGameRequest):
    """
    Create a new game session.
    Initializes year 0 with baseline financials.
    """
    game_id = db.create_game(req.player_name)
    
    # Year 0 baseline
    baseline = {
        "revenue": 28_000_000.0,
        "ebitda": 4_480_000.0,
        "ebitda_margin": 16.0,
        "net_income": 2_387_380.0,
        "cash": 800_000.0,
        "debt": 4_620_000.0,
        "dscr": 1.93,
        "capex": 0.0,
        "dividend_paid": 0.0,
        "personal_cash": 0.0,
    }
    db.save_financials(game_id, 0, baseline)
    
    return {
        "game_id": game_id,
        "player_name": req.player_name,
        "current_year": 0,
        "financial_summary": baseline,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/fastforward")
async def fast_forward(req: FastForwardRequest):
    """
    Fast-forward one year.
    
    PROCESS:
    1. Run FinanceEngine (pure math, deterministic)
    2. Query PostgreSQL for prior narrative
    3. Call DeepSeek with: current financials + prior narrative only
    4. Save results to PostgreSQL
    
    This keeps DeepSeek token-efficient: ~500 tokens per year, regardless of game length.
    """
    game_id = req.game_id
    year = req.year
    directives = req.directives
    
    # Verify game exists
    game = db.get_game(game_id)
    if not game:
        return {"error": f"Game {game_id} not found"}, 404
    
    # Save directives
    for directive in directives:
        db.save_directive(game_id, year, directive)
    
    # STEP 1: Run FinanceEngine (pure math)
    financial_summary = finance_engine.fast_forward_year(year, directives)
    
    # Save financials
    db.save_financials(game_id, year, financial_summary)
    
    # STEP 2: Get prior narrative from PostgreSQL (for continuity)
    prior_narrative = None
    if year > 0:
        prior_narrative = db.get_narrative(game_id, year - 1)
    
    # STEP 3: Call DeepSeek with minimal context
    fin = FinancialSnapshot(
        year=year,
        revenue=financial_summary["revenue"],
        ebitda=financial_summary["ebitda"],
        ebitda_margin=financial_summary["ebitda_margin"],
        net_income=financial_summary["net_income"],
        cash=financial_summary["cash"],
        total_debt=financial_summary["debt"],
        dscr=financial_summary["dscr"],
    )
    
    narrative = narrative_engine.narrate_year(
        year=year,
        fin=fin,
        prior_narrative=prior_narrative,
        directives=directives,
    )
    
    # STEP 4: Save narrative to PostgreSQL
    db.save_narrative(game_id, year, narrative)
    
    # Update game year
    db.update_game_year(game_id, year)
    
    return {
        "game_id": game_id,
        "year": year,
        "directives": directives,
        "financial_summary": financial_summary,
        "narrative": narrative,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat with advisor between moves.
    Maintains conversation history in PostgreSQL.
    """
    game_id = req.game_id
    year = req.year
    user_message = req.message
    
    game = db.get_game(game_id)
    if not game:
        return {"error": f"Game {game_id} not found"}, 404
    
    # Save user message
    db.save_chat_message(game_id, year, "user", user_message)
    
    # Get conversation history (last 10 messages for context)
    history = db.get_chat_messages(game_id, year)
    
    # Get current financials
    financials = db.get_financials(game_id, year)
    if not financials:
        return {"error": f"No financials for year {year}"}, 404
    
    # Build prompt
    prompt = f"""You are Connor Asford's business advisor in a simulation game.

CURRENT YEAR: {year}
COMPANY: Asford Materials, Inc.

CURRENT FINANCIALS:
- Revenue: ${financials.get('revenue', 0):,.0f}
- EBITDA Margin: {financials.get('ebitda_margin', 0):.1f}%
- Cash: ${financials.get('cash', 0):,.0f}
- Debt: ${financials.get('debt', 0):,.0f}
- DSCR: {financials.get('dscr', 0):.2f}x

RECENT CONVERSATION:
"""
    for msg in history[-10:]:
        prompt += f"{msg['role'].upper()}: {msg['content']}\n"
    
    prompt += f"\nUSER: {user_message}\n\nADVISOR: "
    
    # Call DeepSeek
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("choices") and len(data["choices"]) > 0:
            assistant_message = data["choices"][0]["message"]["content"].strip()
        else:
            assistant_message = "I'm unable to respond right now."
    except Exception as e:
        assistant_message = f"Error: {str(e)}"
    
    # Save assistant message
    db.save_chat_message(game_id, year, "assistant", assistant_message)
    
    return {
        "game_id": game_id,
        "year": year,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/stock/price")
async def get_stock_price(game_id: str, year: int, ticker: str = "ASFD"):
    """
    Get current stock price.
    LLM determines price based on company financials.
    """
    game = db.get_game(game_id)
    if not game:
        return {"error": f"Game {game_id} not found"}, 404
    
    financials = db.get_financials(game_id, year)
    if not financials:
        return {"error": f"No financials for year {year}"}, 404
    
    # LLM determines stock price
    stock_price = stock_engine._determine_stock_price(
        ticker=ticker,
        year=year,
        company_financials=financials,
    )
    
    return {
        "ticker": stock_price.ticker,
        "price": stock_price.price,
        "dividend_per_share": stock_price.dividend_per_share,
        "dividend_yield": stock_price.dividend_yield,
        "market_sentiment": stock_price.market_sentiment,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/stock/action")
async def stock_action(req: StockActionRequest):
    """
    Buy, sell, or toggle DRIP for a stock.
    """
    game_id = req.game_id
    year = req.year
    action = req.action
    ticker = req.ticker
    shares = req.shares or 0
    
    game = db.get_game(game_id)
    if not game:
        return {"error": f"Game {game_id} not found"}, 404
    
    financials = db.get_financials(game_id, year)
    if not financials:
        return {"error": f"No financials for year {year}"}, 404
    
    # Get stock price
    stock_price = stock_engine._determine_stock_price(
        ticker=ticker,
        year=year,
        company_financials=financials,
    )
    
    # Get current position
    position_dict = db.get_stock_position(game_id, year, ticker)
    position = None
    if position_dict:
        position = StockPosition(
            ticker=position_dict["ticker"],
            shares=position_dict["shares"],
            avg_cost=position_dict["avg_cost"],
            current_price=position_dict["current_price"],
            dividend_per_share=position_dict["dividend_per_share"],
            drip_enabled=position_dict["drip_enabled"],
        )
    
    # Use personal cash from financials (stored in financials table)
    personal_cash = financials.get("personal_cash", 0)
    message = ""

    if action == "buy":
        position, personal_cash, message = stock_engine.buy_stock(position, stock_price, shares, personal_cash)
    elif action == "sell":
        position, proceeds, message = stock_engine.sell_stock(position, stock_price, shares)
        personal_cash += proceeds
    elif action == "toggle_drip":
        if position:
            position.drip_enabled = not position.drip_enabled
            message = f"DRIP {'enabled' if position.drip_enabled else 'disabled'} for {ticker}"
        else:
            message = f"No position in {ticker}"

    # Save position
    if position and position.shares > 0:
        db.save_stock_position(
            game_id, year, position.ticker, position.shares, position.avg_cost,
            position.current_price, position.dividend_per_share, position.drip_enabled
        )
    
    # Update personal cash (corporate cash is untouched)
    financials["personal_cash"] = personal_cash
    db.save_financials(game_id, year, financials)
    
    return {
        "game_id": game_id,
        "year": year,
        "action": action,
        "ticker": ticker,
        "message": message,
        "position": {
            "shares": position.shares if position else 0,
            "avg_cost": position.avg_cost if position else 0,
            "current_price": stock_price.price,
            "market_value": stock_engine.get_position_value(position),
            "gain_loss": stock_engine.get_position_gain(position),
        } if position else None,
        "personal_cash": personal_cash,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/game/{game_id}")
async def get_game_state(game_id: str):
    """Get full game state."""
    game = db.get_game(game_id)
    if not game:
        return {"error": f"Game {game_id} not found"}, 404
    
    financials = db.get_all_financials(game_id)
    trust_scores = db.get_trust_scores(game_id)
    
    return {
        "game": dict(game),
        "financials": financials,
        "trust_scores": trust_scores,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/game/{game_id}/year/{year}")
async def get_year_state(game_id: str, year: int):
    """Get state for a specific year."""
    game = db.get_game(game_id)
    if not game:
        return {"error": f"Game {game_id} not found"}, 404
    
    financials = db.get_financials(game_id, year)
    narrative = db.get_narrative(game_id, year)
    directives = db.get_directives(game_id, year)
    events = db.get_events(game_id, year)
    stock_positions = db.get_all_stock_positions(game_id, year)
    
    return {
        "game_id": game_id,
        "year": year,
        "financials": financials,
        "narrative": narrative,
        "directives": directives,
        "events": events,
        "stock_positions": stock_positions,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

