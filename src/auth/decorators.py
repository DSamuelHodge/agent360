from functools import wraps
from fastapi import HTTPException, Depends
from typing import Callable, List

from .rbac import Permission, Role, RBACService
from .authentication_service import AuthenticationService, User

def require_permissions(required_permissions: List[Permission]):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the current user from the request context
            current_user: User = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="User not authenticated"
                )

            rbac_service = RBACService()
            
            # Check if user's role has all required permissions
            for permission in required_permissions:
                if not rbac_service.has_permission(current_user.role, permission):
                    raise HTTPException(
                        status_code=403,
                        detail=f"User does not have required permission: {permission}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
