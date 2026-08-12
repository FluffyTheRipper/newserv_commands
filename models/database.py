import aiosqlite
import os
from datetime import datetime

DB_PATH = "pso_bridge.db"

async def init_db():
    """Initializes the SQLite database and creates the required schemas if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Table for periodic server snapshots
        await db.execute("""
            CREATE TABLE IF NOT EXISTS server_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                uptime_usecs INTEGER,
                client_count INTEGER,
                game_count INTEGER
            )
        """)

        # 2. Table for player login/logout activity sessions
        await db.execute("""
            CREATE TABLE IF NOT EXISTS player_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                player_name TEXT,
                login_time DATETIME,
                logout_time DATETIME NULL
            )
        """)

        # 3. Table for historical rare drop tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rare_drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                player_name TEXT,
                game_name TEXT,
                raw_item_name TEXT,
                cleaned_item_name TEXT
            )
        """)
        await db.commit()

# --- DATABASE WRITE OPERATIONS ---

async def log_server_metrics(uptime_usecs: int, client_count: int, game_count: int):
    """Saves a point-in-time snapshot of the server status."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO server_history (uptime_usecs, client_count, game_count) VALUES (?, ?, ?)",
            (uptime_usecs, client_count, game_count)
        )
        await db.commit()

async def log_player_login(player_id: int, player_name: str):
    """Records a player joining the server."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO player_sessions (player_id, player_name, login_time) VALUES (?, ?, ?)",
            (player_id, player_name, datetime.utcnow().isoformat())
        )
        await db.commit()

async def log_player_logout(player_id: int):
    """Finds the player's active open session and closes it with a logout timestamp."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Update the most recent open session for this player ID
        await db.execute("""
            UPDATE player_sessions 
            SET logout_time = ? 
            WHERE player_id = ? AND logout_time IS NULL
            ORDER BY login_time DESC LIMIT 1
        """, (datetime.utcnow().isoformat(), player_id))
        await db.commit()

async def log_rare_drop(player_name: str, game_name: str, raw_item_name: str, cleaned_item_name: str):
    """Commits a rare drop event permanently to the ledger."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO rare_drops (player_name, game_name, raw_item_name, cleaned_item_name) 
            VALUES (?, ?, ?, ?)
        """, (player_name, game_name, raw_item_name, cleaned_item_name))
        await db.commit()