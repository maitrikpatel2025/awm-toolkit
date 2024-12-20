import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID, uuid4
from fastapi import HTTPException
from passlib.context import CryptContext
from config import DB_PATH
import secrets

class UserService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                username TEXT UNIQUE,
                hashed_password TEXT,
                first_name TEXT,
                last_name TEXT,
                phone_number TEXT,
                bio TEXT,
                profile_picture_url TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                reset_token TEXT,
                reset_token_expires TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def create_user(self, email: str, username: str, password: str) -> Dict:
        """Create a new user and store it in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if email or username already exists
        cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", 
                      (email, username))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email or username already registered")
        
        user_id = str(uuid4())
        hashed_password = self.pwd_context.hash(password)
        now = datetime.utcnow()
        
        cursor.execute(
            """INSERT INTO users 
               (id, email, username, hashed_password, created_at, updated_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, email, username, hashed_password, now, now)
        )
        
        conn.commit()
        conn.close()
        
        return self.get_user_by_id(user_id)

    def get_user_by_id(self, user_id: str) -> Dict:
        """Get user information by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT id, email, username, first_name, last_name, 
                      phone_number, bio, profile_picture_url, is_active, 
                      is_verified, created_at, updated_at 
               FROM users WHERE id = ?""",
            (str(user_id),)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
            
        user_dict = {
            "id": result[0],
            "email": result[1],
            "username": result[2],
            "first_name": result[3],
            "last_name": result[4],
            "phone_number": result[5],
            "bio": result[6],
            "profile_picture_url": result[7],
            "is_active": bool(result[8]),
            "is_verified": bool(result[9]),
            "created_at": result[10],
            "updated_at": result[11]
        }
        
        conn.close()
        return user_dict

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hashed password"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with email and password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, hashed_password FROM users WHERE email = ? AND is_active = 1",
            (email,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        user_id, hashed_password = result
        if not self.verify_password(password, hashed_password):
            return None
            
        return self.get_user_by_id(user_id)

    def update_user(self, user_id: str, user_data: dict) -> Dict:
        """Update user information in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Prepare the query and values
        fields = ", ".join(f"{key} = ?" for key in user_data.keys())
        values = list(user_data.values())
        values.append(user_id)  # Add user_id for the WHERE clause

        query = f"UPDATE users SET {fields} WHERE id = ?"

        # Execute the query
        cursor.execute(query, values)
        conn.commit()
        conn.close()

        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM users WHERE id = ?", (str(user_id),))
        affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return affected > 0

    def create_password_reset_token(self, email: str) -> bool:
        """Create a password reset token for the user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ? AND is_active = 1", (email,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
            
        reset_token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(hours=24)
        
        cursor.execute(
            "UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE email = ?",
            (reset_token, expires, email)
        )
        
        conn.commit()
        conn.close()
        return reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user password using reset token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT id FROM users 
               WHERE reset_token = ? AND reset_token_expires > ? AND is_active = 1""",
            (token, datetime.utcnow())
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
            
        hashed_password = self.pwd_context.hash(new_password)
        cursor.execute(
            """UPDATE users 
               SET hashed_password = ?, reset_token = NULL, reset_token_expires = NULL 
               WHERE reset_token = ?""",
            (hashed_password, token)
        )
        
        conn.commit()
        conn.close()
        return True