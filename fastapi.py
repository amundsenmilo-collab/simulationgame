from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
from datetime import datetime

from models import Company, Employee, PlayerDecision, FinancialSnapshot
from finance import FinanceEngine
from narrative import NarrativeEngine
from search import WebSearchEngine

app = FastAPI(title="Asford Materials Hyperrealism Engine")

# Initialize engines
finance = FinanceEngine()
narrative = NarrativeEngine()  # Loads Hugging Face model
search = WebSearchEngine()

class DecisionRequest(BaseModel):
    year: int
    quarter: int
    player_name: str = "Connor Asford"
    directives: List[str]  # "hire 2 estimators", "raise wages 4%", etc.
    entities_involved: List[str] = []

class FastForwardRequest(BaseModel):
    start_year: int
    end_year: int
    directives_by_year: Dict[int, List[str]]

class SearchRequest(BaseModel):
    query: str
    context: Optional[str] = None

@app.post("/decision")
async def process_decision(req: DecisionRequest):
    """
    Process a player decision.
    1. Validate directives against current state
    2. Apply financial model
    3. Check covenants
    4. Generate narrative texture
    5. Log everything
    """
    # Get current state
    state = finance.get_company_state(1)  # Asford Materials
    
    # Validate (simplified)
    validated = []
    for d in req.directives:
        # Check cash, permissions, feasibility
        validated.append({"directive": d, "valid": True, "cost": 0})
    
    # Apply (would call finance.fast_forward_year)
    # For now, return structured response
    
    # Generate narrative
    context = f"Player decides: {', '.join(req.directives)}. Company cash: ${state.get('cash', 0):,.0f}."
    texture = narrative.generate_texture(
        context, req.entities_involved, req.year, req.quarter
    )
    
    return {
        "year": req.year,
        "quarter": req.quarter,
        "directives_validated": validated,
        "company_state": state,
        "narrative": texture,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/fastforward")
async def fast_forward(req: FastForwardRequest):
    """
    Fast-forward multiple years.
    Returns: year-by-year financials + narrative textures
    """
    results = []
    
    for year in range(req.start_year, req.end_year + 1):
        directives = req.directives_by_year.get(year, [])
        
        # Run financial model
        # financials = finance.fast_forward_year(1, year, directives)
        
        # Generate texture for key events
        # texture = narrative.generate_texture(...)
        
        results.append({
            "year": year,
            "directives": directives,
            # "financials": financials,
            # "narrative": texture
        })
    
    return {"years_processed": results}

@app.post("/search")
async def web_search(req: SearchRequest):
    """
    Ground player decisions in reality.
    Searches web, caches results, returns structured data.
    """
    results = search.search(req.query)
    
    # If context provided, extract relevant snippets
    if req.context:
        # Use LLM to extract cost estimates from search results
        pass
    
    return {
        "query": req.query,
        "results": results,
        "cached": results.get("source") != "error"
    }

@app.get("/state/{company_id}")
async def get_state(company_id: int):
    """Get full company state"""
    return finance.get_company_state(company_id)

@app.get("/relationships/{entity_name}")
async def get_relationship(entity_name: str):
    """Get relationship memory for any entity"""
    db = sqlite3.connect("asford.db")
    db.row_factory = sqlite3.Row
    
    cursor = db.execute("""
        SELECT * FROM relationships WHERE entity_name = ?
    """, (entity_name,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return dict(row)

@app.get("/narrative/{year}/{quarter}")
async def get_narrative(year: int, quarter: int):
    """Retrieve generated narrative for any period"""
    db = sqlite3.connect("asford.db")
    db.row_factory = sqlite3.Row
    
    cursor = db.execute("""
        SELECT * FROM narrative_log WHERE year = ? AND quarter = ?
        ORDER BY created_at DESC
    """, (year, quarter))
    
    return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
