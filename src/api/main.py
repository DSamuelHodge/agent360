"""Main API entry point for Agent360."""
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from ..auth.authentication_service import AuthenticationService
from ..workflows.workflow_service import WorkflowService
from ..database.connection import get_connection
from ..config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str

# Initialize FastAPI app
app = FastAPI(title="Agent360 API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
settings = get_settings()
auth_service = AuthenticationService()
workflow_service = WorkflowService()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Initialize database connection
        db = get_connection()
        await db.connect()
        
        # Initialize auth service
        await auth_service.initialize()
        
        logger.info("Successfully initialized all services")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise

@app.post("/api/v1/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get access token."""
    try:
        result = await auth_service.authenticate(
            form_data.username,
            form_data.password
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return result
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/api/v1/workflows/execute")
async def execute_workflow(workflow_id: str, token: str = Depends(oauth2_scheme)):
    """Execute a workflow by ID."""
    try:
        # Verify token
        user = await auth_service.verify_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        # Execute workflow
        result = await workflow_service.execute_workflow(
            workflow_id,
            user_id=user['sub']
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Workflow execution error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/api/v1/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str, token: str = Depends(oauth2_scheme)):
    """Get workflow execution status."""
    try:
        # Verify token
        user = await auth_service.verify_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        # Get status
        status = await workflow_service.get_workflow_status(
            workflow_id,
            user_id=user['sub']
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Workflow status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
