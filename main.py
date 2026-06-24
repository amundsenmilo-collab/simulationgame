from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from duckduckgo_search import DDGS

app = FastAPI(title="Asford Materials Hyperrealism Engine")


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
    Fast-forward multiple years and return a year-by-year summary.
    """
    results = [
        {
            "year": year,
            "directives": req.directives_by_year.get(year, []),
        }
        for year in range(req.start_year, req.end_year + 1)
    ]

    return {"years_processed": results}


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
