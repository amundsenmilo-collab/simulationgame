"""
Narrative engine for Asford Materials Hyperrealism Empire Builder.
Minimal context: only current year financials + prior year narrative.
DeepSeek generates rich narratives with minimal token usage.
"""
import os
import re
import requests
from typing import Optional
from dataclasses import dataclass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Game context (embedded once, not sent to DeepSeek every time)
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
Net Income: $2,387,380"""


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


class NarrativeEngine:
    """
    Minimal narrative engine.
    Input: current year financials + prior year narrative only.
    Output: rich narrative for current year.
    """

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY

    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown bold (**text**) to HTML <strong>text</strong>."""
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

    def _build_prompt(
        self,
        year: int,
        fin: FinancialSnapshot,
        prior_narrative: Optional[str] = None,
        directives: Optional[list] = None,
    ) -> str:
        """
        Build minimal prompt: only current year financials + prior year narrative.
        No full history, no event lists, no relationship tracking.
        """
        directives_str = "; ".join(directives) if directives else "no specific directives"
        covenant_status = "COVENANT BREACH" if fin.dscr < 3.0 else "covenants intact"

        prior_context = ""
        if prior_narrative:
            prior_context = f"""LAST YEAR'S NARRATIVE (for continuity):
{prior_narrative}

"""

        prompt = f"""You are writing a year-end narrative for a business simulation game.

GAME CONTEXT:
{GAME_CONTEXT}

{prior_context}

YEAR {year} FINANCIALS:
- Revenue: ${fin.revenue:,.0f}
- EBITDA: ${fin.ebitda:,.0f} ({fin.ebitda_margin:.1f}% margin)
- Net Income: ${fin.net_income:,.0f}
- Cash: ${fin.cash:,.0f}
- Total Debt: ${fin.total_debt:,.0f}
- DSCR: {fin.dscr:.2f}x ({covenant_status})

PLAYER DIRECTIVES: {directives_str}

NARRATIVE FORMAT:
Write 3-5 paragraphs in a cold, unsentimental, objective tone. Use specific dates, character names, exact financial figures, dialogue, and sensory details. Use **bold** for month/date headers and key moments. Reference last year's narrative for continuity. Focus on consequences and cause-and-effect. The world is indifferent to Connor's youth or good intentions.

Example opening:
**January {year}.** Connor Asford sits in his father's office for the first time. The chair is still warm from Barry III's body. The desk has a ring from a sweating glass...

Write the year {year} narrative now:"""

        return prompt

    def _call_deepseek(self, prompt: str) -> Optional[str]:
        """Call DeepSeek API."""
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
        prior_narrative: Optional[str] = None,
        directives: Optional[list] = None,
    ) -> str:
        """
        Generate year-end narrative.
        
        Args:
            year: Game year
            fin: FinancialSnapshot for the year
            prior_narrative: Last year's narrative (for continuity only)
            directives: List of player directives
        
        Returns:
            HTML-formatted narrative
        """
        directives = directives or []

        prompt = self._build_prompt(year, fin, prior_narrative, directives)
        narrative = self._call_deepseek(prompt)

        if not narrative:
            print(f"[NARRATIVE] DeepSeek failed for year {year}")
            narrative = self._fallback_narrative(year, fin)

        # Convert markdown bold to HTML
        narrative = self._markdown_to_html(narrative)
        return narrative

    def _fallback_narrative(self, year: int, fin: FinancialSnapshot) -> str:
        """Fallback narrative if DeepSeek fails."""
        return f"""**Year {year}.** The books closed. Revenue was ${fin.revenue:,.0f}. EBITDA margin was {fin.ebitda_margin:.1f}%. The DSCR was {fin.dscr:.2f}x. Connor signed the year-end statements alone in the office. The next year would be harder."""

