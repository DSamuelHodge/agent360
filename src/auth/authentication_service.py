"""
Authentication service for Agent360.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from pydantic import BaseModel

from src.auth.user_repository import UserRepository
from src.config import get_settings

logger = logging.getLogger(__name__)

class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: list[str] = []
    
class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    tenant_id: str = "default"
    roles: list[str] = []

class UserInDB(User):
    hashed_password: str

class AuthenticationService:
    """Service for handling authentication related operations."""
    
    def __init__(self, user_repository: Optional[UserRepository] = None):
        """Initialize the authentication service.
        
        Args:
            user_repository: Optional user repository instance
        """
        self.user_repository = user_repository or UserRepository()
        self.settings = get_settings()
        
    async def initialize(self):
        """Initialize the authentication service."""
        await self._create_test_user()
    
    async def authenticate(self, username: str, password: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """Authenticate a user and return a JWT token.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            tenant_id: Tenant ID to authenticate against
            
        Returns:
            Dict containing token and user info if successful, None otherwise
        """
        try:
            user = await self.user_repository.get_user_by_username(username, tenant_id)
            if not user:
                logger.warning(f"User not found: {username}")
                return None
                
            if not self._verify_password(password, user['hashed_password']):
                logger.warning(f"Invalid password for user: {username}")
                await self.user_repository.increment_failed_attempts(username, tenant_id)
                return None
                
            # Reset failed attempts on successful login
            await self.user_repository.reset_failed_attempts(username, tenant_id)
            
            token = self._create_token(user)
            return {
                'access_token': token,
                'token_type': 'bearer',
                'user': {
                    'id': str(user['id']),
                    'username': user['username'],
                    'email': user['email'],
                    'roles': user['roles']
                }
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
            
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password to compare against
            
        Returns:
            True if password matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
            
    def _create_token(self, user: Dict[str, Any]) -> str:
        """Create a JWT token for a user.
        
        Args:
            user: User data to encode in token
            
        Returns:
            JWT token string
        """
        expires = datetime.utcnow() + timedelta(minutes=60)
        
        return jwt.encode(
            {
                'sub': str(user['id']),
                'username': user['username'],
                'roles': user['roles'],
                'exp': expires
            },
            self.settings.jwt_secret_key,
            algorithm='HS256'
        )
        
    async def _create_test_user(self):
        """Create a test user if it doesn't exist."""
        try:
            test_user = await self.user_repository.get_user_by_username('test_user', 'default')
            if test_user:
                return
                
            password_hash = bcrypt.hashpw(
                'test_password'.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            await self.user_repository.create_user(
                username='test_user',
                hashed_password=password_hash,
                email='test@example.com',
                tenant_id='default',
                roles=['user']
            )
            logger.info("Created test user")
            
        except Exception as e:
            logger.error(f"Error creating test user: {str(e)}")
            
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict containing user info if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            # Verify user exists
            user = await self.user_repository.get_user_by_id(payload['sub'])
            if not user:
                return None
                
            return payload
            
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
