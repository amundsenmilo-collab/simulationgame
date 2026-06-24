from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

# Import engines from their respective modules
from textfile_1 import FinanceEngine
from narrative_engine import (
    NarrativeEngine,
    FinancialSnapshot,
    CompanyState,
)
from database import GameDatabase
from github_integration import GitHubGameState

app = FastAPI(title="Asford Materials Hyperrealism Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
narrative_engine = NarrativeEngine()
db = GameDatabase()
github = GitHubGameState()

# Initialize database schema on startup
try:
    db.init_schema()
except Exception as e:
    print(f"[STARTUP] DB init warning: {e}")


class FastForwardRequest(BaseModel):
    year: int
    directives: List[str] = []


@app.get("/")
async def root():
    return {
        "status": "ok",
        "app": "Asford Materials Hyperrealism Engine",
        "trust_scores": narrative_engine.get_all_trust_scores(),
    }


@app.post("/fastforward")
async def fast_forward(req: FastForwardRequest):
    """
    Fast-forward one year: run the financial model then generate narrative.
    
    ARCHITECTURE (Token Efficient):
    1. FinanceEngine: Pure arithmetic, no LLM
    2. Database: Stores all state (financials, trust scores, events)
    3. GitHub: Stores narrative history (one commit per year)
    4. DeepSeek: Only reads current year + last narrative + prior snapshot
    
    This way DeepSeek never tracks 10+ years of history—it just reads the summary.
    """
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
        # 1. Run financial model (pure arithmetic, no LLM)
        financial_summary = FinanceEngine().fast_forward_year(req.year, req.directives)

        # 2. Get prior narrative from GitHub (or database fallback)
        prior_narrative = github.get_year_narrative(req.year - 1)
        if not prior_narrative:
            prior_narrative = db.get_prior_narrative(req.year)

        # 3. Get prior financials from database
        prior_fin_dict = db.get_prior_financials(req.year)

        # 4. Convert to FinancialSnapshot objects
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

        prior_fin = None
        if prior_fin_dict:
            prior_fin = FinancialSnapshot(
                year=prior_fin_dict.get("year", req.year - 1),
                revenue=prior_fin_dict.get("revenue", 0),
                ebitda=prior_fin_dict.get("ebitda", 0),
                ebitda_margin=prior_fin_dict.get("ebitda_margin", 0),
                net_income=prior_fin_dict.get("net_income", 0),
                cash=prior_fin_dict.get("cash", 0),
                total_debt=prior_fin_dict.get("total_debt", 0),
                dscr=prior_fin_dict.get("dscr", 0),
                dividend_paid=prior_fin_dict.get("dividend_paid", 0),
                capex=prior_fin_dict.get("capex", 0),
            )

        # 5. Create company state
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

        # 6. Get trust scores from database
        trust_scores_dict = db.get_trust_scores()
        if trust_scores_dict:
            narrative_engine.trust_scores = trust_scores_dict

        # 7. Generate narrative (DeepSeek only reads: current + last narrative + prior snapshot)
        narrative = narrative_engine.narrate_year(
            year=req.year,
            fin=fin,
            company=company,
            events=[],
            relationships=[],
            prior_fin=prior_fin,
            prior_narrative=prior_narrative,
            directives=req.directives,
        )

        # 8. Save to database
        db.save_year_result(
            year=req.year,
            financials=financial_summary,
            narrative=narrative,
            directives=req.directives,
            trust_scores=narrative_engine.get_all_trust_scores(),
        )

        # 9. Commit to GitHub (narrative history)
        github.commit_year(req.year, narrative, financial_summary)

    except Exception as e:
        error = str(e)
        narrative = f"Financial simulation encountered an error: {error}"
        print(f"[ERROR] {error}")

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
    """Update an NPC's trust score in the database."""
    new_score = db.update_trust_score(entity_name, delta)
    return {
        "entity_name": entity_name,
        "new_score": new_score,
        "reason": reason,
        "all_trust_scores": db.get_trust_scores(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/trust")
async def get_trust_scores():
    """Get all current trust scores from database."""
    return {
        "trust_scores": db.get_trust_scores(),
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

