import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "movyra.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Promotions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    image_url TEXT,
                    rating REAL,
                    website_link TEXT,
                    trailer_link TEXT,
                    genres TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sent TIMESTAMP,
                    times_sent INTEGER DEFAULT 0
                )
            ''')
            
            # Groups table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT UNIQUE NOT NULL,
                    group_name TEXT NOT NULL,
                    group_link TEXT,
                    added_by TEXT,
                    active BOOLEAN DEFAULT 1,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    invite_template INTEGER DEFAULT 1,
                    last_invite_sent TIMESTAMP
                )
            ''')
            
            # Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promotion_id INTEGER,
                    group_id TEXT,
                    message_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    error_message TEXT
                )
            ''')
            
            # Bot settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT OR IGNORE INTO bot_settings (key, value)
                VALUES ('auto_posting_enabled', 'true'), ('post_interval_minutes', '30')
            ''')
            
            logger.info("Database initialized successfully")
    
    def add_promotion(self, title, description, image_url=None, rating=None, website_link=None, trailer_link=None, genres=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO promotions (title, description, image_url, rating, website_link, trailer_link, genres)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, image_url, rating, website_link, trailer_link, genres))
            return cursor.lastrowid
    
    def get_promotion(self, promo_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM promotions WHERE id = ?', (promo_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_promotions(self, active_only=True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT * FROM promotions WHERE active = 1 ORDER BY id')
            else:
                cursor.execute('SELECT * FROM promotions ORDER BY id')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_promotion(self, promo_id, **kwargs):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['title', 'description', 'image_url', 'rating', 'website_link', 'trailer_link', 'genres', 'active']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            if not fields:
                return False
            values.append(promo_id)
            cursor.execute(f"UPDATE promotions SET {', '.join(fields)} WHERE id = ?", values)
            return cursor.rowcount > 0
    
    def delete_promotion(self, promo_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM promotions WHERE id = ?', (promo_id,))
            return cursor.rowcount > 0
    
    def update_promotion_sent(self, promo_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE promotions SET last_sent = CURRENT_TIMESTAMP, times_sent = times_sent + 1
                WHERE id = ?
            ''', (promo_id,))
    
    def add_group(self, group_id, group_name, group_link=None, added_by=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO groups (group_id, group_name, group_link, added_by)
                    VALUES (?, ?, ?, ?)
                ''', (group_id, group_name, group_link, added_by))
                return True
            except sqlite3.IntegrityError:
                return False
    
    def remove_group(self, group_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM groups WHERE group_id = ?', (group_id,))
            return cursor.rowcount > 0
    
    def get_all_groups(self, active_only=True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT * FROM groups WHERE active = 1 ORDER BY group_name')
            else:
                cursor.execute('SELECT * FROM groups ORDER BY group_name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_next_promotion(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM promotions 
                WHERE active = 1 
                ORDER BY last_sent NULLS FIRST, times_sent, id
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def log_sent_message(self, promotion_id, group_id, message_id, status, error=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs (promotion_id, group_id, message_id, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (promotion_id, group_id, message_id, status, error))
    
    def was_sent_recently(self, promotion_id, group_id, hours=24):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM logs 
                WHERE promotion_id = ? AND group_id = ? 
                AND sent_at > datetime('now', ?)
                AND status = 'success'
                LIMIT 1
            ''', (promotion_id, group_id, f'-{hours} hours'))
            return cursor.fetchone() is not None
    
    def get_statistics(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM logs WHERE status = "success"')
            total_sent = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM promotions WHERE active = 1')
            promo_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM groups WHERE active = 1')
            group_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT value FROM bot_settings WHERE key = "post_interval_minutes"')
            interval_row = cursor.fetchone()
            interval = int(interval_row[0]) if interval_row else 30
            
            cursor.execute('SELECT value FROM bot_settings WHERE key = "auto_posting_enabled"')
            status_row = cursor.fetchone()
            auto_posting = status_row[0] == 'true' if status_row else True
            
            success_rate = 100.0
            
            return {
                'total_sent': total_sent,
                'success_rate': success_rate,
                'promo_count': promo_count,
                'group_count': group_count,
                'interval': interval,
                'auto_posting': auto_posting
            }
    
    def get_setting(self, key):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM bot_settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_setting(self, key, value):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))

# Create a single instance to export
db = Database()
