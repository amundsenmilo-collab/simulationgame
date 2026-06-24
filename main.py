from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from duckduckgo_search import DDGS
import sys
import os

# Import local modules
sys.path.insert(0, os.path.dirname(__file__))
from init_db import init_database
from textfile_1 import FinanceEngine
from textfile_2 import NarrativeEngine

# Initialize database on startup
init_database()

app = FastAPI(title="Asford Materials Hyperrealism Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DecisionRequest(BaseModel):
    year: int
    quarter: int
    player_name: str = "Connor Asford"
    directives: List[str]
    entities_involved: List[str] = []


class FastForwardRequest(BaseModel):
    start_year: int
    end_year: int
    directives_by_year: Dict[int, List[str]]


class SearchRequest(BaseModel):
    query: str
    context: Optional[str] = None


@app.get("/")
async def root():
    return {"status": "ok", "app": "Asford Materials Hyperrealism Engine"}


@app.post("/decision")
async def process_decision(req: DecisionRequest):
    """
    Process a player decision and return a structured response.
    """
    validated = [
        {"directive": d, "valid": True, "cost": 0}
        for d in req.directives
    ]

    return {
        "year": req.year,
        "quarter": req.quarter,
        "player_name": req.player_name,
        "directives_validated": validated,
        "company_state": {"status": "placeholder"},
        "narrative": f"Player {req.player_name} issued {len(req.directives)} directive(s) in Q{req.quarter} {req.year}.",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/fastforward")
async def fast_forward(req: FastForwardRequest):
    """
    Fast-forward one year: run financial model + LLM narrative generation.
    """
    try:
        # Get directives for the year (or empty list)
        year = req.start_year
        directives = req.directives_by_year.get(year, [])
        
        # Run financial model
        finance = FinanceEngine()
        financial_result = finance.fast_forward_year(company_id=1, year=year, directives=directives)
        
        # Build context for LLM
        event_context = f"""
YEAR {year} FINANCIAL RESULTS:
Revenue: ${financial_result['revenue']:,.0f}
EBITDA: ${financial_result['ebitda']:,.0f} ({financial_result['ebitda_margin']:.1f}% margin)
Net Income: ${financial_result['net_income']:,.0f}
Cash Position: ${financial_result['cash']:,.0f}
Total Debt: ${financial_result['total_debt']:,.0f}
DSCR: {financial_result['dscr']:.2f}x
Covenant Breach: {financial_result['covenant_breach']}

Directives Applied: {', '.join(directives) if directives else 'None'}
"""
        
        # Generate narrative via LLM
        try:
            narrative_engine = NarrativeEngine()
            narrative = narrative_engine.generate_texture(
                event_context=event_context,
                entities=["Asford Materials", "Connor Asford", "Mike Castellano"],
                year=year,
                quarter=1
            )
        except Exception as e:
            # Fallback if LLM fails
            narrative = f"Year {year} concluded. Financial model executed. {str(e)}"
        
        return {
            "year": year,
            "narrative": narrative,
            "financial_summary": financial_result,
            "timestamp": datetime.now().isoformat(),
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "year": req.start_year,
            "narrative": f"Error processing year: {str(e)}",
        }


@app.post("/search")
async def web_search(req: SearchRequest):
    """
    Search the web using DuckDuckGo and return structured results.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(req.query, max_results=5):
                results.append({
                    "title": r.get("title"),
                    "snippet": r.get("body"),
                    "link": r.get("href"),
                })
    except Exception as e:
        return {
            "query": req.query,
            "results": [],
            "error": str(e),
        }

    return {
        "query": req.query,
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

