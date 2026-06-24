from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Import engines
from textfile_1 import FinanceEngine
from narrative_engine import NarrativeEngine, FinancialSnapshot
from database import GameDatabase

app = FastAPI(title="Asford Materials Hyperrealism Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and engines
db = GameDatabase()
db.init_schema()
narrative_engine = NarrativeEngine()


class CreateGameRequest(BaseModel):
    player_name: str = "Connor Asford"


class FastForwardRequest(BaseModel):
    game_id: str
    year: int
    directives: List[str] = []


@app.get("/")
async def root():
    return {
        "status": "ok",
        "app": "Asford Materials Hyperrealism Engine",
        "message": "Use POST /game to create a new game, then POST /fastforward to advance years",
    }


@app.post("/game")
async def create_game(req: CreateGameRequest):
    """
    Create a new game session.
    Returns game_id to use for all subsequent requests.
    """
    game_id = db.create_game(req.player_name)
    
    # Initialize year 0 financials (baseline)
    baseline_financials = {
        "revenue": 28_000_000.0,
        "ebitda": 4_480_000.0,
        "ebitda_margin": 16.0,
        "net_income": 2_387_380.0,
        "cash": 3_175_000.0,
        "debt": 4_620_000.0,
        "dscr": 1.93,
    }
    db.save_financials(game_id, 0, baseline_financials)
    
    return {
        "game_id": game_id,
        "player_name": req.player_name,
        "current_year": 0,
        "financial_summary": baseline_financials,
        "message": "Game created. Use POST /fastforward to advance to year 1.",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/fastforward")
async def fast_forward(req: FastForwardRequest):
    """
    Fast-forward one year: run financial model, generate narrative, save to database.
    
    Request body:
        game_id     – game session ID
        year        – target year (e.g., 1, 2, 3...)
        directives  – list of player directive strings
    
    Response:
        year, directives, financial_summary, narrative, timestamp
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
    
    # Run financial model
    financial_summary = FinanceEngine().fast_forward_year(year, directives)
    
    # Save financials
    db.save_financials(game_id, year, financial_summary)
    
    # Get prior year narrative for continuity
    prior_narrative = None
    if year > 0:
        prior_narrative = db.get_narrative(game_id, year - 1)
    
    # Generate narrative (minimal context: only current financials + prior narrative)
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
    
    # Save narrative
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


@app.get("/game/{game_id}")
async def get_game_state(game_id: str):
    """Get current game state and all financials."""
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
    
    return {
        "game_id": game_id,
        "year": year,
        "financials": financials,
        "narrative": narrative,
        "directives": directives,
        "events": events,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

