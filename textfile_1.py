from typing import Dict, List


# 2026 baseline financials for Asford Materials
BASELINE = {
    "year": 2026,
    "revenue": 4_800_000.0,
    "cogs_ratio": 0.62,        # cost of goods as % of revenue
    "opex": 980_000.0,         # fixed operating expenses
    "depreciation": 120_000.0,
    "interest": 95_000.0,
    "tax_rate": 0.26,
    "debt": 1_200_000.0,
    "cash": 540_000.0,
    "annual_debt_service": 180_000.0,
}

# Directive modifiers: each directive keyword maps to revenue/cost adjustments
DIRECTIVE_EFFECTS: Dict[str, Dict[str, float]] = {
    "expand":        {"revenue_delta": 0.08,  "opex_delta": 0.05},
    "cut":           {"revenue_delta": -0.03, "opex_delta": -0.07},
    "hire":          {"revenue_delta": 0.04,  "opex_delta": 0.06},
    "automate":      {"revenue_delta": 0.02,  "opex_delta": -0.04},
    "acquire":       {"revenue_delta": 0.12,  "opex_delta": 0.09,  "debt_delta": 0.15},
    "divest":        {"revenue_delta": -0.06, "opex_delta": -0.05, "debt_delta": -0.08},
    "refinance":     {"interest_delta": -0.10},
    "invest":        {"revenue_delta": 0.05,  "opex_delta": 0.03},
    "restructure":   {"revenue_delta": -0.02, "opex_delta": -0.08},
    "default":       {"revenue_delta": 0.02,  "opex_delta": 0.025},  # baseline growth
}

REVENUE_GROWTH_RATE = 0.025   # organic annual growth
INFLATION_RATE = 0.035        # cost inflation per year
MIN_CASH_COVENANT = 200_000.0
MIN_DSCR_COVENANT = 3.0


class FinanceEngine:

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calculate_dscr(self, ebitda: float, debt_service: float) -> float:
        """Debt Service Coverage Ratio"""
        if debt_service <= 0:
            return 99.0
        return round(ebitda / debt_service, 2)

    def _calculate_ebitda_margin(self, ebitda: float, revenue: float) -> float:
        if revenue <= 0:
            return 0.0
        return round((ebitda / revenue) * 100, 1)

    def _check_covenant(self, cash: float, dscr: float) -> bool:
        return not (cash >= MIN_CASH_COVENANT and dscr >= MIN_DSCR_COVENANT)

    def _parse_directive_effects(self, directives: List[str]) -> Dict[str, float]:
        """Aggregate multiplier deltas from all directives."""
        totals: Dict[str, float] = {
            "revenue_delta": 0.0,
            "opex_delta": 0.0,
            "debt_delta": 0.0,
            "interest_delta": 0.0,
        }
        matched_any = False
        for directive in directives:
            directive_lower = directive.lower()
            for keyword, effects in DIRECTIVE_EFFECTS.items():
                if keyword == "default":
                    continue
                if keyword in directive_lower:
                    for k, v in effects.items():
                        totals[k] = totals.get(k, 0.0) + v
                    matched_any = True
                    break

        if not matched_any:
            # Apply baseline organic growth when no specific directive matches
            for k, v in DIRECTIVE_EFFECTS["default"].items():
                totals[k] = totals.get(k, 0.0) + v

        return totals

    # ------------------------------------------------------------------
    # Core public method
    # ------------------------------------------------------------------

    def fast_forward_year(self, year: int, directives: List[str]) -> Dict:
        """
        Calculate one year of financials from the 2026 baseline.
        No database required — pure arithmetic.

        Args:
            year:       Target year (2026 = baseline, 2027+ = projected).
            directives: List of player directive strings.

        Returns:
            Dict with keys: revenue, ebitda, ebitda_margin, net_income,
                            cash, debt, dscr, covenant_breach.
        """
        years_from_baseline = max(0, year - BASELINE["year"])

        # --- Organic growth / inflation on baseline ---
        revenue = BASELINE["revenue"] * (1 + REVENUE_GROWTH_RATE) ** years_from_baseline
        opex = BASELINE["opex"] * (1 + INFLATION_RATE) ** years_from_baseline
        depreciation = BASELINE["depreciation"]
        interest = BASELINE["interest"]
        debt = BASELINE["debt"]
        cash = BASELINE["cash"]
        debt_service = BASELINE["annual_debt_service"]

        # --- Apply directive effects (as % adjustments on the grown base) ---
        effects = self._parse_directive_effects(directives)

        revenue *= (1 + effects["revenue_delta"])
        opex *= (1 + effects["opex_delta"])
        debt *= (1 + effects["debt_delta"])
        interest *= (1 + effects["interest_delta"])

        # --- P&L ---
        cogs = revenue * BASELINE["cogs_ratio"]
        gross_profit = revenue - cogs
        ebitda = gross_profit - opex
        ebit = ebitda - depreciation
        taxable_income = max(0.0, ebit - interest)
        tax = taxable_income * BASELINE["tax_rate"]
        net_income = taxable_income - tax

        # --- Balance sheet approximation ---
        # Cash grows by net income, shrinks by debt service
        cash = cash + net_income - debt_service
        # Debt reduced by principal portion of debt service (rough: 40% of service)
        debt = max(0.0, debt - debt_service * 0.4)

        # --- Ratios ---
        ebitda_margin = self._calculate_ebitda_margin(ebitda, revenue)
        dscr = self._calculate_dscr(ebitda, debt_service)
        covenant_breach = self._check_covenant(cash, dscr)

        return {
            "revenue":        round(revenue, 2),
            "ebitda":         round(ebitda, 2),
            "ebitda_margin":  ebitda_margin,
            "net_income":     round(net_income, 2),
            "cash":           round(cash, 2),
            "debt":           round(debt, 2),
            "dscr":           dscr,
            "covenant_breach": covenant_breach,
        }
