"""Main API entry point for Agent360."""
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from src.auth.authentication_service import AuthenticationService
from src.workflows.workflow_service import WorkflowService
from src.database.connection import get_connection, DatabaseConnection
from src.config import get_settings

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

# Initialize settings
settings = get_settings()

# Initialize app state
app.state.auth_service = None
app.state.workflow_service = None
app.state.db = None

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_auth_service() -> AuthenticationService:
    """Get authentication service from app state."""
    if not app.state.auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized"
        )
    return app.state.auth_service

async def get_workflow_service() -> WorkflowService:
    """Get workflow service from app state."""
    if not app.state.workflow_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow service not initialized"
        )
    return app.state.workflow_service

async def get_db() -> DatabaseConnection:
    """Get database connection from app state."""
    if not app.state.db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    return app.state.db

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Initialize database connection
        app.state.db = get_connection()
        await app.state.db.connect()
        
        # Initialize services with proper dependencies
        app.state.auth_service = AuthenticationService(
            user_repository=None  # Will use default from AuthenticationService
        )
        app.state.workflow_service = WorkflowService(
            db=app.state.db
        )
        
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if app.state.db:
        await app.state.db.disconnect()

@app.post("/api/v1/auth/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Login endpoint to get access token."""
    user = await auth_service.authenticate(
        username=form_data.username,
        password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": auth_service.create_token(user),
        "token_type": "bearer"
    }

@app.post("/api/v1/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    token: str = Depends(oauth2_scheme),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Execute a workflow by ID."""
    # Verify token and get user
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        result = await workflow_service.execute_workflow(
            workflow_id=workflow_id,
            user_id=user["id"]
        )
        return result
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    token: str = Depends(oauth2_scheme),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Get workflow execution status."""
    # Verify token and get user
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        status = await workflow_service.get_workflow_status(
            workflow_id=workflow_id,
            user_id=user["id"]
        )
        return status
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
