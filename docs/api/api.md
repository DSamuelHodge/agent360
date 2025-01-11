# Agent360 API Documentation

## Overview
This document provides comprehensive documentation for the Agent360 API.

## Table of Contents
1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
3. [Rate Limiting](#rate-limiting)
4. [Error Handling](#error-handling)
5. [Versioning](#versioning)
6. [Best Practices](#best-practices)

## Authentication

### API Keys
```python
# auth/api_keys.py
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not is_valid_api_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    return api_key
```

### JWT Authentication
```python
# auth/jwt.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
```

## Endpoints

### Agent Execution
```python
# api/agent.py
from fastapi import APIRouter, Depends
from typing import Dict, List

router = APIRouter()

@router.post("/agent/execute")
async def execute_agent(
    request: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """
    Execute an agent with the given request.
    
    Parameters:
    - query (str): The query to process
    - tools (List[str]): List of tools to use
    - context (Dict): Additional context
    
    Returns:
    - response (Dict): Agent execution response
    """
    try:
        return await agent_service.execute(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
```

### Workflow Management
```python
# api/workflow.py
@router.post("/workflow/create")
async def create_workflow(
    workflow: WorkflowCreate,
    token: str = Depends(verify_token)
):
    """
    Create a new workflow.
    
    Parameters:
    - name (str): Workflow name
    - steps (List[Step]): Workflow steps
    - config (Dict): Workflow configuration
    
    Returns:
    - workflow_id (str): Created workflow ID
    """
    return await workflow_service.create(workflow)

@router.get("/workflow/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    token: str = Depends(verify_token)
):
    """
    Get workflow details.
    
    Parameters:
    - workflow_id (str): Workflow ID
    
    Returns:
    - workflow (Dict): Workflow details
    """
    return await workflow_service.get(workflow_id)
```

### Tool Management
```python
# api/tools.py
@router.get("/tools")
async def list_tools(token: str = Depends(verify_token)):
    """
    List available tools.
    
    Returns:
    - tools (List[Dict]): List of available tools
    """
    return await tool_service.list_tools()

@router.post("/tools/{tool_id}/execute")
async def execute_tool(
    tool_id: str,
    params: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """
    Execute a specific tool.
    
    Parameters:
    - tool_id (str): Tool identifier
    - params (Dict): Tool parameters
    
    Returns:
    - result (Dict): Tool execution result
    """
    return await tool_service.execute(tool_id, params)
```

## Rate Limiting

### Rate Limiter Configuration
```python
# middleware/rate_limit.py
from fastapi import Request
import redis
import time

class RateLimiter:
    def __init__(self):
        self.redis = redis.Redis()
        self.rate_limit = 100  # requests per minute
        self.window = 60  # seconds
    
    async def is_rate_limited(self, key: str) -> bool:
        current = int(time.time())
        pipeline = self.redis.pipeline()
        
        # Add current timestamp
        pipeline.zadd(key, {current: current})
        
        # Remove old entries
        pipeline.zremrangebyscore(
            key,
            0,
            current - self.window
        )
        
        # Count requests in window
        pipeline.zcard(key)
        
        # Set key expiry
        pipeline.expire(key, self.window)
        
        _, _, count, _ = pipeline.execute()
        
        return count > self.rate_limit
```

### Rate Limit Middleware
```python
# middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = request.headers.get("X-API-Key")
        
        # Check rate limit
        if await rate_limiter.is_rate_limited(client_id):
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        
        return await call_next(request)
```

## Error Handling

### Error Definitions
```python
# errors/definitions.py
from typing import Dict, Optional

class APIError(Exception):
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: Optional[Dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(APIError):
    def __init__(self, message: str, details: Dict):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )

class AuthenticationError(APIError):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )
```

### Error Handlers
```python
# errors/handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred"
            }
        }
    )
```

## Versioning

### Version Management
```python
# api/versioning.py
from fastapi import APIRouter, Depends
from enum import Enum

class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"

def get_api_version(version: APIVersion):
    return version

router = APIRouter()

@router.post("/v{version}/agent/execute")
async def execute_agent(
    request: Dict[str, Any],
    version: APIVersion = Depends(get_api_version)
):
    if version == APIVersion.V1:
        return await agent_service.execute_v1(request)
    elif version == APIVersion.V2:
        return await agent_service.execute_v2(request)
```

## Best Practices

### 1. Authentication
- Use secure authentication methods
- Implement token expiration
- Rotate API keys regularly
- Use HTTPS only

### 2. Rate Limiting
- Set appropriate limits
- Implement gradual backoff
- Monitor usage patterns
- Alert on abuse

### 3. Error Handling
- Use consistent error formats
- Provide meaningful messages
- Include error codes
- Log errors properly

### 4. Documentation
- Keep docs updated
- Include examples
- Document all parameters
- Version documentation
