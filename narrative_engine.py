"""
Narrative engine for Asford Materials Hyperrealism Empire Builder.
Generates year-end texture using DeepSeek API + fragment-based fallback.
Tracks NPC trust scores and relationship state.
Injects game context from game_context.md for grounded narratives.
"""
import os
import json
import random
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# DeepSeek API config
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


@dataclass
class FinancialSnapshot:
    """Year-end financials."""
    year: int
    revenue: float
    cogs_opex: float
    ebitda: float
    depreciation: float
    ebit: float
    interest: float
    taxable_income: float
    tax: float
    net_income: float
    cash: float
    total_debt: float
    dscr: float
    dividend_paid: float
    capex: float
    ebitda_margin: float


@dataclass
class CompanyState:
    """Current company condition."""
    name: str
    cash: float
    total_debt: float
    revenue_annual: float
    ebitda_annual: float
    net_income: float
    dscr: float
    founded_year: int


@dataclass
class RelationshipState:
    """NPC relationship snapshot."""
    entity_name: str
    trust_score: int  # 0-100
    last_interaction: Optional[str]
    key_facts: List[str]
    promises_made: Optional[str]
    promises_broken: int


@dataclass
class EventMemory:
    """Prior events that shape narrative."""
    year: int
    quarter: int
    event_type: str
    description: str
    entities_involved: List[str]
    financial_impact: float


class NarrativeEngine:
    """
    Generates year-end narrative texture from financial and state data.
    Uses DeepSeek API for rich narratives, falls back to fragments if API fails.
    Tracks and updates NPC trust scores.
    Injects game context from game_context.md for grounded narratives.
    """

    # Default trust scores for key NPCs
    DEFAULT_TRUST_SCORES = {
        "mike_castellano": 75,      # Plant manager, loyal but aging
        "patricia_holt": 60,        # Bank relationship manager, cautious
        "mother": 80,               # Family, supportive
        "sister": 70,               # Family, involved in business
        "business_agent": 40,       # Union, adversarial
        "harold_vance": 50,         # Competitor, neutral
        "darius_cole": 45,          # Supplier, transactional
    }

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.trust_scores = self.DEFAULT_TRUST_SCORES.copy()
        self.game_context = self._load_game_context()

    def _load_game_context(self) -> str:
        """Load game context from game_context.md if it exists."""
        context_path = Path(__file__).parent / "game_context.md"
        if context_path.exists():
            try:
                return context_path.read_text()
            except Exception as e:
                print(f"[CONTEXT] Failed to load game_context.md: {e}")
                return ""
        return ""

    # ======================================================================
    # Trust Score Management
    # ======================================================================

    def update_trust_score(self, entity_name: str, delta: int, reason: str = "") -> int:
        """
        Update an NPC's trust score. Clamps to [0, 100].
        Returns new score.
        """
        if entity_name not in self.trust_scores:
            self.trust_scores[entity_name] = 50  # Default neutral

        old_score = self.trust_scores[entity_name]
        new_score = max(0, min(100, old_score + delta))
        self.trust_scores[entity_name] = new_score

        # Log for debugging
        if reason:
            print(f"[TRUST] {entity_name}: {old_score} → {new_score} ({reason})")

        return new_score

    def get_trust_score(self, entity_name: str) -> int:
        """Get current trust score for an NPC."""
        return self.trust_scores.get(entity_name, 50)

    def get_all_trust_scores(self) -> Dict[str, int]:
        """Return all trust scores as dict."""
        return self.trust_scores.copy()

    # ======================================================================
    # Prompt Construction
    # ======================================================================

    def _build_deepseek_prompt(
        self,
        year: int,
        fin: FinancialSnapshot,
        company: Optional[CompanyState],
        events: List[EventMemory],
        relationships: List[RelationshipState],
        year_type: str,
    ) -> str:
        """Build a rich prompt for DeepSeek with game context injected."""

        # Format relationships for context
        rel_context = ""
        if relationships:
            rel_lines = []
            for rel in relationships:
                trust_label = self._trust_label(rel.trust_score)
                rel_lines.append(
                    f"- {rel.entity_name}: trust {rel.trust_score}/100 ({trust_label})"
                )
            rel_context = "\n".join(rel_lines)

        # Format events for context
        event_context = ""
        if events:
            event_lines = []
            for evt in events:
                event_lines.append(f"- Q{evt.quarter}: {evt.event_type} - {evt.description}")
            event_context = "\n".join(event_lines)

        # Build prompt with game context
        prompt = f"""You are the objective, unsentimental game master for Asford Materials Hyperrealism Empire Builder.

## GAME CONTEXT

{self.game_context}

## THIS YEAR ({year})

**Year Type:** {year_type}

**Financials:**
- Revenue: ${fin.revenue:,.0f}
- EBITDA: ${fin.ebitda:,.0f} ({fin.ebitda_margin:.1f}% margin)
- Net Income: ${fin.net_income:,.0f}
- Cash: ${fin.cash:,.0f}
- Total Debt: ${fin.total_debt:,.0f}
- DSCR: {fin.dscr:.2f}x
- CapEx: ${fin.capex:,.0f}
- Dividend: ${fin.dividend_paid:,.0f}

**Relationship Status:**
{rel_context if rel_context else "No relationship data."}

**Events This Year:**
{event_context if event_context else "No major events."}

## YOUR TASK

Write 2-3 paragraphs of year-end narrative texture. Ground it in the game world, the characters, and the financial reality above. No lists. No dashboards. Show, don't tell.

**Requirements:**
1. Include sensory details (smell, sound, temperature, texture, touch)
2. Let character dialogue reveal motivation, not explain it
3. Embed the financial reality into the narrative (margins, covenants, cash flow)
4. Reflect the year type ({year_type}) in tone and events
5. Reference specific NPCs and their trust dynamics
6. Be cold and unsentimental. No cheering. No ensuring victory. The world is indifferent.

**Tone Example:**
"The year started with a backlog Connor had not seen since his grandfather's era. The batch plant smelled of wet cement and diesel. Mike Castellano moved his tools to the new kiln in March, three weeks behind schedule. By June, the margin was 18 percent. Patricia Holt's year-end call was brief: 'See me in January.' Connor signed the year-end statements at 11 PM, alone in the office."

Write the narrative now."""

        return prompt

    def _trust_label(self, score: int) -> str:
        """Convert trust score to narrative label."""
        if score >= 80:
            return "loyal"
        elif score >= 60:
            return "cooperative"
        elif score >= 40:
            return "neutral"
        elif score >= 20:
            return "wary"
        else:
            return "hostile"

    # ======================================================================
    # DeepSeek API Call
    # ======================================================================

    def _call_deepseek(self, prompt: str) -> Optional[str]:
        """Call DeepSeek API. Returns narrative or None on failure."""
        if not self.api_key:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 800,
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
                return data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            print("[DEEPSEEK] Timeout")
        except requests.exceptions.ConnectionError:
            print("[DEEPSEEK] Connection error")
        except requests.exceptions.HTTPError as e:
            print(f"[DEEPSEEK] HTTP error: {e}")
        except Exception as e:
            print(f"[DEEPSEEK] Error: {e}")

        return None

    # ======================================================================
    # Fragment-Based Fallback
    # ======================================================================

    def _select_texture_fragments(
        self,
        year_type: str,
        events: List[EventMemory],
        relationships: List[RelationshipState],
    ) -> Dict:
        """Select narrative fragments based on year type and events."""

        fragments = {"openings": [], "middles": [], "closes": [], "sensory": []}

        # Year-type openings
        year_openings = {
            "boom": [
                "The year started with a backlog Connor had not seen since his grandfather's era.",
                "January brought three major DOT awards in the same week.",
                "The production floor ran two shifts for the first time.",
            ],
            "crisis": [
                "Connor knew by February that this would be a hard year.",
                "The January books showed cash bleeding faster than he had modeled.",
                "Patricia Holt's Q1 call came on a Tuesday, earlier than scheduled.",
            ],
            "investment": [
                "The ground broke in March, three weeks behind schedule.",
                "Connor spent more nights in Sylacauga than in Hoover.",
                "Mike Castellano moved his tools to the new plant in April.",
            ],
            "extraction": [
                "Connor took the dividend in January, before the year revealed itself.",
                "The board minutes were one page. The vote was 1-0.",
                "Patricia Holt made a note in the file. She did not call.",
            ],
            "ordinary": [
                "The year began with ice on the batch plant roof.",
                "January was cold and slow, as January always is.",
                "Connor drove to the plant on New Year's Day. Mike was already there.",
            ],
        }
        fragments["openings"].extend(
            year_openings.get(year_type, year_openings["ordinary"])
        )

        # Event-based middles
        for event in events:
            if event.event_type == "equipment" and event.financial_impact > 10000:
                fragments["middles"].append(
                    f"The {event.description.lower()}. Mike fixed it in {self._rng_hours()} hours."
                )
            elif event.event_type == "personnel" and "mike_castellano" in event.entities_involved:
                fragments["middles"].append(
                    "Mike asked about the equity again. Connor said later. Mike said nothing."
                )
            elif event.event_type == "union":
                fragments["middles"].append(
                    f"The union business agent filed in {self._rng_month()}. The hearing was in {self._rng_month()}."
                )
            elif event.event_type == "market" and event.financial_impact > 100000:
                fragments["middles"].append(
                    "Forterra underbid them on the bridge job. The margin was thin anyway."
                )
            elif event.event_type == "regulatory" and "osha" in event.entities_involved:
                fragments["middles"].append(
                    f"OSHA arrived {self._rng_day()}. The fine was ${event.financial_impact:,.0f}."
                )

        # Relationship-based closes
        for rel in relationships:
            if rel.entity_name == "mike_castellano" and rel.trust_score < 60:
                fragments["closes"].append(
                    "Mike took his vacation in December. He had not taken vacation in three years."
                )
            elif rel.entity_name == "patricia_holt" and rel.promises_broken > 0:
                fragments["closes"].append(
                    "Patricia Holt's year-end note was one sentence: 'See me in January.'"
                )
            elif rel.entity_name == "mother" and rel.last_interaction:
                fragments["closes"].append(
                    "His mother called in December. She did not ask for money. She asked about the lake house."
                )

        # Default closes if none triggered
        if not fragments["closes"]:
            fragments["closes"].extend(
                [
                    "The books closed December 31. The accountant worked until 9 PM.",
                    "Connor signed the year-end statements at 11 PM, alone in the office.",
                    "The CHOMEX break room was empty when he walked through. The Sharpie was still there.",
                ]
            )

        # Sensory details
        fragments["sensory"] = [
            "The crane groaned at 6 AM when the temperature dropped below freezing.",
            "The batch plant smelled of wet cement and diesel.",
            "Mike's coffee cup left a ring on every surface he touched.",
            "The fluorescent lights in the form shop flickered but never died.",
            "Connor's F-150 needed new shocks. He felt every pothole on I-65.",
        ]

        return fragments

    def _assemble_narrative_fallback(
        self,
        year: int,
        fin: FinancialSnapshot,
        company: Optional[CompanyState],
        fragments: Dict,
        year_type: str,
    ) -> str:
        """Assemble fragments into coherent year-end texture (fallback)."""

        # Opening
        opening = random.choice(fragments["openings"])

        # Middle (events + financial pressure)
        middle_parts = []
        if fragments["middles"]:
            middle_parts.append(random.choice(fragments["middles"]))

        # Financial texture (embedded in narrative, not listed)
        if fin.ebitda_margin < 5:
            middle_parts.append(
                f"The margin was {fin.ebitda_margin:.1f} percent. "
                f"Connor did not need Kevin Jock to tell him what that meant."
            )
        elif fin.ebitda_margin > 15:
            middle_parts.append(
                f"The margin was {fin.ebitda_margin:.1f} percent. "
                f"Mike said it was the best year since Barry Jr."
            )

        if fin.dscr < 2.0:
            middle_parts.append(
                f"The bank's covenant was {fin.dscr:.2f}x. Patricia Holt would notice."
            )

        if fin.capex > 1000000:
            middle_parts.append(
                f"${fin.capex:,.0f} left the account for dirt and concrete. "
                f"Connor watched the wires clear."
            )

        if fin.dividend_paid > 0:
            middle_parts.append(
                f"He took ${fin.dividend_paid:,.0f} in December. The board minutes were one page."
            )

        # Sensory detail
        sensory = random.choice(fragments["sensory"])

        # Close
        close = random.choice(fragments["closes"])

        # Assemble
        paragraphs = []

        # Paragraph 1: Opening + context
        p1 = f"{opening} {sensory}"
        paragraphs.append(p1)

        # Paragraph 2: Events + financial pressure
        if middle_parts:
            p2 = " ".join(middle_parts[:2])  # Max 2 middle fragments
            paragraphs.append(p2)

        # Paragraph 3: Close + forward look
        if fin.dscr < 1.5:
            p3 = f"{close} The next year would be harder."
        elif fin.dscr > 3.0 and fin.cash > 1000000:
            p3 = f"{close} For the first time in years, the balance sheet felt like breathing room."
        else:
            p3 = close

        paragraphs.append(p3)

        return "\n\n".join(paragraphs)

    # ======================================================================
    # Year Classification
    # ======================================================================

    def _classify_year(
        self, fin: FinancialSnapshot, prior_fin: Optional[FinancialSnapshot]
    ) -> str:
        """Classify the year's character for narrative tone."""

        if prior_fin:
            revenue_change = (
                ((fin.revenue - prior_fin.revenue) / prior_fin.revenue * 100)
                if prior_fin.revenue > 0
                else 0
            )
            ebitda_change = (
                ((fin.ebitda - prior_fin.ebitda) / prior_fin.ebitda * 100)
                if prior_fin.ebitda > 0
                else 0
            )
            cash_change = fin.cash - prior_fin.cash
        else:
            revenue_change = 0
            ebitda_change = 0
            cash_change = 0

        # Year archetypes
        if fin.ebitda_margin >= 15 and revenue_change > 5:
            return "boom"
        elif fin.ebitda_margin >= 10 and fin.dscr >= 3.0:
            return "stable"
        elif fin.ebitda_margin >= 5 and fin.dscr >= 2.0:
            return "lean"
        elif fin.dscr < 1.5 or fin.cash < 200000:
            return "crisis"
        elif fin.capex > fin.ebitda * 0.5:
            return "investment"
        elif revenue_change < -5:
            return "contraction"
        elif fin.dividend_paid > fin.net_income * 0.5:
            return "extraction"
        else:
            return "ordinary"

    # ======================================================================
    # Random Narrative Helpers
    # ======================================================================

    def _rng_hours(self) -> str:
        """Random plausible hour count for narrative."""
        return str(random.choice([8, 12, 24, 36, 48]))

    def _rng_month(self) -> str:
        """Random month for narrative."""
        return random.choice(
            ["February", "March", "April", "May", "September", "October"]
        )

    def _rng_day(self) -> str:
        """Random day descriptor for narrative."""
        return random.choice(
            ["Monday morning", "a Thursday", "the last Friday of the month", "a rainy Tuesday"]
        )

    # ======================================================================
    # Main Entry Point
    # ======================================================================

    def narrate_year(
        self,
        year: int,
        fin: FinancialSnapshot,
        company: Optional[CompanyState] = None,
        events: Optional[List[EventMemory]] = None,
        relationships: Optional[List[RelationshipState]] = None,
        prior_fin: Optional[FinancialSnapshot] = None,
    ) -> str:
        """
        Main entry point. Generate year-end narrative.

        Args:
            year: Game year
            fin: FinancialSnapshot for the year
            company: CompanyState (optional)
            events: List of EventMemory (optional)
            relationships: List of RelationshipState (optional)
            prior_fin: Prior year's FinancialSnapshot for comparison (optional)

        Returns:
            2-3 paragraph year-end narrative texture.
        """

        events = events or []
        relationships = relationships or []

        # Classify year
        year_type = self._classify_year(fin, prior_fin)

        # Try DeepSeek first
        prompt = self._build_deepseek_prompt(
            year, fin, company, events, relationships, year_type
        )
        narrative = self._call_deepseek(prompt)

        # Fall back to fragments if DeepSeek fails
        if not narrative:
            fragments = self._select_texture_fragments(year_type, events, relationships)
            narrative = self._assemble_narrative_fallback(
                year, fin, company, fragments, year_type
            )

        return narrative

    # ======================================================================
    # Serialization (for API responses)
    # ======================================================================

    def to_dict(self) -> Dict:
        """Serialize engine state to dict."""
        return {
            "trust_scores": self.trust_scores,
            "timestamp": datetime.now().isoformat(),
        }
