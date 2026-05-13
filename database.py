"""
database.py - MovYra Bot Database Layer
========================================
Handles all SQLite operations:
  - promotions  (movie promos to send)
  - groups      (Telegram groups to post in)
  - logs        (send history for dedup & analytics)
  - settings    (runtime config like interval, pause state)
"""

import sqlite3
import logging
import shutil
import os
from datetime import datetime, timedelta
from typing import Optional

import config

logger = logging.getLogger(__name__)


# ─── CONNECTION HELPER ────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory so columns are accessible by name."""
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row   # access columns as dict keys
    conn.execute("PRAGMA journal_mode=WAL")  # write-ahead logging = better concurrency
    return conn


# ─── SCHEMA CREATION ──────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist yet. Safe to call on every startup."""
    conn = get_connection()
    c = conn.cursor()

    # ── promotions ────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,           -- Movie name
            description TEXT    NOT NULL,           -- Short promo text (2-3 lines)
            image_url   TEXT,                       -- Poster/banner URL (optional)
            rating      TEXT    DEFAULT '8.0',      -- e.g. "8.5"
            website_link TEXT   NOT NULL,           -- movyra.com/movie-name
            trailer_link TEXT,                      -- YouTube URL
            genres      TEXT,                       -- "#Action #Thriller"
            active      INTEGER DEFAULT 1,          -- 1=active, 0=disabled
            created_at  TEXT    DEFAULT (datetime('now')),
            last_sent   TEXT                        -- ISO datetime of last send
        )
    """)

    # ── groups ────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id    TEXT    NOT NULL UNIQUE,    -- Telegram chat ID (e.g. -1001234)
            group_name  TEXT    NOT NULL,
            group_link  TEXT,                      -- https://t.me/groupname
            added_by    TEXT,                      -- admin username
            active      INTEGER DEFAULT 1,
            joined_at   TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── logs ──────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            promotion_id INTEGER NOT NULL,
            group_id     TEXT    NOT NULL,
            sent_at      TEXT    DEFAULT (datetime('now')),
            status       TEXT    DEFAULT 'success'  -- 'success' | 'failed'
        )
    """)

    # ── settings (key-value store for runtime state) ──────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Insert default settings if not already present
    defaults = {
        "interval_minutes": str(config.DEFAULT_INTERVAL_MINUTES),
        "paused":           "0",     # "1" = paused
        "promo_index":      "0",     # which promo to send next (round-robin)
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", config.DB_PATH)


# ─── SETTINGS HELPERS ─────────────────────────────────────────────────────────

def get_setting(key: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


# ─── PROMOTIONS ───────────────────────────────────────────────────────────────

def add_promotion(
    title: str,
    description: str,
    website_link: str,
    image_url: str = "",
    rating: str = "8.0",
    trailer_link: str = "",
    genres: str = "",
) -> int:
    """Insert a new promotion. Returns the new row id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO promotions (title, description, image_url, rating,
                                website_link, trailer_link, genres)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, description, image_url, rating, website_link, trailer_link, genres))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    logger.info("Promotion added: id=%d title=%s", new_id, title)
    return new_id


def get_promotion(promo_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM promotions WHERE id=?", (promo_id,)).fetchone()
    conn.close()
    return row


def get_active_promotions() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM promotions WHERE active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def get_all_promotions() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM promotions ORDER BY id").fetchall()
    conn.close()
    return rows


def update_promotion(promo_id: int, **fields) -> bool:
    """Update any fields of a promotion by keyword arguments."""
    allowed = {"title", "description", "image_url", "rating",
               "website_link", "trailer_link", "genres", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [promo_id]
    conn = get_connection()
    conn.execute(f"UPDATE promotions SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()
    return True


def delete_promotion(promo_id: int) -> bool:
    conn = get_connection()
    result = conn.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
    conn.commit()
    conn.close()
    return result.rowcount > 0


def mark_promotion_sent(promo_id: int) -> None:
    """Update last_sent timestamp for the promotion."""
    conn = get_connection()
    conn.execute(
        "UPDATE promotions SET last_sent=datetime('now') WHERE id=?", (promo_id,)
    )
    conn.commit()
    conn.close()


# ─── GROUPS ───────────────────────────────────────────────────────────────────

def add_group(group_id: str, group_name: str,
              group_link: str = "", added_by: str = "") -> bool:
    """Add a group. Returns False if it already exists."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO groups (group_id, group_name, group_link, added_by)
            VALUES (?, ?, ?, ?)
        """, (str(group_id), group_name, group_link, added_by))
        conn.commit()
        logger.info("Group added: %s (%s)", group_name, group_id)
        return True
    except sqlite3.IntegrityError:
        return False          # already exists (UNIQUE constraint)
    finally:
        conn.close()


def remove_group(group_id: str) -> bool:
    conn = get_connection()
    result = conn.execute(
        "UPDATE groups SET active=0 WHERE group_id=?", (str(group_id),)
    )
    conn.commit()
    conn.close()
    return result.rowcount > 0


def get_active_groups() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM groups WHERE active=1 ORDER BY joined_at"
    ).fetchall()
    conn.close()
    return rows


def get_all_groups() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM groups ORDER BY joined_at").fetchall()
    conn.close()
    return rows


def group_exists(group_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM groups WHERE group_id=? AND active=1", (str(group_id),)
    ).fetchone()
    conn.close()
    return row is not None


# ─── LOGS ─────────────────────────────────────────────────────────────────────

def log_send(promotion_id: int, group_id: str, status: str = "success") -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO logs (promotion_id, group_id, status)
        VALUES (?, ?, ?)
    """, (promotion_id, str(group_id), status))
    conn.commit()
    conn.close()


def was_recently_sent(promotion_id: int, group_id: str) -> bool:
    """Return True if this promo was already sent to this group within DUPLICATE_WINDOW_HOURS."""
    cutoff = datetime.utcnow() - timedelta(hours=config.DUPLICATE_WINDOW_HOURS)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    row = conn.execute("""
        SELECT 1 FROM logs
        WHERE promotion_id=? AND group_id=? AND status='success'
          AND sent_at >= ?
    """, (promotion_id, str(group_id), cutoff_str)).fetchone()
    conn.close()
    return row is not None


def get_send_stats() -> dict:
    """Return aggregate stats for /status command."""
    conn = get_connection()
    total_sent  = conn.execute("SELECT COUNT(*) FROM logs WHERE status='success'").fetchone()[0]
    total_fail  = conn.execute("SELECT COUNT(*) FROM logs WHERE status='failed'").fetchone()[0]
    active_promos = conn.execute("SELECT COUNT(*) FROM promotions WHERE active=1").fetchone()[0]
    active_groups = conn.execute("SELECT COUNT(*) FROM groups WHERE active=1").fetchone()[0]
    conn.close()
    return {
        "total_sent":    total_sent,
        "total_failed":  total_fail,
        "active_promos": active_promos,
        "active_groups": active_groups,
    }


# ─── BACKUP ───────────────────────────────────────────────────────────────────

def backup_database() -> str:
    """Copy the DB file to the backups/ folder with a timestamp. Returns backup path."""
    os.makedirs(config.BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(config.BACKUP_DIR, f"movyra_{ts}.db")
    shutil.copy2(config.DB_PATH, dest)
    logger.info("Database backed up to %s", dest)
    return dest
