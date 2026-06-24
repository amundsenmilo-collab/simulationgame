import os
import requests
from typing import List, Dict

# DeepSeek API endpoint
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


class NarrativeEngine:

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, financial_data: Dict, directives: List[str], year: int) -> str:
        revenue_m = financial_data.get("revenue", 0) / 1_000_000
        ebitda_m = financial_data.get("ebitda", 0) / 1_000_000
        margin = financial_data.get("ebitda_margin", 0)
        net_income_m = financial_data.get("net_income", 0) / 1_000_000
        cash_m = financial_data.get("cash", 0) / 1_000_000
        debt_m = financial_data.get("debt", 0) / 1_000_000
        dscr = financial_data.get("dscr", 0)
        breach = financial_data.get("covenant_breach", False)

        directives_str = "; ".join(directives) if directives else "no specific directives"
        covenant_str = "COVENANT BREACH — bank is watching." if breach else "covenants intact."

        prompt = f"""You are an objective, unsentimental game master narrating a business simulation. No cheering. No ensuring victory. The world is indifferent.

GAME STATE — {year}:
- Directives issued: {directives_str}
- Revenue: ${revenue_m:.2f}M | EBITDA: ${ebitda_m:.2f}M ({margin:.1f}% margin)
- Net income: ${net_income_m:.2f}M | Cash: ${cash_m:.2f}M | Debt: ${debt_m:.2f}M
- DSCR: {dscr:.2f} | {covenant_str}

Write 2-3 sentences of narrative texture. Cold, specific, human. No lists. No dashboards. Show, don't tell. Include one sensory detail (smell, sound, temperature). If a character speaks, let their words reveal their motivation, not explain it."""
        return prompt

    # ------------------------------------------------------------------
    # Core public method
    # ------------------------------------------------------------------

    def generate_texture(self, financial_data: Dict, directives: List[str], year: int) -> str:
        """
        Generate narrative texture via DeepSeek API.

        Args:
            financial_data: Dict returned by FinanceEngine.fast_forward_year().
            directives:     List of player directive strings.
            year:           Game year being narrated.

        Returns:
            Narrative string. Falls back to a plain summary on API errors.
        """
        if not self.api_key:
            return self._fallback_narrative(financial_data, directives, year, reason="No DEEPSEEK_API_KEY")

        prompt = self._build_prompt(financial_data, directives, year)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            }
            response = requests.post(
                DEEPSEEK_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # DeepSeek returns: {"choices": [{"message": {"content": "..."}}]}
            if data.get("choices") and len(data["choices"]) > 0:
                generated = data["choices"][0]["message"]["content"].strip()
                
                # Trim at first double-newline to avoid runaway output
                if "\n\n" in generated:
                    generated = generated.split("\n\n")[0].strip()

                if generated:
                    return generated

        except requests.exceptions.Timeout:
            return self._fallback_narrative(financial_data, directives, year, reason="DeepSeek timeout")
        except requests.exceptions.ConnectionError:
            return self._fallback_narrative(financial_data, directives, year, reason="DeepSeek unreachable")
        except requests.exceptions.HTTPError as e:
            return self._fallback_narrative(financial_data, directives, year, reason=str(e))
        except Exception as e:
            return self._fallback_narrative(financial_data, directives, year, reason=str(e))

        return self._fallback_narrative(financial_data, directives, year, reason="No response from DeepSeek")

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_narrative(
        self,
        financial_data: Dict,
        directives: List[str],
        year: int,
        reason: str = "",
    ) -> str:
        revenue_m = financial_data.get("revenue", 0) / 1_000_000
        ebitda_m = financial_data.get("ebitda", 0) / 1_000_000
        margin = financial_data.get("ebitda_margin", 0)
        breach = financial_data.get("covenant_breach", False)
        directive_summary = ", ".join(directives[:2]) if directives else "standard operations"

        covenant_note = " The bank's covenant threshold has been breached." if breach else ""
        suffix = f" [{reason}]" if reason else ""

        return (
            f"In {year}, Asford Materials posted ${revenue_m:.1f}M in revenue and "
            f"${ebitda_m:.1f}M EBITDA ({margin:.1f}% margin) following directives to {directive_summary}.{covenant_note}"
            f"{suffix}"
        )

