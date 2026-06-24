import sqlite3
from typing import Dict, List, Tuple
from datetime import datetime

class FinanceEngine:
    def __init__(self, db_path: str = "asford.db"):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
    
    def calculate_dscr(self, ebitda: float, debt_service: float) -> float:
        """Debt Service Coverage Ratio"""
        if debt_service <= 0:
            return float('inf')
        return round(ebitda / debt_service, 2)
    
    def calculate_ebitda_margin(self, ebitda: float, revenue: float) -> float:
        if revenue <= 0:
            return 0
        return round((ebitda / revenue) * 100, 1)
    
    def apply_inflation(self, base_amount: float, years: int, 
                       wage_rate: float = 0.04,
                       material_rate: float = 0.03,
                       service_rate: float = 0.035) -> Dict[str, float]:
        """Apply compounded inflation by category"""
        return {
            'wages': round(base_amount * (1 + wage_rate) ** years, 2),
            'materials': round(base_amount * (1 + material_rate) ** years, 2),
            'services': round(base_amount * (1 + service_rate) ** years, 2)
        }
    
    def check_covenant(self, cash: float, dscr: float, 
                      min_cash: float = 200000,
                      min_dscr: float = 3.0) -> Dict[str, any]:
        """Check bank covenant compliance"""
        return {
            'cash_pass': cash >= min_cash,
            'dscr_pass': dscr >= min_dscr,
            'cash_amount': cash,
            'dscr_value': dscr,
            'breach': not (cash >= min_cash and dscr >= min_dscr)
        }
    
    def fast_forward_year(self, company_id: int, year: int,
                         directives: Dict) -> Dict:
        """
        Execute one year of financial operations.
        Returns: P&L, balance sheet, cash flow, covenant check
        """
        # This is where your Python model runs
        # Query current state, apply directives, calculate outcomes
        # Return structured results for narrative layer
        pass
    
    def get_company_state(self, company_id: int) -> Dict:
        cursor = self.db.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else {}