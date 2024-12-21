import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID, uuid4
from fastapi import HTTPException
from passlib.context import CryptContext
from config import DB_PATH
import secrets

from models.user_model import Role

import logging
logger = logging.getLogger(__name__)


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
                role TEXT DEFAULT 'user',
                reset_token TEXT,
                reset_token_expires TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_blacklist (
                token TEXT PRIMARY KEY,
                expiry TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def create_user(self, email: str, username: str, password: str, role: Optional[str] = None) -> Dict:
        """Create a new user and store it in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # If no role specified, default to USER
            if role is None:
                role = Role.USER.value
            else:
                # Validate the role
                try:
                    role = Role(role).value
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid role specified")
                
                # Validate that the role is a valid enum value
                if role not in [r.value for r in Role]:
                    raise HTTPException(status_code=400, detail="Invalid role specified")
            
            # Check if email or username already exists
            cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", 
                          (email, username))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email or username already registered")
            
            user_id = str(uuid4())
            hashed_password = self.pwd_context.hash(password)
            now = datetime.utcnow().isoformat()
            
            cursor.execute(
                """INSERT INTO users 
                   (id, email, username, hashed_password, first_name, last_name, 
                    phone_number, bio, profile_picture_url, is_active, is_verified, 
                    role, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 1, 0, ?, ?, ?)""",
                (user_id, email, username, hashed_password, role, now, now,)
            )
            
            conn.commit()
            return self.get_user_by_id(user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            conn.close()

    def get_user_by_id(self, user_id: str) -> Dict:
        """Get user information by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT id, email, username, first_name, last_name, 
                          phone_number, bio, profile_picture_url, is_active, 
                          is_verified, role, created_at, updated_at 
                   FROM users WHERE id = ?""",
                (str(user_id),)
            )
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
                
            # Validate role from database
            role = result[10] or Role.USER.value  # Default to USER if None
            try:
                role = Role(role).value
            except ValueError:
                logger.warning(f"Invalid role in database for user {user_id}: {role}")
                role = Role.USER.value
            
            user_dict = {
                "id": result[0],
                "email": result[1],
                "username": result[2],
                "first_name": result[3],
                "last_name": result[4],
                "phone_number": result[5],
                "bio": result[6],
                "profile_picture_url": result[7],
                "is_active": bool(result[8]) if result[8] is not None else True,
                "is_verified": bool(result[9]) if result[9] is not None else False,
                "role": role,
                "created_at": result[11],
                "updated_at": result[12]
            }
            
            return user_dict
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            conn.close()

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

        try:
            # Validate role if present
            if 'role' in user_data:
                try:
                    user_data['role'] = Role(user_data['role']).value
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid role specified")

            # Add updated_at timestamp
            user_data['updated_at'] = datetime.utcnow().isoformat()

            # Prepare the query and values
            fields = ", ".join(f"{key} = ?" for key in user_data.keys())
            values = list(user_data.values())
            values.append(user_id)  # Add user_id for the WHERE clause

            query = f"UPDATE users SET {fields} WHERE id = ?"

            # Execute the query
            cursor.execute(query, values)
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            conn.commit()
            return self.get_user_by_id(user_id)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            conn.close()

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

    def get_all_users(self) -> List[Dict]:
        """Get all users from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT id, email, username, first_name, last_name, 
                      phone_number, bio, profile_picture_url, is_active, 
                      is_verified, role, created_at, updated_at 
               FROM users"""
        )
        results = cursor.fetchall()
        
        users = []
        for result in results:
            users.append({
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
                "role": result[10] or "user",
                "created_at": result[11],
                "updated_at": result[12]
            })
        
        conn.close()
        return users

    def update_user_role(self, user_id: str, new_role: str) -> Dict:
        """Update user's role"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Validate the new role
            try:
                new_role = Role(new_role).value
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid role specified")
            
            # Update the user's role
            cursor.execute(
                """UPDATE users 
                   SET role = ?, 
                       updated_at = ? 
                   WHERE id = ?""",
                (new_role, datetime.utcnow().isoformat(), user_id)
            )
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            conn.commit()
            return self.get_user_by_id(user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user role: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            conn.close()

    def get_user_role(self, user_id: str) -> str:
        """Get user's role"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
            
            return result[0] or Role.USER.value  # Default to USER if None
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user role: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user information by email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT id, email, username, first_name, last_name, 
                          phone_number, bio, profile_picture_url, is_active, 
                          is_verified, role, created_at, updated_at 
                   FROM users WHERE email = ?""",
                (email,)
            )
            result = cursor.fetchone()
            
            if not result:
                return None
            
            user_dict = {
                "id": result[0],
                "email": result[1],
                "username": result[2],
                "first_name": result[3],
                "last_name": result[4],
                "phone_number": result[5],
                "bio": result[6],
                "profile_picture_url": result[7],
                "is_active": bool(result[8]) if result[8] is not None else True,
                "is_verified": bool(result[9]) if result[9] is not None else False,
                "role": result[10],
                "created_at": result[11],
                "updated_at": result[12]
            }
            
            return user_dict
            
        except Exception as e:
            logger.error(f"Error retrieving user by email: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            conn.close()

    def blacklist_token(self, token: str, expiry: datetime) -> bool:
        """Add a token to the blacklist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT INTO token_blacklist (token, expiry, created_at) VALUES (?, ?, ?)",
                (token, expiry.isoformat(), now)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error blacklisting token: {str(e)}")
            return False
        finally:
            conn.close()

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Clean up expired tokens
            cursor.execute(
                "DELETE FROM token_blacklist WHERE expiry < ?",
                (datetime.utcnow().isoformat(),)
            )
            conn.commit()
            
            # Check if token is blacklisted
            cursor.execute("SELECT 1 FROM token_blacklist WHERE token = ?", (token,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
