"""
Database layer for Asford Materials game state.
Stores financials, trust scores, events, decisions, relationships.
Keeps DeepSeek token-efficient by only passing last narrative + prior snapshot.
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/asford")


class GameDatabase:
    """PostgreSQL backend for game state."""

    def __init__(self):
        self.conn_string = DATABASE_URL

    def _get_conn(self):
        """Get a database connection."""
        return psycopg2.connect(self.conn_string)

    def init_schema(self):
        """Initialize database schema if not exists."""
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            # Companies
            cur.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    entity_type TEXT DEFAULT 'C-corp',
                    founded_year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Relationships (NPC trust scores)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id SERIAL PRIMARY KEY,
                    entity_name TEXT NOT NULL UNIQUE,
                    entity_type TEXT DEFAULT 'person',
                    trust_score INTEGER DEFAULT 50 CHECK(trust_score BETWEEN 0 AND 100),
                    last_interaction DATE,
                    key_facts JSONB DEFAULT '[]',
                    promises_made TEXT,
                    promises_broken INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Financial Snapshots (year-end only)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS financials (
                    id SERIAL PRIMARY KEY,
                    year INTEGER NOT NULL UNIQUE,
                    revenue REAL,
                    ebitda REAL,
                    ebitda_margin REAL,
                    net_income REAL,
                    cash REAL,
                    total_debt REAL,
                    dscr REAL,
                    dividend_paid REAL DEFAULT 0,
                    capex REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Events (what happened each year)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    year INTEGER,
                    event_type TEXT,
                    description TEXT NOT NULL,
                    entities_involved JSONB DEFAULT '[]',
                    financial_impact REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Decisions (player directives)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id SERIAL PRIMARY KEY,
                    year INTEGER,
                    directive_text TEXT NOT NULL,
                    outcome TEXT,
                    financial_impact REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Narrative Log (for GitHub commits)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS narrative_log (
                    id SERIAL PRIMARY KEY,
                    year INTEGER NOT NULL UNIQUE,
                    narrative_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            print("[DB] Schema initialized")
        except Exception as e:
            conn.rollback()
            print(f"[DB] Schema init error: {e}")
        finally:
            cur.close()
            conn.close()

    def save_year_result(
        self,
        year: int,
        financials: Dict,
        narrative: str,
        directives: List[str],
        trust_scores: Dict[str, int],
    ):
        """Save a complete year result to database."""
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            # Save financials
            cur.execute("""
                INSERT INTO financials (year, revenue, ebitda, ebitda_margin, net_income, cash, total_debt, dscr, dividend_paid, capex)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (year) DO UPDATE SET
                    revenue = EXCLUDED.revenue,
                    ebitda = EXCLUDED.ebitda,
                    ebitda_margin = EXCLUDED.ebitda_margin,
                    net_income = EXCLUDED.net_income,
                    cash = EXCLUDED.cash,
                    total_debt = EXCLUDED.total_debt,
                    dscr = EXCLUDED.dscr
            """, (
                year,
                financials.get("revenue"),
                financials.get("ebitda"),
                financials.get("ebitda_margin"),
                financials.get("net_income"),
                financials.get("cash"),
                financials.get("debt"),
                financials.get("dscr"),
                financials.get("dividend_paid", 0),
                financials.get("capex", 0),
            ))

            # Save narrative
            cur.execute("""
                INSERT INTO narrative_log (year, narrative_text)
                VALUES (%s, %s)
                ON CONFLICT (year) DO UPDATE SET narrative_text = EXCLUDED.narrative_text
            """, (year, narrative))

            # Save directives as decision
            cur.execute("""
                INSERT INTO decisions (year, directive_text)
                VALUES (%s, %s)
            """, (year, "; ".join(directives)))

            # Update trust scores
            for entity_name, score in trust_scores.items():
                cur.execute("""
                    INSERT INTO relationships (entity_name, trust_score, last_interaction)
                    VALUES (%s, %s, CURRENT_DATE)
                    ON CONFLICT (entity_name) DO UPDATE SET
                        trust_score = EXCLUDED.trust_score,
                        last_interaction = CURRENT_DATE
                """, (entity_name, score))

            conn.commit()
            print(f"[DB] Year {year} saved")
        except Exception as e:
            conn.rollback()
            print(f"[DB] Save error: {e}")
        finally:
            cur.close()
            conn.close()

    def get_prior_narrative(self, year: int) -> Optional[str]:
        """Get last year's narrative (for DeepSeek context)."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT narrative_text FROM narrative_log WHERE year = %s
            """, (year - 1,))
            row = cur.fetchone()
            return row["narrative_text"] if row else None
        except Exception as e:
            print(f"[DB] Get narrative error: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def get_prior_financials(self, year: int) -> Optional[Dict]:
        """Get prior year's financial snapshot (for DeepSeek context)."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT * FROM financials WHERE year = %s
            """, (year - 1,))
            row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"[DB] Get financials error: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def get_trust_scores(self) -> Dict[str, int]:
        """Get all current trust scores."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT entity_name, trust_score FROM relationships")
            rows = cur.fetchall()
            return {row["entity_name"]: row["trust_score"] for row in rows}
        except Exception as e:
            print(f"[DB] Get trust scores error: {e}")
            return {}
        finally:
            cur.close()
            conn.close()

    def update_trust_score(self, entity_name: str, delta: int) -> int:
        """Update an NPC's trust score."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Get current score
            cur.execute("""
                SELECT trust_score FROM relationships WHERE entity_name = %s
            """, (entity_name,))
            row = cur.fetchone()
            old_score = row["trust_score"] if row else 50

            new_score = max(0, min(100, old_score + delta))

            # Update or insert
            cur.execute("""
                INSERT INTO relationships (entity_name, trust_score, last_interaction)
                VALUES (%s, %s, CURRENT_DATE)
                ON CONFLICT (entity_name) DO UPDATE SET
                    trust_score = EXCLUDED.trust_score,
                    last_interaction = CURRENT_DATE
            """, (entity_name, new_score))

            conn.commit()
            return new_score
        except Exception as e:
            conn.rollback()
            print(f"[DB] Update trust error: {e}")
            return old_score
        finally:
            cur.close()
            conn.close()

