from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date
from enum import Enum

class EntityType(str, Enum):
    C_CORP = "C-corp"
    S_CORP = "S-corp"
    LLC = "LLC"

class EventType(str, Enum):
    MARKET = "market"
    PERSONNEL = "personnel"
    EQUIPMENT = "equipment"
    REGULATORY = "regulatory"
    FINANCIAL = "financial"
    PERSONAL = "personal"

class Company(BaseModel):
    id: Optional[int] = None
    name: str
    entity_type: EntityType
    founded_year: int
    cash: float = 0
    total_debt: float = 0
    revenue_annual: float = 0
    ebitda_annual: float = 0
    net_income: float = 0
    dscr: float = 0

class Employee(BaseModel):
    id: Optional[int] = None
    company_id: int
    name: str
    role: str
    salary: float = 0
    hourly_wage: Optional[float] = None
    hire_date: Optional[date] = None
    trust_score: int = Field(50, ge=0, le=100)
    last_interaction: Optional[date] = None
    grievances: Optional[str] = None
    promises: Optional[str] = None
    is_active: bool = True

class Relationship(BaseModel):
    id: Optional[int] = None
    entity_name: str
    entity_type: str = Field(..., pattern="^(person|organization|object)$")
    trust_score: int = Field(50, ge=0, le=100)
    last_interaction: Optional[date] = None
    key_facts: List[str] = []
    promises_made: Optional[str] = None
    promises_broken: int = 0

class FinancialSnapshot(BaseModel):
    id: Optional[int] = None
    company_id: int
    year: int
    quarter: int
    revenue: float = 0
    cogs_opex: float = 0
    ebitda: float = 0
    depreciation: float = 0
    ebit: float = 0
    interest: float = 0
    taxable_income: float = 0
    tax: float = 0
    net_income: float = 0
    cash: float = 0
    total_debt: float = 0
    dscr: float = 0
    dividend_paid: float = 0
    capex: float = 0

class GameEvent(BaseModel):
    id: Optional[int] = None
    year: int
    quarter: int
    event_type: EventType
    description: str
    entities_involved: List[str] = []
    financial_impact: float = 0
    narrative_rendered: Optional[str] = None

class PlayerDecision(BaseModel):
    id: Optional[int] = None
    year: int
    quarter: int
    decision_text: str
    outcome: Optional[str] = None
    financial_impact: float = 0
    entities_affected: List[str] = []

class NarrativeTexture(BaseModel):
    id: Optional[int] = None
    year: int
    quarter: int
    context: str
    narrative_text: str
    entities_involved: List[str] = []
    importance: int = Field(5, ge=1, le=10)

class LLMContextBlock(BaseModel):
    id: Optional[int] = None
    context_type: str
    content: str
    entities: List[str] = []
    year: int
    importance: int = Field(5, ge=1, le=10)
    decay_rate: int = 1

class RevenueStream(BaseModel):
    id: Optional[int] = None
    company_id: int
    sku: Optional[str] = None
    description: str
    monthly_revenue: float = 0
    monthly_cogs: float = 0
    is_active: bool = True