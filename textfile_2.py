import os
import requests
from typing import List, Dict

HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"


class NarrativeEngine:

    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self._headers = (
            {"Authorization": f"Bearer {self.hf_token}"}
            if self.hf_token
            else {}
        )

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

        prompt = f"""<s>[INST] You are an objective, unsentimental game master narrating a business simulation. No cheering. No ensuring victory. The world is indifferent.

GAME STATE — {year}:
- Directives issued: {directives_str}
- Revenue: ${revenue_m:.2f}M | EBITDA: ${ebitda_m:.2f}M ({margin:.1f}% margin)
- Net income: ${net_income_m:.2f}M | Cash: ${cash_m:.2f}M | Debt: ${debt_m:.2f}M
- DSCR: {dscr:.2f} | {covenant_str}

Write 2-3 sentences of narrative texture. Cold, specific, human. No lists. No dashboards. Show, don't tell. Include one sensory detail (smell, sound, temperature). If a character speaks, let their words reveal their motivation, not explain it. [/INST]"""
        return prompt

    # ------------------------------------------------------------------
    # Core public method
    # ------------------------------------------------------------------

    def generate_texture(self, financial_data: Dict, directives: List[str], year: int) -> str:
        """
        Generate narrative texture via Hugging Face Inference API.

        Args:
            financial_data: Dict returned by FinanceEngine.fast_forward_year().
            directives:     List of player directive strings.
            year:           Game year being narrated.

        Returns:
            Narrative string. Falls back to a plain summary on API errors.
        """
        prompt = self._build_prompt(financial_data, directives, year)

        if not self.hf_token:
            return self._fallback_narrative(financial_data, directives, year)

        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "do_sample": True,
                    "return_full_text": False,
                },
            }
            response = requests.post(
                HF_API_URL,
                headers=self._headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # HF returns a list: [{"generated_text": "..."}]
            if isinstance(data, list) and data:
                generated = data[0].get("generated_text", "").strip()
            elif isinstance(data, dict):
                generated = data.get("generated_text", "").strip()
            else:
                generated = ""

            # Trim at first double-newline to avoid runaway output
            if "\n\n" in generated:
                generated = generated.split("\n\n")[0].strip()

            return generated if generated else self._fallback_narrative(financial_data, directives, year)

        except requests.exceptions.Timeout:
            return self._fallback_narrative(financial_data, directives, year, reason="API timeout")
        except requests.exceptions.HTTPError as e:
            return self._fallback_narrative(financial_data, directives, year, reason=str(e))
        except Exception as e:
            return self._fallback_narrative(financial_data, directives, year, reason=str(e))

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
        breach = financial_data.get("covenant_breach", False)
        directive_summary = ", ".join(directives[:2]) if directives else "standard operations"

        covenant_note = " The bank's covenant threshold has been breached." if breach else ""
        suffix = f" [{reason}]" if reason else ""

        return (
            f"In {year}, Asford Materials posted ${revenue_m:.1f}M in revenue and "
            f"${ebitda_m:.1f}M EBITDA following directives to {directive_summary}.{covenant_note}"
            f"{suffix}"
        )
