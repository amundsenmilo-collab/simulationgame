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
    
    def get_previous_snapshot(self, company_id: int, year: int) -> Dict:
        """Get the most recent financial snapshot before the given year"""
        cursor = self.db.execute(
            "SELECT * FROM financial_snapshots WHERE company_id = ? AND year < ? ORDER BY year DESC LIMIT 1",
            (company_id, year)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_employees(self, company_id: int) -> Tuple[List[Dict], float]:
        """Get all employees and calculate total payroll burden"""
        cursor = self.db.execute(
            "SELECT * FROM employees WHERE company_id = ? AND is_active = 1",
            (company_id,)
        )
        employees = [dict(row) for row in cursor.fetchall()]
        
        # Calculate payroll: salaried + hourly (2080 hours/year)
        total_payroll = 0
        for emp in employees:
            if emp['salary']:
                total_payroll += emp['salary']
            elif emp['hourly_wage']:
                total_payroll += emp['hourly_wage'] * 2080
        
        # Add payroll taxes (~15% burden)
        payroll_burden = total_payroll * 1.15
        return employees, payroll_burden
    
    def fast_forward_year(self, company_id: int, year: int,
                         directives: List[str]) -> Dict:
        """
        Execute one year of financial operations.
        Returns: P&L, balance sheet, cash flow, covenant check, narrative context
        """
        # Get previous year's snapshot
        prev = self.get_previous_snapshot(company_id, year)
        if not prev:
            raise ValueError(f"No financial data found for company {company_id}")
        
        # Years elapsed since 2025 (base year)
        years_elapsed = year - 2025
        
        # ===== REVENUE =====
        # Base revenue: $28M in 2025
        # Apply directives that affect capacity/pricing
        base_revenue = 28000000
        revenue_multiplier = 1.0
        
        # Check for capacity/expansion directives
        if any("expand" in d.lower() or "capex" in d.lower() for d in directives):
            revenue_multiplier += 0.05  # 5% growth from expansion
        
        # Check for price/bid directives
        if any("raise price" in d.lower() or "premium" in d.lower() for d in directives):
            revenue_multiplier += 0.03
        
        revenue = base_revenue * revenue_multiplier
        
        # ===== PAYROLL & LABOR COSTS =====
        employees, payroll_burden = self.get_employees(company_id)
        
        # Apply wage inflation
        wage_inflation = (1.04 ** years_elapsed)
        
        # Check for wage directives
        wage_adjustment = 1.0
        if any("raise wage" in d.lower() or "increase wage" in d.lower() for d in directives):
            wage_adjustment = 1.10  # 10% raise
        
        adjusted_payroll = payroll_burden * wage_inflation * wage_adjustment
        
        # ===== COGS & OPEX =====
        # Base COGS+OPEX: $23.52M in 2025 (84% of revenue)
        base_cogs_opex = 23520000
        
        # Material inflation
        material_inflation = (1.03 ** years_elapsed)
        
        # Deferred maintenance impact
        maintenance_cost = 0
        if any("defer" in d.lower() or "skip" in d.lower() for d in directives):
            maintenance_cost = -50000  # Saves money short-term
        elif any("repair" in d.lower() or "fix" in d.lower() or "replace" in d.lower() for d in directives):
            maintenance_cost = 200000  # Costs money
        
        cogs_opex = (base_cogs_opex * material_inflation) + adjusted_payroll + maintenance_cost
        
        # ===== EBITDA =====
        ebitda = revenue - cogs_opex
        ebitda_margin = self.calculate_ebitda_margin(ebitda, revenue)
        
        # ===== DEPRECIATION =====
        # Expansion asset (2019) in year 6-7 of MACRS: $680K → drops to $420K in year 7
        if year <= 2025:
            depreciation = 1180000
        elif year == 2026:
            depreciation = 1180000
        elif year == 2027:
            depreciation = 420000
        else:
            depreciation = 300000
        
        # ===== EBIT =====
        ebit = ebitda - depreciation
        
        # ===== INTEREST =====
        # Term loan: $2.5M at 6.5%, 4yr remaining (2026-2029)
        # Equipment line: $800K at 7.25%, 3yr remaining (2026-2028)
        term_loan_balance = 2500000
        equipment_line_balance = 800000
        
        # Amortize loans
        if year >= 2026:
            years_into_term = year - 2026
            if years_into_term < 4:
                term_loan_balance = 2500000 * (1 - (years_into_term / 4))
            else:
                term_loan_balance = 0
        
        if year >= 2026:
            years_into_equip = year - 2026
            if years_into_equip < 3:
                equipment_line_balance = 800000 * (1 - (years_into_equip / 3))
            else:
                equipment_line_balance = 0
        
        interest = (term_loan_balance * 0.065) + (equipment_line_balance * 0.0725)
        
        # ===== TAXABLE INCOME & TAX =====
        taxable_income = ebit - interest
        tax = max(0, taxable_income * 0.21)  # 21% federal C-corp tax
        
        # ===== NET INCOME =====
        net_income = taxable_income - tax
        
        # ===== CASH FLOW =====
        # Simplified: Net income + depreciation - capex - debt service
        capex = 0
        if any("capex" in d.lower() or "expand" in d.lower() for d in directives):
            capex = 300000
        
        debt_service = (term_loan_balance * 0.25) + (equipment_line_balance * 0.33)  # Principal payments
        
        cash_flow = net_income + depreciation - capex - debt_service
        cash = prev['cash'] + cash_flow
        
        # ===== DEBT =====
        total_debt = term_loan_balance + equipment_line_balance
        
        # ===== DSCR =====
        dscr = self.calculate_dscr(ebitda, debt_service) if debt_service > 0 else float('inf')
        
        # ===== COVENANT CHECK =====
        covenant = self.check_covenant(cash, dscr)
        
        # ===== SAVE SNAPSHOT =====
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO financial_snapshots
            (company_id, year, quarter, revenue, cogs_opex, ebitda, depreciation, ebit, interest, taxable_income, tax, net_income, cash, total_debt, dscr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_id, year, 1, revenue, cogs_opex, ebitda, depreciation, ebit, interest, taxable_income, tax, net_income, cash, total_debt, dscr))
        self.db.commit()
        
        # ===== RETURN STRUCTURED RESULT =====
        return {
            'year': year,
            'revenue': round(revenue, 0),
            'cogs_opex': round(cogs_opex, 0),
            'ebitda': round(ebitda, 0),
            'ebitda_margin': ebitda_margin,
            'depreciation': round(depreciation, 0),
            'ebit': round(ebit, 0),
            'interest': round(interest, 0),
            'tax': round(tax, 0),
            'net_income': round(net_income, 0),
            'cash': round(cash, 0),
            'total_debt': round(total_debt, 0),
            'dscr': dscr,
            'debt_service': round(debt_service, 0),
            'capex': round(capex, 0),
            'covenant_breach': covenant['breach'],
            'covenant_details': covenant,
            'directives_applied': directives
        }
    
    def get_company_state(self, company_id: int) -> Dict:
        cursor = self.db.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

