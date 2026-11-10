"""
SQLite Database manager for session history, attack statistics, wall upgrades,
calibration data, and failure diagnostics.
"""

from __future__ import annotations
import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


class DatabaseManager:
    """Manages SQLite storage for sessions, attacks, and diagnostics."""

    def __init__(self, db_path: str = "data/farming_history.db"):
        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, db_path)
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        """Initializes relational tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                total_attacks INTEGER DEFAULT 0,
                total_skips INTEGER DEFAULT 0,
                gold_looted INTEGER DEFAULT 0,
                elixir_looted INTEGER DEFAULT 0,
                dark_elixir_looted INTEGER DEFAULT 0,
                walls_upgraded INTEGER DEFAULT 0,
                status TEXT DEFAULT 'RUNNING'
            )
            """)

            # Attacks table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attacks (
                attack_id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                outcome TEXT,
                damage_percent REAL DEFAULT 0.0,
                stars INTEGER DEFAULT 0,
                target_gold INTEGER DEFAULT 0,
                target_elixir INTEGER DEFAULT 0,
                target_dark_elixir INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                exit_reason TEXT,
                raw_data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
            """)

            # Wall upgrades table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS wall_upgrades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                wall_level INTEGER,
                batch_count INTEGER DEFAULT 1,
                resource_type TEXT,
                cost INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
            """)

            # Calibration cache table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                screen_width INTEGER,
                screen_height INTEGER,
                viewport_x INTEGER,
                viewport_y INTEGER,
                viewport_width INTEGER,
                viewport_height INTEGER,
                scale_x REAL,
                scale_y REAL,
                confidence REAL
            )
            """)

            # Failure diagnostics table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT NOT NULL,
                state TEXT,
                intended_action TEXT,
                error_message TEXT,
                screenshot_path TEXT,
                confidence_data TEXT
            )
            """)

            # Player storage capacity limits (dynamic per-ID capacity)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_storage_limits (
                player_name TEXT PRIMARY KEY,
                max_gold INTEGER DEFAULT 0,
                max_elixir INTEGER DEFAULT 0,
                max_dark_elixir INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """)
            conn.commit()

    # Session methods
    def start_session(self, session_id: str, mode: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, mode, start_time, status) VALUES (?, ?, ?, 'RUNNING')",
                (session_id, mode, datetime.now().isoformat())
            )
            conn.commit()

    def end_session(self, session_id: str, status: str = "COMPLETED") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET end_time = ?, status = ? WHERE session_id = ?",
                (datetime.now().isoformat(), status, session_id)
            )
            conn.commit()

    def increment_session_skips(self, session_id: str, count: int = 1) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET total_skips = total_skips + ? WHERE session_id = ?",
                (count, session_id)
            )
            conn.commit()

    def record_attack(self, attack_data: Dict[str, Any]) -> None:
        session_id = attack_data.get("session_id")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attacks (
                    attack_id, session_id, timestamp, outcome, damage_percent,
                    stars, target_gold, target_elixir, target_dark_elixir,
                    duration_seconds, exit_reason, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attack_data.get("attack_id", str(datetime.now().timestamp())),
                session_id,
                attack_data.get("timestamp", datetime.now().isoformat()),
                attack_data.get("outcome", "UNKNOWN"),
                attack_data.get("damage_percent", 0.0),
                attack_data.get("stars", 0),
                attack_data.get("target_gold", 0),
                attack_data.get("target_elixir", 0),
                attack_data.get("target_dark_elixir", 0),
                attack_data.get("duration_seconds", 0.0),
                attack_data.get("exit_reason", ""),
                json.dumps(attack_data.get("raw_data", {}))
            ))

            if session_id:
                cursor.execute("""
                    UPDATE sessions SET
                        total_attacks = total_attacks + 1,
                        gold_looted = gold_looted + ?,
                        elixir_looted = elixir_looted + ?,
                        dark_elixir_looted = dark_elixir_looted + ?
                    WHERE session_id = ?
                """, (
                    attack_data.get("target_gold", 0),
                    attack_data.get("target_elixir", 0),
                    attack_data.get("target_dark_elixir", 0),
                    session_id
                ))
            conn.commit()

    def record_wall_upgrade(self, session_id: Optional[str], wall_level: Optional[int], batch_count: int, resource_type: str, cost: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wall_upgrades (session_id, timestamp, wall_level, batch_count, resource_type, cost)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, datetime.now().isoformat(), wall_level, batch_count, resource_type, cost))

            if session_id:
                cursor.execute(
                    "UPDATE sessions SET walls_upgraded = walls_upgraded + ? WHERE session_id = ?",
                    (batch_count, session_id)
                )
            conn.commit()

    def record_failure(self, session_id: Optional[str], state: str, intended_action: str, error_message: str, screenshot_path: Optional[str] = None, confidence_data: Optional[Dict] = None) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO failure_logs (session_id, timestamp, state, intended_action, error_message, screenshot_path, confidence_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                datetime.now().isoformat(),
                state,
                intended_action,
                error_message,
                screenshot_path or "",
                json.dumps(confidence_data or {})
            ))
            conn.commit()

    def save_calibration(self, screen_w: int, screen_h: int, vx: int, vy: int, vw: int, vh: int, sx: float, sy: float, conf: float) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calibration (timestamp, screen_width, screen_height, viewport_x, viewport_y, viewport_width, viewport_height, scale_x, scale_y, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), screen_w, screen_h, vx, vy, vw, vh, sx, sy, conf))
            conn.commit()

    def get_latest_calibration(self) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calibration ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_player_storage_limits(self, player_name: str) -> Optional[Dict[str, int]]:
        """Retrieves cached maximum storage capacities for a specific player ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT max_gold, max_elixir, max_dark_elixir FROM player_storage_limits WHERE player_name = ?",
                (player_name.strip(),)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "max_gold": row["max_gold"],
                    "max_elixir": row["max_elixir"],
                    "max_dark_elixir": row["max_dark_elixir"],
                }
            return None

    def save_player_storage_limits(self, player_name: str, max_gold: int, max_elixir: int, max_dark_elixir: int = 0) -> None:
        """Saves or updates detected maximum storage capacity for a specific player ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO player_storage_limits (player_name, max_gold, max_elixir, max_dark_elixir, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(player_name) DO UPDATE SET
                    max_gold = excluded.max_gold,
                    max_elixir = excluded.max_elixir,
                    max_dark_elixir = excluded.max_dark_elixir,
                    updated_at = excluded.updated_at
            """, (player_name.strip(), max_gold, max_elixir, max_dark_elixir, datetime.now().isoformat()))
            conn.commit()

    def get_recent_attacks(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attacks ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]


# Backward compatibility alias
Database = DatabaseManager

