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

The Plant — Birmingham
Product Line | Annual Revenue | Capacity | Utilization
RCP pipe | $9.2M | $10.5M | 88%
Manholes | $6.1M | $7.0M | 87%
Junction boxes | $5.6M | $6.4M | 88%
Inlets/end treatments | $7.1M | $8.2M | 86%
Total Precast | $28.0M | $32.1M | 87%

The Problem: The plant is maxed out. The equipment is old but functional. The father deferred maintenance for six years. The expansion bay (added 2019) is the only reason you hit $28M. The main bay is crumbling. The form shop roof is gone — tarpaulins and buckets. The batch plant needs a new mixer drum. The crane is 18 years old and has a hairline crack in the hook block. Mike has documented all of this. Your father filed the reports in a drawer.

Land & Buildings: 7 acres, 14,000 sq ft, functional but tired, 14 years old, heavy industrial, no rail, no union.

THE MARGIN IS EXTRACTION, NOT COMPETENCE
The EBITDA margin of 16% is real but brittle. It rests on three pillars:

1. Labor compression. 29 production workers at $19.50/hour in a $26–28 market. Annual underpayment: ~$452,000 versus market. Barry III extracted this every year.

2. Deferred maintenance. $866,000 in replacement backlog. Equipment functional until it isn't. The crane hook block, batch mixer drum, and form shop roof are time bombs.

3. Mike Castellano. He makes $78,000, knows the operation completely, and has not quit. If he leaves, the margin collapses.

Adjusted for market wages, EBITDA margin is 14.4% — healthy but unexceptional. The extra 1.6 points are the lie your father told."""

# Narrative format instruction
NARRATIVE_FORMAT = """NARRATIVE FORMAT INSTRUCTION:

You will narrate each year in a specific, grounded format. Here is an example for Year 5 (2030):

January. The 2 new estimators start. Brian Holt, 31, formerly Forterra Atlanta. Marcus Webb, 27, UAB Civil Engineering, Connor's year. They train in Birmingham March 1–15, then rotate to Rockford March 16–31. High-end Airbnb in Sylacauga: $180/night × 14 nights × 2 rooms = $5,040. Per diem: $75/day × 14 × 2 = $2,100. They drive company F-150s. Brian hits a deer on US-280 March 18. The truck is repairable. The deer is not. $4,200 insurance deductible. Brian is fine. He does not mention the deer again.

March 15. The lead estimator is promoted to Director of Estimating. Salary: $130,240. The $20,000 bonus is tied to Rockford's first-year DSCR. He does not know the target is 3.0x by Q4 2031. He knows his bonus is tied to "plant performance." He buys a bigger boat in October. He names it "The Underbid II."

April 15. Rockford Phase 1 opens. The batch plant is operational. The first pour is a 48-inch RCP pipe for Jefferson County Utilities. Mike Castellano is on site at 5:30 AM. Connor is there at 5:45. The concrete is 4,000 psi, fly ash blend, same spec as Birmingham. The pipe cures 28 days. It passes QC. The second pour is May 3. By June, the plant produces 40 pipes a day, 12 manholes a week, 8 junction boxes. The metal fab shop is not yet operational — Wendell the GC is still installing the shear and press. It opens July 1.

May. Three Rockford workers quit. Two are fired in June for showing up drunk. Darius Cole, the plant manager, hires replacements from Alexander City, Talladega, Sylacauga. The labor pool is thin. The quality is inconsistent. In July, a batch of 24-inch pipe fails slump test — too much water, not enough cement. $12,000 in scrap. Mike drives from Sylacauga (unit 3B) and spends 48 hours recalibrating the batch plant. He does not sleep. He fixes it. He says to Darius, "You call me before you call Connor. Always." Darius says, "Yes sir."

July. The metal fab shop opens. The first ring and cover set is produced July 15. It is for a Birmingham DOT job, shipped from Rockford because the Birmingham fab shop is not yet built. The margin is negative — $18,000 in red ink before September. The "Proudly made in the USA by Asford Materials" stamp is applied. The paint is still wet when it ships. The stamp smudges. The DOT inspector does not notice.

August. Patricia Holt visits Rockford. She wears hard boots and a Regions Bank polo. She walks the batch plant. She asks Darius about the July scrap loss. Darius tells her about Mike's 48-hour fix. She writes in her notebook. She asks Connor about the DSCR. He says, "1.57x this year. 2.5x next year. 3.2x the year after." She says, "You need 3.0x by Q4 2031. Not 2032." Connor says, "I know." She says, "Your personal guarantee is on file. Your lake house is on file. Your condo is on file. I hope you swim well." Connor does not swim well. He does not tell her.

September. BBTW installs the vending machine. Rosa stocks it. Sandwiches from a Birmingham wholesaler ($3.50 cost, $6.50 sale), snacks from Sam's Club, detergent and dryer sheets from Dollar General. Revenue: $340/month. Cost of goods: $180. Net: $160/month. Rosa gets a $75/month stipend to stock it. She says, "I am not a store clerk." Connor gives her $100. She says, "Fine." The machine jams twice in August. Carl the handyman fixes it. He charges $40/hour. Connor pays him from BBTW. Derek from IT set up the SKU in Odoo: "VENDING-001." The revenue stream is tracked. It is $1,920/year. It is not material. It is tracked.

October. The 2 engineers (hired Q2, deferred from 2029) begin writing specs. FEMA shelter designs. Wind foundation concepts. Prison module preliminary drawings. They have no orders. They have no permits. They have no customers. They have salaries: $130,000 each. Connor says, "Write it. Patent it. Wait." They write. They wait.

November. Rockford produces its 10,000th pipe. Mike Castellano does not celebrate. He is 46. He lives in unit 3B of the Sylacauga apartment building. He has not taken a Saturday off since March 2029. He has $180,000 in savings. He still wants 5% of the company. Connor still has not answered. Harold Vance runs Birmingham. The plant is stable. The union is gone. The Odoo tablets show 94% uptime. The Director of Estimating wins a $4.2M DOT job in November — approach slabs for the I-59 widening. Margin: 11%. He does not get his $20,000 bonus. The DSCR is 1.57x. He buys a third boat anyway. He names it "The DSCR."

December 31. The books close. No dividend from Asford Materials. The signal is sent: we are serious. The bank knows. Patricia Holt knows. The $938,186 cash is above the $500,000 minimum. The DSCR is 1.57x. The trajectory is 1.57x → 2.5x → 3.2x. If Rockford scales. If the specialty lines work. If the engineers write specs that someone buys. If the metal fab shop turns profitable. If Mike Castellano does not quit. If Connor Asford does not drown.

Connor sits on the dock. It is 38 degrees. The water is black. The Boston Whaler is covered for winter. He has $340,000 in personal cash. He has a $9.5M company. He has a lake house with no mortgage. He has a mother who does not call. He has a sister who does not call. He has Mike Castellano, in unit 3B, in Sylacauga, running a plant that is not his, who wants 5%, who Connor will never give it to.

He thinks about 2031. He thinks about the DSCR. He thinks about Patricia Holt, who hopes he swims well. He does not swim well. He does not tell her.

KEY CHARACTERISTICS OF THIS FORMAT:
- Specific dates and months (January, March 15, April 15, etc.)
- Character names, ages, and details (Brian Holt, 31, formerly Forterra Atlanta)
- Exact financial figures ($180/night, $5,040, $4,200 deductible)
- Dialogue that reveals character motivation and stakes
- Sensory details (38 degrees, black water, hard boots, wet paint)
- Embedded financial reality (DSCR targets, margins, cash positions)
- Personal stakes and emotional truth (Connor does not swim well, Mike wants 5%, mother does not call)
- Specific locations (unit 3B in Sylacauga, the dock, the batch plant)
- Specific machines and equipment (Boston Whaler, F-150s, batch plant mixer)
- Consequences and cause-and-effect (Brian hits deer → $4,200 deductible, pipe fails → $12,000 scrap)
- Tone: Cold, unsentimental, objective. No cheerleading. The world is indifferent.
- Length: 3-5 paragraphs, not a list. Tell a story.

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
    dividend_paid: float
    capex: float


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
Dividend: ${prior_fin.dividend_paid:,.0f}

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
                "max_tokens": 1200,
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
            "The CHOMEX break room was empty when he walked through. The Sharpie was still there.",
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

