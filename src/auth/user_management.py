"""
User management system for Agent360.
Handles user authentication, authorization, and management.
"""
from typing import Optional, Dict, List
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pydantic import BaseModel
import logging
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model

logger = logging.getLogger(__name__)

class User(Model):
    """User model for database storage."""
    __keyspace__ = 'agent360'
    __table_name__ = 'users'
    
    id = columns.UUID(primary_key=True)
    username = columns.Text(index=True)
    email = columns.Text(index=True)
    hashed_password = columns.Text()
    is_active = columns.Boolean(default=True)
    is_superuser = columns.Boolean(default=False)
    created_at = columns.DateTime()
    last_login = columns.DateTime()
    roles = columns.List(value_type=columns.Text)

class UserCreate(BaseModel):
    """Schema for user creation."""
    username: str
    email: str
    password: str
    roles: List[str] = []

class UserUpdate(BaseModel):
    """Schema for user updates."""
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None

class UserManager:
    """Handles user management operations."""
    
    def __init__(self, secret_key: str):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = secret_key
        
    def create_user(self, user: UserCreate) -> User:
        """Create a new user."""
        try:
            # Check if user exists
            if User.objects.filter(username=user.username).count() > 0:
                raise ValueError("Username already exists")
                
            # Create user
            db_user = User.create(
                username=user.username,
                email=user.email,
                hashed_password=self.pwd_context.hash(user.password),
                roles=user.roles,
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Created user: {user.username}")
            return db_user
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise
            
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        try:
            user = User.objects.filter(username=username).first()
            if not user or not self.pwd_context.verify(password, user.hashed_password):
                return None
                
            # Update last login
            user.last_login = datetime.utcnow()
            user.save()
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return None
            
    def create_access_token(self, user: User, expires_delta: timedelta = None) -> str:
        """Create JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=15)
            
        expire = datetime.utcnow() + expires_delta
        data = {
            "sub": str(user.id),
            "username": user.username,
            "roles": user.roles,
            "exp": expire
        }
        
        return jwt.encode(data, self.secret_key, algorithm="HS256")
        
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.PyJWTError:
            return None
            
    def update_user(self, user_id: str, update: UserUpdate) -> Optional[User]:
        """Update user information."""
        try:
            user = User.objects.filter(id=user_id).first()
            if not user:
                return None
                
            # Update fields
            if update.email:
                user.email = update.email
            if update.password:
                user.hashed_password = self.pwd_context.hash(update.password)
            if update.is_active is not None:
                user.is_active = update.is_active
            if update.roles:
                user.roles = update.roles
                
            user.save()
            return user
            
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            raise
            
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        try:
            user = User.objects.filter(id=user_id).first()
            if not user:
                return False
                
            user.delete()
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user: {str(e)}")
            raise
