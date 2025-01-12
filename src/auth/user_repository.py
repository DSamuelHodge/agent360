"""
User repository for Agent360.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from ..database.schema import User
from ..database.connection import get_connection, DatabaseConnection

logger = logging.getLogger(__name__)

class UserRepository:
    """Repository for user management."""
    
    def __init__(self, db: Optional[DatabaseConnection] = None):
        """Initialize repository.
        
        Args:
            db: Optional database connection
        """
        self.db = db or get_connection()
        
    async def get_user_by_username(self, username: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get user by username.
        
        Args:
            username: Username to look up
            tenant_id: Tenant ID to filter by
            
        Returns:
            User data if found, None otherwise
        """
        query = "SELECT * FROM users WHERE username = %s AND tenant_id = %s ALLOW FILTERING"
        result = self.db.execute(query, {'username': username, 'tenant_id': tenant_id})
        return result[0] if result else None
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            User data if found, None otherwise
        """
        query = "SELECT * FROM users WHERE id = %s"
        result = self.db.execute(query, {'id': user_id})
        return result[0] if result else None
    
    async def create_user(self, username: str, hashed_password: str, email: str,
                         tenant_id: str, roles: List[str]) -> Dict[str, Any]:
        """Create a new user.
        
        Args:
            username: Username
            hashed_password: Hashed password
            email: Email address
            tenant_id: Tenant ID
            roles: List of roles
            
        Returns:
            Created user data
        """
        user_id = uuid4()
        now = datetime.utcnow()
        
        user = {
            'id': user_id,
            'username': username,
            'hashed_password': hashed_password,
            'email': email,
            'tenant_id': tenant_id,
            'roles': roles,
            'created_at': now,
            'updated_at': now,
            'failed_attempts': 0,
            'locked_until': None
        }
        
        query = """
            INSERT INTO users (id, username, hashed_password, email, tenant_id, roles,
                             created_at, updated_at, failed_attempts, locked_until)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(query, user)
        
        return user
    
    async def update_user(self, user_id: UUID, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user data.
        
        Args:
            user_id: User ID to update
            updates: Fields to update
            
        Returns:
            Updated user data if successful, None if user not found
        """
        updates['updated_at'] = datetime.utcnow()
        
        set_clause = ', '.join(f"{k} = %s" for k in updates.keys())
        query = f"UPDATE users SET {set_clause} WHERE id = %s"
        
        params = list(updates.values()) + [user_id]
        self.db.execute(query, params)
        
        return await self.get_user_by_id(user_id)
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if user was deleted, False if not found
        """
        query = "DELETE FROM users WHERE id = %s"
        self.db.execute(query, {'id': user_id})
        return True
    
    async def increment_failed_attempts(self, username: str, tenant_id: str) -> Optional[int]:
        """Increment failed login attempts for a user.
        
        Args:
            username: Username to update
            tenant_id: Tenant ID to filter by
            
        Returns:
            New number of failed attempts if user exists, None otherwise
        """
        user = await self.get_user_by_username(username, tenant_id)
        if not user:
            return None
            
        new_attempts = user['failed_attempts'] + 1
        locked_until = None
        
        # Lock account after 5 failed attempts
        if new_attempts >= 5:
            locked_until = datetime.utcnow() + timedelta(minutes=30)
            
        query = """
            UPDATE users 
            SET failed_attempts = %s, locked_until = %s, updated_at = %s
            WHERE id = %s
        """
        self.db.execute(query, {
            'failed_attempts': new_attempts,
            'locked_until': locked_until,
            'updated_at': datetime.utcnow(),
            'id': user['id']
        })
        
        return new_attempts
    
    async def reset_failed_attempts(self, username: str, tenant_id: str) -> bool:
        """Reset failed login attempts for a user.
        
        Args:
            username: Username to update
            tenant_id: Tenant ID to filter by
            
        Returns:
            True if user was updated, False if not found
        """
        user = await self.get_user_by_username(username, tenant_id)
        if not user:
            return False
            
        query = """
            UPDATE users 
            SET failed_attempts = 0, locked_until = null, updated_at = %s
            WHERE id = %s
        """
        self.db.execute(query, {
            'updated_at': datetime.utcnow(),
            'id': user['id']
        })
        
        return True
