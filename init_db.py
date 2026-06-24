import sqlite3
from datetime import datetime

def init_database(db_path: str = "asford.db"):
    """Initialize SQLite database with schema and starting data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT,
            founded_year INTEGER,
            cash REAL DEFAULT 0,
            total_debt REAL DEFAULT 0,
            revenue_annual REAL DEFAULT 0,
            ebitda_annual REAL DEFAULT 0,
            net_income REAL DEFAULT 0,
            dscr REAL DEFAULT 0
        )
    """)
    
    # Financial snapshots (year-by-year)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_snapshots (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            quarter INTEGER DEFAULT 1,
            revenue REAL DEFAULT 0,
            cogs_opex REAL DEFAULT 0,
            ebitda REAL DEFAULT 0,
            depreciation REAL DEFAULT 0,
            ebit REAL DEFAULT 0,
            interest REAL DEFAULT 0,
            taxable_income REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            net_income REAL DEFAULT 0,
            cash REAL DEFAULT 0,
            total_debt REAL DEFAULT 0,
            dscr REAL DEFAULT 0,
            dividend_paid REAL DEFAULT 0,
            capex REAL DEFAULT 0,
            UNIQUE(company_id, year, quarter)
        )
    """)
    
    # Employees
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            name TEXT,
            role TEXT,
            salary REAL DEFAULT 0,
            hourly_wage REAL,
            hire_date TEXT,
            trust_score INTEGER DEFAULT 50,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Narrative log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS narrative_log (
            id INTEGER PRIMARY KEY,
            year INTEGER NOT NULL,
            quarter INTEGER DEFAULT 1,
            context TEXT,
            narrative_text TEXT,
            entities_involved TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # LLM context (for RAG)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_context (
            id INTEGER PRIMARY KEY,
            context_type TEXT,
            content TEXT,
            entities TEXT,
            year INTEGER,
            importance INTEGER DEFAULT 5,
            decay_rate INTEGER DEFAULT 1
        )
    """)
    
    # Insert starting company state (Jan 1, 2026)
    cursor.execute("""
        INSERT OR IGNORE INTO companies 
        (id, name, entity_type, founded_year, cash, total_debt, revenue_annual, ebitda_annual, net_income, dscr)
        VALUES (1, 'Asford Materials, Inc.', 'C-corp', 1978, 850000, 3300000, 28000000, 4480000, 2387380, 1.46)
    """)
    
    # Insert starting financial snapshot (Year 0 = 2025 TTM)
    cursor.execute("""
        INSERT OR IGNORE INTO financial_snapshots
        (company_id, year, quarter, revenue, cogs_opex, ebitda, depreciation, ebit, interest, taxable_income, tax, net_income, cash, total_debt, dscr)
        VALUES (1, 2025, 4, 28000000, 23520000, 4480000, 1180000, 3300000, 278000, 3022000, 634620, 2387380, 850000, 3300000, 1.46)
    """)
    
    # Insert employees
    employees = [
        (1, 1, "Mike Castellano", "VP Operations", 78000, None, "2023-01-01", 75, 1),
        (1, 2, "PE/Estimator", "Engineering", 65000, None, "2023-06-01", 70, 1),
        (1, 3, "Office Manager", "Admin", 52000, None, "2020-01-01", 65, 1),
        (1, 4, "QC Lead", "Quality", 58000, None, "2022-01-01", 60, 1),
        (1, 5, "Foreman 1", "Production", 55000, None, "2019-01-01", 70, 1),
        (1, 6, "Foreman 2", "Production", 55000, None, "2020-01-01", 65, 1),
    ]
    
    for emp in employees:
        cursor.execute("""
            INSERT OR IGNORE INTO employees 
            (company_id, id, name, role, salary, hire_date, trust_score, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, emp)
    
    # Insert 29 hourly workers
    for i in range(29):
        cursor.execute("""
            INSERT OR IGNORE INTO employees 
            (company_id, id, name, role, hourly_wage, hire_date, trust_score, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, 100 + i, f"Worker {i+1}", "Production", 19.50, "2020-01-01", 50, 1))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_database()

