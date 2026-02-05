"""Schema validation for agent and arbiter decisions."""
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict, Any
import json
import re


class AgentDecision(BaseModel):
    """Agent decision schema."""
    recommendation: str = Field(..., description="Recommendation text")
    actions: List[str] = Field(default_factory=list, description="Recommended actions")
    reasons: List[str] = Field(default_factory=list, description="Key reasons")
    risks: List[str] = Field(default_factory=list, description="Risks and notes")
    citations: List[Dict[str, str]] = Field(..., description="Citations with source and chunk_id")
    
    class Config:
        extra = "forbid"


class ArbiterDecision(BaseModel):
    """Arbiter decision schema."""
    final_recommendation: str = Field(..., description="Final recommendation")
    final_actions: List[str] = Field(default_factory=list, description="Final actions")
    key_reasons: List[str] = Field(default_factory=list, description="Key reasons")
    risks_and_notes: List[str] = Field(default_factory=list, description="Risks and notes")
    conflicts: List[str] = Field(default_factory=list, description="Conflicts between agents")
    citations: List[Dict[str, str]] = Field(..., description="Citations with source and chunk_id")
    
    class Config:
        extra = "forbid"


def extract_json_from_text(text: str) -> Optional[str]:
    """Extract JSON from text that may contain markdown or extra text."""
    # Try to find JSON block in markdown code fence
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return None


def parse_agent_decision(raw: str) -> tuple[Optional[AgentDecision], Optional[str]]:
    """
    Parse agent decision from raw LLM output.
    
    Returns:
        (AgentDecision, error_message) - error_message is None if successful
    """
    try:
        json_str = extract_json_from_text(raw)
        if not json_str:
            return None, "No JSON found in response"
        
        data = json.loads(json_str)
        decision = AgentDecision(**data)
        return decision, None
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {str(e)}"
    except ValidationError as e:
        return None, f"Validation error: {str(e)}"
    except Exception as e:
        return None, f"Parse error: {str(e)}"


def parse_arbiter_decision(raw: str) -> tuple[Optional[ArbiterDecision], Optional[str]]:
    """
    Parse arbiter decision from raw LLM output.
    
    Returns:
        (ArbiterDecision, error_message) - error_message is None if successful
    """
    try:
        json_str = extract_json_from_text(raw)
        if not json_str:
            return None, "No JSON found in response"
        
        data = json.loads(json_str)
        decision = ArbiterDecision(**data)
        return decision, None
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {str(e)}"
    except ValidationError as e:
        return None, f"Validation error: {str(e)}"
    except Exception as e:
        return None, f"Parse error: {str(e)}"
