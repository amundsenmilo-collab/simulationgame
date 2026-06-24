from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from duckduckgo_search import DDGS

# Import engines from their respective modules
from textfile_1 import FinanceEngine
from narrative_engine import (
    NarrativeEngine,
    FinancialSnapshot,
    CompanyState,
    RelationshipState,
    EventMemory,
)

app = FastAPI(title="Asford Materials Hyperrealism Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global narrative engine instance (maintains trust scores across requests)
narrative_engine = NarrativeEngine()


class DecisionRequest(BaseModel):
    year: int
    quarter: int
    player_name: str = "Connor Asford"
    directives: List[str]
    entities_involved: List[str] = []


class FastForwardRequest(BaseModel):
    year: int
    directives: List[str] = []
    prior_narrative: Optional[str] = None  # Last year's narrative for continuity
    prior_year_financials: Optional[Dict] = None  # Prior year's end-of-year snapshot only


class SearchRequest(BaseModel):
    query: str
    context: Optional[str] = None


@app.get("/")
async def root():
    return {
        "status": "ok",
        "app": "Asford Materials Hyperrealism Engine",
        "trust_scores": narrative_engine.get_all_trust_scores(),
    }


@app.post("/decision")
async def process_decision(req: DecisionRequest):
    """
    Process a player decision and return a structured response.
    """
    validated = [{"directive": d, "valid": True, "cost": 0} for d in req.directives]

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
    Fast-forward one year: run the financial model then generate narrative.

    Request body:
        year                    – target game year (e.g. 2027)
        directives              – list of player directive strings
        prior_narrative         – last year's narrative text (for continuity)
        prior_year_financials   – prior year's end-of-year snapshot only (efficient)

    Response:
        year, directives, financial_summary, narrative, trust_scores, timestamp
    """
    # Guaranteed-safe defaults
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

        # 2. Convert financial summary to FinancialSnapshot (current year)
        fin = FinancialSnapshot(
            year=req.year,
            revenue=financial_summary.get("revenue", 0),
            ebitda=financial_summary.get("ebitda", 0),
            ebitda_margin=financial_summary.get("ebitda_margin", 0),
            net_income=financial_summary.get("net_income", 0),
            cash=financial_summary.get("cash", 0),
            total_debt=financial_summary.get("debt", 0),
            dscr=financial_summary.get("dscr", 0),
            dividend_paid=financial_summary.get("dividend_paid", 0),
            capex=financial_summary.get("capex", 0),
        )

        # 3. Create company state
        company = CompanyState(
            name="Asford Materials",
            cash=financial_summary.get("cash", 0),
            total_debt=financial_summary.get("debt", 0),
            revenue_annual=financial_summary.get("revenue", 0),
            ebitda_annual=financial_summary.get("ebitda", 0),
            net_income=financial_summary.get("net_income", 0),
            dscr=financial_summary.get("dscr", 0),
            founded_year=1978,
        )

        # 4. Convert prior year financials if provided (efficient: end-of-year snapshot only)
        prior_fin = None
        if req.prior_year_financials:
            prior_fin = FinancialSnapshot(
                year=req.year - 1,
                revenue=req.prior_year_financials.get("revenue", 0),
                ebitda=req.prior_year_financials.get("ebitda", 0),
                ebitda_margin=req.prior_year_financials.get("ebitda_margin", 0),
                net_income=req.prior_year_financials.get("net_income", 0),
                cash=req.prior_year_financials.get("cash", 0),
                total_debt=req.prior_year_financials.get("debt", 0),
                dscr=req.prior_year_financials.get("dscr", 0),
                dividend_paid=req.prior_year_financials.get("dividend_paid", 0),
                capex=req.prior_year_financials.get("capex", 0),
            )

        # 5. Generate narrative with prior narrative and prior year snapshot
        narrative = narrative_engine.narrate_year(
            year=req.year,
            fin=fin,
            company=company,
            events=[],  # Can be populated from database if needed
            relationships=[],  # Can be populated from database if needed
            prior_fin=prior_fin,  # Prior year's end-of-year snapshot only
            prior_narrative=req.prior_narrative,  # Last year's narrative for continuity
            directives=req.directives,
        )

    except Exception as e:
        error = str(e)
        narrative = f"Financial simulation encountered an error: {error}"

    response = {
        "year": req.year,
        "directives": req.directives,
        "financial_summary": financial_summary,
        "narrative": narrative,
        "trust_scores": narrative_engine.get_all_trust_scores(),
        "timestamp": datetime.now().isoformat(),
    }
    if error:
        response["error"] = error

    return response


@app.post("/trust/{entity_name}")
async def update_trust(entity_name: str, delta: int, reason: str = ""):
    """
    Update an NPC's trust score.

    Args:
        entity_name: NPC name (e.g. 'mike_castellano')
        delta: Change in trust score (-100 to +100)
        reason: Optional reason for the change

    Returns:
        Updated trust score and all trust scores
    """
    new_score = narrative_engine.update_trust_score(entity_name, delta, reason)
    return {
        "entity_name": entity_name,
        "new_score": new_score,
        "reason": reason,
        "all_trust_scores": narrative_engine.get_all_trust_scores(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/trust")
async def get_trust_scores():
    """
    Get all current trust scores.
    """
    return {
        "trust_scores": narrative_engine.get_all_trust_scores(),
        "timestamp": datetime.now().isoformat(),
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
                results.append(
                    {
                        "title": r.get("title"),
                        "snippet": r.get("body"),
                        "link": r.get("href"),
                    }
                )
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

