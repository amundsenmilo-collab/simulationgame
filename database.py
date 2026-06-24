"""
PostgreSQL models and queries for Asford Materials game state.
Tracks games, financials, events, relationships, and stock positions.
"""
import os
from datetime import datetime
from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")


class GameDatabase:
    """PostgreSQL interface for game state management."""

    def __init__(self):
        self.conn_string = DATABASE_URL

    def _get_conn(self):
        """Get a database connection."""
        return psycopg2.connect(self.conn_string)

    def init_schema(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        cur = conn.cursor()

        # Games table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                player_name VARCHAR(255) NOT NULL,
                current_year INT DEFAULT 0,
                personal_cash FLOAT DEFAULT 800000,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Migrate: add personal_cash column if it doesn't exist (for existing tables)
        conn.commit()  # commit games table creation first
        try:
            cur.execute(
                "ALTER TABLE games ADD COLUMN personal_cash FLOAT DEFAULT 800000;"
            )
            conn.commit()
        except Exception:
            conn.rollback()  # column already exists, ignore

        # Financials table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS financials (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                year INT NOT NULL,
                revenue FLOAT NOT NULL,
                ebitda FLOAT NOT NULL,
                ebitda_margin FLOAT NOT NULL,
                net_income FLOAT NOT NULL,
                cash FLOAT NOT NULL,
                total_debt FLOAT NOT NULL,
                dscr FLOAT NOT NULL,
                capex FLOAT DEFAULT 0,
                dividend_paid FLOAT DEFAULT 0,
                personal_cash FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(game_id, year)
            );
        """)

        # Idempotent migration: add personal_cash to existing financials tables
        cur.execute("""
            ALTER TABLE financials ADD COLUMN IF NOT EXISTS personal_cash FLOAT DEFAULT 0;
        """)

        # Narratives table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS narratives (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                year INT NOT NULL,
                narrative_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(game_id, year)
            );
        """)

        # Events table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                year INT NOT NULL,
                event_type VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                financial_impact FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Relationships table (NPC trust scores)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                npc_name VARCHAR(255) NOT NULL,
                trust_score INT DEFAULT 50,
                last_interaction TEXT,
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(game_id, npc_name)
            );
        """)

        # Directives table (player decisions)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS directives (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                year INT NOT NULL,
                directive_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Stock positions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_positions (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                year INT NOT NULL,
                ticker VARCHAR(10) NOT NULL,
                shares FLOAT NOT NULL,
                avg_cost FLOAT NOT NULL,
                current_price FLOAT NOT NULL,
                dividend_per_share FLOAT DEFAULT 0,
                drip_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(game_id, year, ticker)
            );
        """)

        # Stock prices history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                year INT NOT NULL,
                price FLOAT NOT NULL,
                dividend_per_share FLOAT DEFAULT 0,
                dividend_yield FLOAT DEFAULT 0,
                market_sentiment VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(ticker, year)
            );
        """)

        # Chat messages table (for LLM conversations)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                game_id UUID NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                year INT NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        conn.commit()
        cur.close()
        conn.close()

    # ===== GAMES =====

    def create_game(self, player_name: str) -> str:
        """Create a new game session. Returns game_id."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO games (player_name, current_year, personal_cash) VALUES (%s, %s, %s) RETURNING game_id;",
            (player_name, 0, 800000.0),
        )
        game_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return str(game_id)

    def get_game(self, game_id: str) -> Optional[Dict]:
        """Get game metadata."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM games WHERE game_id = %s;", (game_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return dict(result) if result else None

    def update_game_year(self, game_id: str, year: int):
        """Update current year for a game."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE games SET current_year = %s, updated_at = NOW() WHERE game_id = %s;",
            (year, game_id),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_personal_cash(self, game_id: str) -> float:
        """Get the player's personal cash balance."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT personal_cash FROM games WHERE game_id = %s;", (game_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return float(result[0]) if result and result[0] is not None else 800000.0

    def update_personal_cash(self, game_id: str, personal_cash: float):
        """Update the player's personal cash balance."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE games SET personal_cash = %s, updated_at = NOW() WHERE game_id = %s;",
            (personal_cash, game_id),
        )
        conn.commit()
        cur.close()
        conn.close()

    # ===== FINANCIALS =====

    def save_financials(self, game_id: str, year: int, financials: Dict):
        """Save year-end financials."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO financials 
            (game_id, year, revenue, ebitda, ebitda_margin, net_income, cash, total_debt, dscr, capex, dividend_paid, personal_cash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id, year) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                ebitda = EXCLUDED.ebitda,
                ebitda_margin = EXCLUDED.ebitda_margin,
                net_income = EXCLUDED.net_income,
                cash = EXCLUDED.cash,
                total_debt = EXCLUDED.total_debt,
                dscr = EXCLUDED.dscr,
                capex = EXCLUDED.capex,
                dividend_paid = EXCLUDED.dividend_paid,
                personal_cash = EXCLUDED.personal_cash;
            """,
            (
                game_id,
                year,
                financials.get("revenue", 0),
                financials.get("ebitda", 0),
                financials.get("ebitda_margin", 0),
                financials.get("net_income", 0),
                financials.get("cash", 0),
                financials.get("debt", 0),
                financials.get("dscr", 0),
                financials.get("capex", 0),
                financials.get("dividend_paid", 0),
                financials.get("personal_cash", 0),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_financials(self, game_id: str, year: int) -> Optional[Dict]:
        """Get financials for a specific year."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM financials WHERE game_id = %s AND year = %s;",
            (game_id, year),
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return dict(result) if result else None

    def get_all_financials(self, game_id: str) -> List[Dict]:
        """Get all financials for a game."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM financials WHERE game_id = %s ORDER BY year;",
            (game_id,),
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]

    # ===== NARRATIVES =====

    def save_narrative(self, game_id: str, year: int, narrative: str):
        """Save year narrative."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO narratives (game_id, year, narrative_text)
            VALUES (%s, %s, %s)
            ON CONFLICT (game_id, year) DO UPDATE SET narrative_text = EXCLUDED.narrative_text;
            """,
            (game_id, year, narrative),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_narrative(self, game_id: str, year: int) -> Optional[str]:
        """Get narrative for a specific year."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT narrative_text FROM narratives WHERE game_id = %s AND year = %s;",
            (game_id, year),
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None

    # ===== DIRECTIVES =====

    def save_directive(self, game_id: str, year: int, directive: str):
        """Save player directive."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO directives (game_id, year, directive_text) VALUES (%s, %s, %s);",
            (game_id, year, directive),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_directives(self, game_id: str, year: int) -> List[str]:
        """Get all directives for a year."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT directive_text FROM directives WHERE game_id = %s AND year = %s ORDER BY created_at;",
            (game_id, year),
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in results]

    # ===== RELATIONSHIPS =====

    def update_trust_score(self, game_id: str, npc_name: str, delta: int):
        """Update NPC trust score."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO relationships (game_id, npc_name, trust_score)
            VALUES (%s, %s, 50)
            ON CONFLICT (game_id, npc_name) DO UPDATE SET
                trust_score = GREATEST(0, LEAST(100, relationships.trust_score + %s)),
                updated_at = NOW();
            """,
            (game_id, npc_name, delta),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_trust_scores(self, game_id: str) -> Dict[str, int]:
        """Get all NPC trust scores for a game."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT npc_name, trust_score FROM relationships WHERE game_id = %s;",
            (game_id,),
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return {r["npc_name"]: r["trust_score"] for r in results}

    # ===== EVENTS =====

    def save_event(
        self,
        game_id: str,
        year: int,
        event_type: str,
        description: str,
        financial_impact: float = 0,
    ):
        """Save a game event."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO events (game_id, year, event_type, description, financial_impact)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (game_id, year, event_type, description, financial_impact),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_events(self, game_id: str, year: int) -> List[Dict]:
        """Get all events for a year."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM events WHERE game_id = %s AND year = %s ORDER BY created_at;",
            (game_id, year),
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]

    # ===== STOCK POSITIONS =====

    def save_stock_position(
        self,
        game_id: str,
        year: int,
        ticker: str,
        shares: float,
        avg_cost: float,
        current_price: float,
        dividend_per_share: float = 0,
        drip_enabled: bool = True,
    ):
        """Save stock position."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO stock_positions (game_id, year, ticker, shares, avg_cost, current_price, dividend_per_share, drip_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id, year, ticker) DO UPDATE SET
                shares = EXCLUDED.shares,
                avg_cost = EXCLUDED.avg_cost,
                current_price = EXCLUDED.current_price,
                dividend_per_share = EXCLUDED.dividend_per_share,
                drip_enabled = EXCLUDED.drip_enabled;
            """,
            (game_id, year, ticker, shares, avg_cost, current_price, dividend_per_share, drip_enabled),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_stock_position(self, game_id: str, year: int, ticker: str) -> Optional[Dict]:
        """Get stock position for a year."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM stock_positions WHERE game_id = %s AND year = %s AND ticker = %s;",
            (game_id, year, ticker),
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return dict(result) if result else None

    def get_all_stock_positions(self, game_id: str, year: int) -> List[Dict]:
        """Get all stock positions for a year."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM stock_positions WHERE game_id = %s AND year = %s;",
            (game_id, year),
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]

    # ===== CHAT MESSAGES =====

    def save_chat_message(self, game_id: str, year: int, role: str, content: str):
        """Save chat message."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_messages (game_id, year, role, content) VALUES (%s, %s, %s, %s);",
            (game_id, year, role, content),
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_chat_messages(self, game_id: str, year: int) -> List[Dict]:
        """Get all chat messages for a year."""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT role, content FROM chat_messages WHERE game_id = %s AND year = %s ORDER BY created_at;",
            (game_id, year),
        )
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]

