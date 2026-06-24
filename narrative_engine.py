"""
Narrative engine for Asford Materials Hyperrealism Empire Builder.
Generates year-end texture using DeepSeek API + fragment-based fallback.
Tracks NPC trust scores and relationship state.
Embeds game context for grounded, character-driven narratives.
Efficient: passes last year's narrative text + prior year's end-of-year snapshot only.
"""
import os
import json
import random
import requests
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# DeepSeek API config
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Game context (embedded directly)
GAME_CONTEXT = """ASFORD MATERIALS, INC. — HYPERREALISM EMPIRE BUILDER
January 1, 2026. Connor Asford, age 25.

THE INHERITANCE
Your father, Barry Asford III, died December 15, 2025. Liver failure. He was 49. He weighed 340 pounds. He drank a fifth of bourbon a day. He ate fried chicken for breakfast. He inherited Asford Materials from his father, Barry Jr., who built it from a gravel yard in 1978. Barry III worked three days a week — Monday, Wednesday, Friday, 10 AM to 2 PM. He spent the rest of his time at the Birmingham Athletic Club, at the Regions Bank box, at the lake house in Cullman with women who were not your mother.

Mike Castellano ran the company. He has run it for three years. He is not your uncle. He is your father's third cousin by marriage. You have called him "Uncle Mike" since you were six. He is 41. He is the VP of Operations. He makes $78,000. He has not had a raise in four years. He has not complained. He knows more about precast concrete than anyone in Alabama. He knows more about your father than you do.

THE COMPANY
Asford Materials, Inc. C-corporation. Birmingham, Alabama. Heavy industrial. 7 acres. No rail.
Products: RCP pipe, manholes, junction boxes, inlets, end treatments. DOT-adjacent, utility, commercial.

OPENING BALANCE SHEET — January 1, 2026
Assets: $7,795,000
Liabilities: $4,620,000
Equity: $3,175,000

INCOME STATEMENT — Year 0 (Trailing Twelve Months)
Revenue: $28,000,000
EBITDA: $4,480,000
Net Income: $2,387,380

THE PROBLEM
The plant is maxed out at 87% utilization. Equipment is old but functional. Deferred maintenance backlog: $866,000. The union election is 45 days away. 30% of workers showed interest in unionizing.

THE MARGIN IS EXTRACTION, NOT COMPETENCE
Labor compression: 29 production workers at $19.50/hr in a $27–28 market. Annual underpayment: ~$452,000.
Deferred maintenance: $866,000 in replacement backlog.
Mike Castellano: Makes $78,000, knows everything, hasn't quit yet.

YOUR POSITION
Age: 25
Education: UAB Civil Engineering
Experience: 3 years in company (estimating, QC)
Personal cash: $12,000
Company salary: $65,000
Debt: $180K condo mortgage, $180K lake house mortgage
Inherited: Lake house (worth ~$340K)

IMMEDIATE CRISES
1. Union election in 45 days (February 15, 2026)
2. Plant at 87% utilization — losing bids due to capacity
3. Deferred maintenance time bombs: crane hook block, batch mixer, form shop roof
4. Regions Bank meeting required by January 15
5. Estimator has outside offer; might leave
6. Mother wants more money; sister wants "fairness"

GOAL: Hyperrealism Empire Builder
Build fast, manage scale, or lose everything your grandfather built and your father drank away."""

# Narrative format instruction
NARRATIVE_FORMAT = """NARRATIVE FORMAT INSTRUCTION:

You will narrate each year in a specific, grounded format. Here is an example for Year 1 (2027):

**January 2027.** Connor Asford sits in his father's office for the first time. The chair is still warm from Barry III's body. The desk has a ring from a sweating glass. The file drawer is full of Mike Castellano's reports — each one dated, each one stamped RECEIVED, each one unread. The crane hook block has a hairline crack. The batch mixer drum is 14 years old. The form shop roof is tarpaulins and buckets. Connor reads all of it. He calls Mike Castellano at 6:00 PM on January 3. Mike answers on the first ring. Connor says, "I'm not my father." Mike says, "I know." Connor says, "I want to replace everything this year. Operating cash. No debt." Mike is quiet for seven seconds. He says, "You can't. Not everything." Connor says, "Watch me."

**February 2027.** The office manager, Diane Foster, 58, pulls the ADEM replacement permit for the batch plant. She has worked at Asford Materials for 22 years. She knows where every form is filed. She knows that Barry III never filed anything on time. She submits the permit electronically at 8:14 AM. ADEM confirms receipt at 8:17 AM. Diane prints the confirmation and puts it on Connor's desk with a sticky note that says, "Your father never did this." Connor reads the note. He does not smile.

KEY CHARACTERISTICS OF THIS FORMAT:
- Specific dates and months (January, February, etc.)
- Character names, ages, and details (Diane Foster, 58, 22 years at Asford)
- Exact financial figures ($78,000, $4,480,000, etc.)
- Dialogue that reveals character motivation and stakes
- Sensory details (warm chair, sweating glass, tarpaulins and buckets)
- Embedded financial reality (DSCR targets, margins, cash positions)
- Personal stakes and emotional truth (Connor does not smile, Mike is quiet for seven seconds)
- Specific locations (the office, the batch plant, the break room)
- Specific machines and equipment (crane hook block, batch mixer drum, form shop roof)
- Consequences and cause-and-effect
- Tone: Cold, unsentimental, objective. No cheerleading. The world is indifferent.
- Length: 3-5 paragraphs, not a list. Tell a story.
- Use **bold** for month/date headers and key moments.

APPLY THIS FORMAT TO THE YEAR YOU ARE NARRATING."""


@dataclass
class FinancialSnapshot:
    """Year-end financials."""
    year: int
    revenue: float
    ebitda: float
    ebitda_margin: float
    net_income: float
    cash: float
    total_debt: float
    dscr: float
    dividend_paid: float = 0.0
    capex: float = 0.0


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
    last_interaction: Optional[str] = None
    key_facts: Optional[List[str]] = None
    promises_made: Optional[str] = None
    promises_broken: int = 0


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
    Embeds game context for grounded, character-driven narratives.
    EFFICIENT: Passes last year's narrative text + prior year's end-of-year snapshot only.
    """

    # Default trust scores for key NPCs
    DEFAULT_TRUST_SCORES = {
        "mike_castellano": 75,
        "patricia_holt": 60,
        "mother": 80,
        "sister": 70,
        "business_agent": 40,
        "harold_vance": 50,
        "darius_cole": 45,
    }

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.trust_scores = self.DEFAULT_TRUST_SCORES.copy()

    def update_trust_score(self, entity_name: str, delta: int, reason: str = "") -> int:
        if entity_name not in self.trust_scores:
            self.trust_scores[entity_name] = 50
        old_score = self.trust_scores[entity_name]
        new_score = max(0, min(100, old_score + delta))
        self.trust_scores[entity_name] = new_score
        if reason:
            print(f"[TRUST] {entity_name}: {old_score} → {new_score} ({reason})")
        return new_score

    def get_trust_score(self, entity_name: str) -> int:
        return self.trust_scores.get(entity_name, 50)

    def get_all_trust_scores(self) -> Dict[str, int]:
        return self.trust_scores.copy()

    def _trust_label(self, score: int) -> str:
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

    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown bold (**text**) to HTML <strong>text</strong>."""
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

    def _build_deepseek_prompt(
        self,
        year: int,
        fin: FinancialSnapshot,
        company: Optional[CompanyState],
        events: List[EventMemory],
        relationships: List[RelationshipState],
        year_type: str,
        directives: List[str],
        prior_fin: Optional[FinancialSnapshot] = None,
        prior_narrative: Optional[str] = None,
    ) -> str:
        """Build efficient prompt: game context + last year's narrative + prior year snapshot + current year data."""

        rel_context = ""
        if relationships:
            rel_lines = []
            for rel in relationships:
                trust_label = self._trust_label(rel.trust_score)
                rel_lines.append(f"- {rel.entity_name}: trust {rel.trust_score}/100 ({trust_label})")
            rel_context = "\n".join(rel_lines)
        else:
            rel_lines = []
            for name, score in self.trust_scores.items():
                trust_label = self._trust_label(score)
                rel_lines.append(f"- {name}: trust {score}/100 ({trust_label})")
            rel_context = "\n".join(rel_lines)

        event_context = ""
        if events:
            event_lines = []
            for evt in events:
                event_lines.append(f"- Q{evt.quarter}: {evt.event_type} - {evt.description}")
            event_context = "\n".join(event_lines)
        else:
            event_context = "No major events recorded."

        directives_str = "; ".join(directives) if directives else "no specific directives"
        covenant_status = "COVENANT BREACH" if fin.dscr < 3.0 else "covenants intact"

        # Prior year context (efficient: only end-of-year snapshot)
        prior_context = ""
        if prior_fin:
            prior_context = f"""LAST YEAR ({prior_fin.year}) — END OF YEAR:
Revenue: ${prior_fin.revenue:,.0f}
EBITDA: ${prior_fin.ebitda:,.0f} ({prior_fin.ebitda_margin:.1f}% margin)
Net Income: ${prior_fin.net_income:,.0f}
Cash: ${prior_fin.cash:,.0f}
Debt: ${prior_fin.total_debt:,.0f}
DSCR: {prior_fin.dscr:.2f}x

LAST YEAR'S NARRATIVE:
{prior_narrative if prior_narrative else "No prior narrative available."}


"""

        prompt = f"""{GAME_CONTEXT}

{NARRATIVE_FORMAT}

{prior_context}

YEAR {year} RESULTS:
Year type: {year_type}
Player directives: {directives_str}

FINANCIALS:
- Revenue: ${fin.revenue:,.0f}
- EBITDA: ${fin.ebitda:,.0f} ({fin.ebitda_margin:.1f}% margin)
- Net Income: ${fin.net_income:,.0f}
- Cash: ${fin.cash:,.0f}
- Total Debt: ${fin.total_debt:,.0f}
- DSCR: {fin.dscr:.2f}x ({covenant_status})
- CapEx: ${fin.capex:,.0f}
- Dividend: ${fin.dividend_paid:,.0f}

RELATIONSHIP DYNAMICS:
{rel_context}

EVENTS THIS YEAR:
{event_context}

TASK:
Write the year {year} narrative in the format shown above. Reference last year's narrative for continuity. Apply the key characteristics:
- Specific dates and months
- Character names, ages, and details
- Exact financial figures
- Dialogue that reveals character motivation
- Sensory details (temperatures, textures, sounds, smells)
- Embedded financial reality (DSCR, margins, cash)
- Personal stakes and emotional truth
- Specific locations and machines
- Consequences and cause-and-effect
- Cold, unsentimental, objective tone
- 3-5 paragraphs, not a list
- Use **bold** for month/date headers and key moments

Remember: Connor is 25, quiet, observant, doesn't bluff. The margin is brittle. Mike Castellano is the linchpin. Patricia Holt watches the DSCR. The world is indifferent to Connor's youth or good intentions.

Write the narrative now:"""

        return prompt

    def _call_deepseek(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            print("[DEEPSEEK] No API key configured")
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
                "max_tokens": 1500,
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
                narrative = data["choices"][0]["message"]["content"].strip()
                return narrative

        except requests.exceptions.Timeout:
            print("[DEEPSEEK] Timeout")
        except requests.exceptions.ConnectionError:
            print("[DEEPSEEK] Connection error")
        except requests.exceptions.HTTPError as e:
            print(f"[DEEPSEEK] HTTP error: {e}")
        except Exception as e:
            print(f"[DEEPSEEK] Error: {e}")

        return None

    def narrate_year(
        self,
        year: int,
        fin: FinancialSnapshot,
        company: Optional[CompanyState] = None,
        events: Optional[List[EventMemory]] = None,
        relationships: Optional[List[RelationshipState]] = None,
        prior_fin: Optional[FinancialSnapshot] = None,
        prior_narrative: Optional[str] = None,
        directives: Optional[List[str]] = None,
    ) -> str:
        """
        Main entry point. Generate year-end narrative.

        Args:
            year: Game year
            fin: FinancialSnapshot for the year (end-of-year only)
            company: CompanyState (optional)
            events: List of EventMemory (optional)
            relationships: List of RelationshipState (optional)
            prior_fin: Prior year's END-OF-YEAR FinancialSnapshot only (efficient)
            prior_narrative: Last year's narrative text (for continuity)
            directives: List of player directives (optional)

        Returns:
            3-5 paragraph year-end narrative texture in the specified format.
        """

        events = events or []
        relationships = relationships or []
        directives = directives or []

        year_type = self._classify_year(fin, prior_fin)

        prompt = self._build_deepseek_prompt(
            year, fin, company, events, relationships, year_type, directives, prior_fin, prior_narrative
        )
        narrative = self._call_deepseek(prompt)

        if not narrative:
            print(f"[NARRATIVE] DeepSeek failed, using fragment fallback for year {year}")
            fragments = self._select_texture_fragments(year_type, events, relationships)
            narrative = self._assemble_narrative_fallback(
                year, fin, company, fragments, year_type
            )

        # Convert markdown bold to HTML
        narrative = self._markdown_to_html(narrative)
        return narrative

    def _classify_year(
        self, fin: FinancialSnapshot, prior_fin: Optional[FinancialSnapshot]
    ) -> str:
        if prior_fin:
            revenue_change = (
                ((fin.revenue - prior_fin.revenue) / prior_fin.revenue * 100)
                if prior_fin.revenue > 0
                else 0
            )
        else:
            revenue_change = 0

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

    def _select_texture_fragments(
        self,
        year_type: str,
        events: List[EventMemory],
        relationships: List[RelationshipState],
    ) -> Dict:
        fragments = {"openings": [], "middles": [], "closes": [], "sensory": []}
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
            "ordinary": [
                "The year began with ice on the batch plant roof.",
                "January was cold and slow, as January always is.",
                "Connor drove to the plant on New Year's Day. Mike was already there.",
            ],
        }
        fragments["openings"].extend(
            year_openings.get(year_type, year_openings["ordinary"])
        )
        fragments["sensory"] = [
            "The crane groaned at 6 AM when the temperature dropped below freezing.",
            "The batch plant smelled of wet cement and diesel.",
            "Mike's coffee cup left a ring on every surface he touched.",
            "The fluorescent lights in the form shop flickered but never died.",
            "Connor's F-150 needed new shocks. He felt every pothole on I-65.",
        ]
        fragments["closes"].extend([
            "The books closed December 31. The accountant worked until 9 PM.",
            "Connor signed the year-end statements at 11 PM, alone in the office.",
            "The break room was empty when he walked through. The Sharpie was still there.",
        ])
        return fragments

    def _assemble_narrative_fallback(
        self,
        year: int,
        fin: FinancialSnapshot,
        company: Optional[CompanyState],
        fragments: Dict,
        year_type: str,
    ) -> str:
        opening = random.choice(fragments["openings"])
        sensory = random.choice(fragments["sensory"])
        close = random.choice(fragments["closes"])
        p1 = f"{opening} {sensory}"
        p2 = f"The margin was {fin.ebitda_margin:.1f} percent. The DSCR was {fin.dscr:.2f}x."
        if fin.dscr < 1.5:
            p3 = f"{close} The next year would be harder."
        else:
            p3 = close
        return "\n\n".join([p1, p2, p3])

    def to_dict(self) -> Dict:
        return {
            "trust_scores": self.trust_scores,
            "timestamp": datetime.now().isoformat(),
        }

