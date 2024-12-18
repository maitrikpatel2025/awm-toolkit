import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import HTTPException

class KeyManager:
    def __init__(self, db_path: str = "keys.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # API Keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                rate_limit INTEGER DEFAULT 100
            )
        ''')
        
        # Usage tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT,
                endpoint TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (api_key) REFERENCES api_keys (key)
            )
        ''')
        
        conn.commit()
        conn.close()

    def generate_key(self, description: Optional[str] = None, 
                    expires_in_days: Optional[int] = 365,
                    rate_limit: int = 100) -> str:
        """Generate a new API key and store it in the database"""
        api_key = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO api_keys 
               (key, created_at, expires_at, description, rate_limit) 
               VALUES (?, ?, ?, ?, ?)""",
            (api_key, datetime.utcnow(), expires_at, description, rate_limit)
        )
        
        conn.commit()
        conn.close()
        return api_key

    def revoke_key(self, api_key: str) -> bool:
        """Revoke an API key by setting is_active to False"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key = ?",
            (api_key,)
        )
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def is_key_valid(self, api_key: str) -> bool:
        """Check if an API key exists, is active, and not expired"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT is_active, expires_at 
               FROM api_keys 
               WHERE key = ?""",
            (api_key,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            return False
            
        is_active, expires_at = result
        if not is_active:
            return False
            
        if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
            return False
            
        return True

    def log_usage(self, api_key: str, endpoint: str):
        """Log API key usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO usage_logs (api_key, endpoint, timestamp) VALUES (?, ?, ?)",
            (api_key, endpoint, datetime.utcnow())
        )
        
        conn.commit()
        conn.close()

    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key has exceeded its rate limit (requests per day)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get rate limit for the key
        cursor.execute(
            "SELECT rate_limit FROM api_keys WHERE key = ?",
            (api_key,)
        )
        result = cursor.fetchone()
        if not result:
            return False
            
        rate_limit = result[0]
        
        # Count today's requests
        today = datetime.utcnow().date()
        cursor.execute(
            """SELECT COUNT(*) FROM usage_logs 
               WHERE api_key = ? 
               AND date(timestamp) = date(?)""",
            (api_key, today)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count < rate_limit

    def get_key_info(self, api_key: str) -> Dict:
        """Get detailed information about an API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT created_at, expires_at, description, is_active, rate_limit 
               FROM api_keys WHERE key = ?""",
            (api_key,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="API key not found")
            
        created_at, expires_at, description, is_active, rate_limit = result
        
        # Get usage statistics
        cursor.execute(
            """SELECT COUNT(*) FROM usage_logs 
               WHERE api_key = ? 
               AND date(timestamp) = date(?)""",
            (api_key, datetime.utcnow().date())
        )
        today_usage = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "created_at": created_at,
            "expires_at": expires_at,
            "description": description,
            "is_active": bool(is_active),
            "rate_limit": rate_limit,
            "today_usage": today_usage
        } 