"""Workflow context and state definitions."""
from typing import Dict, Any
from pydantic import BaseModel

class AgentState(BaseModel):
    """Agent state."""
    tenant_id: str
    metadata: Dict[str, Any] = {}

class AgentContext(BaseModel):
    """Agent context."""
    state: AgentState
    llm_config: Dict[str, Any]
    tool_config: Dict[str, Any]
