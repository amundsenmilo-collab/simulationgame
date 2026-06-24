from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from duckduckgo_search import DDGS

# Import engines from their respective modules
from textfile_1 import FinanceEngine
from textfile_2 import NarrativeEngine

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
    year: int
    directives: List[str] = []


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
    Fast-forward one year: run the financial model then generate LLM narrative.

    Request body:
        year       – target game year (e.g. 2027)
        directives – list of player directive strings

    Response:
        year, directives, financial_summary, narrative, timestamp
    """
    # Guaranteed-safe default so the frontend never sees undefined
    financial_summary: Dict = {
        "revenue": 0.0,
        "ebitda": 0.0,
        "ebitda_margin": 0.0,
        "net_income": 0.0,
        "cash": 0.0,
        "debt": 0.0,
        "dscr": 0.0,
        "covenant_breach": False,
    }
    narrative = ""
    error = None

    try:
        # 1. Run financial model
        financial_summary = FinanceEngine().fast_forward_year(req.year, req.directives)

        # 2. Generate LLM narrative
        narrative = NarrativeEngine().generate_texture(financial_summary, req.directives, req.year)

    except Exception as e:
        error = str(e)
        narrative = f"Financial simulation encountered an error: {error}"

    response = {
        "year": req.year,
        "directives": req.directives,
        "financial_summary": financial_summary,
        "narrative": narrative,
        "timestamp": datetime.now().isoformat(),
    }
    if error:
        response["error"] = error

    return response


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
