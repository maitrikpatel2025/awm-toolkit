import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import HTTPException
from config import DB_PATH
import uuid

class KeyManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS api_keys (key_id TEXT PRIMARY KEY, key TEXT, key_name TEXT, user_id TEXT, created_at DATETIME, expires_at DATETIME, description TEXT, is_active INTEGER)")
        conn.commit()
        conn.close()

    def verify_user_key(self, key_id: str, user_id: str) -> bool:
        """Verify if the key belongs to the user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT 1 FROM api_keys 
               WHERE key_id = ? AND user_id = ?""",
            (key_id, user_id)
        )
        result = cursor.fetchone() is not None
        conn.close()
        
        return result

    def generate_key(self, user_id: str, key_name: str, 
                    description: Optional[str] = None,
                    expires_in_days: Optional[int] = 365) -> Dict:
        """Generate a new API key and store it in the database"""
        key_id = str(uuid.uuid4())
        api_key = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO api_keys 
               (key_id, key, key_name, user_id, created_at, expires_at, description) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (key_id, api_key, key_name, user_id, datetime.utcnow(), expires_at, description)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "key_id": key_id,
            "api_key": api_key,
            "key_name": key_name
        }

    def get_key_info(self, key_id: str, user_id: str) -> Dict:
        """Get detailed information about an API key"""
        # First verify the key belongs to this user
        if not self.verify_user_key(key_id, user_id):
            raise HTTPException(
                status_code=404,
                detail=f"No API key found with ID: {key_id}"
            )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT key_id, key, key_name, created_at, expires_at, description, 
                      is_active
               FROM api_keys WHERE key_id = ?""",
            (key_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="API key not found")
            
        key_id, key, key_name, created_at, expires_at, description, is_active = result
        
        return {
            "key_id": key_id,
            "key": key,
            "key_name": key_name,
            "created_at": created_at,
            "expires_at": expires_at,
            "description": description,
            "is_active": bool(is_active)
        }

    def get_user_keys(self, user_id: str) -> List[Dict]:
        """Get all API keys for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT key_id, key, key_name, created_at, expires_at, description, 
                      is_active 
               FROM api_keys WHERE user_id = ?""",
            (user_id,)
        )
        results = cursor.fetchall()
        
        keys = []
        for result in results:
            key_id, key, key_name, created_at, expires_at, description, is_active = result
            keys.append({
                "key_id": key_id,
                "key": key,
                "key_name": key_name,
                "created_at": created_at,
                "expires_at": expires_at,
                "description": description,
                "is_active": bool(is_active)
            })
        
        conn.close()
        return keys

    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """Revoke an API key by setting is_active to False"""
        # First verify the key belongs to this user
        if not self.verify_user_key(key_id, user_id):
            raise HTTPException(
                status_code=404,
                detail=f"No API key found with ID: {key_id}"
            )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key_id = ?",
            (key_id,)
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

    def get_key_user_id(self, api_key: str) -> Optional[str]:
        """Get user_id associated with an API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM api_keys WHERE key = ?", (api_key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
