"""API request/response schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ERASRequest(BaseModel):
    """Request schema for ERAS evaluation."""
    scenario: Optional[str] = Field(None, description="Scenario: PONV, POD, or CHEST_TUBE")
    question: str = Field(..., description="Clinical question")
    top_k: int = Field(6, ge=1, le=20, description="Number of retrieval hits")
    patient_fhir: Dict[str, Any] = Field(..., description="Patient FHIR data")


class Citation(BaseModel):
    """Citation schema."""
    source: str = Field(..., description="Source document name")
    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Cited text excerpt")


class ERASResponse(BaseModel):
    """Response schema for ERAS evaluation."""
    final_recommendation: str = Field(..., description="Final recommendation")
    final_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    key_reasons: List[str] = Field(default_factory=list, description="Key reasons")
    risks_and_notes: List[str] = Field(default_factory=list, description="Risks and notes")
    missing_data: List[str] = Field(default_factory=list, description="Missing data fields")
    conflicts: List[str] = Field(default_factory=list, description="Conflicts between agents")
    citations: List[Citation] = Field(default_factory=list, description="Citations from RAG")
    agents: List[Dict[str, Any]] = Field(default_factory=list, description="Raw agent decisions")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Metrics (latency, errors, etc.)")
