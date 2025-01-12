"""
Mock context classes for testing.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class AgentState:
    tenant_id: str
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id
        }

@dataclass
class AgentContext:
    state: AgentState
    model_config: Dict[str, Any]
    tool_config: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "model_config": self.model_config,
            "tool_config": self.tool_config
        }
