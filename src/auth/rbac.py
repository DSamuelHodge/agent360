from enum import Enum
from typing import List, Set, Dict
from pydantic import BaseModel

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    MANAGE = "manage"

class RBACService:
    def __init__(self):
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.MANAGE},
            Role.OPERATOR: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
            Role.USER: {Permission.READ, Permission.EXECUTE}
        }
    
    def has_permission(self, role: Role, required_permission: Permission) -> bool:
        return required_permission in self.role_permissions.get(role, set())
