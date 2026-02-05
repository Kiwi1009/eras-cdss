"""Scenario routing logic."""
from typing import Optional, Dict, Any
from enum import Enum


class Scenario(str, Enum):
    """Supported scenarios."""
    PONV = "PONV"
    POD = "POD"
    CHEST_TUBE = "CHEST_TUBE"
    UNKNOWN = "UNKNOWN"


def infer_scenario(
    explicit: Optional[str],
    question: str,
    patient_fhir: Dict[str, Any]
) -> Scenario:
    """
    Infer scenario from explicit value, question, or patient data.
    
    Args:
        explicit: Explicitly provided scenario
        question: Clinical question text
        patient_fhir: Patient FHIR data
        
    Returns:
        Scenario enum value
    """
    # If explicit scenario provided and valid, use it
    if explicit:
        explicit_upper = explicit.upper()
        if explicit_upper in ["PONV", "POD", "CHEST_TUBE"]:
            return Scenario[explicit_upper]
    
    # Infer from question keywords
    question_lower = question.lower()
    
    if any(kw in question_lower for kw in ["ponv", "postoperative nausea", "nausea", "vomiting"]):
        return Scenario.PONV
    
    if any(kw in question_lower for kw in ["pod", "delirium", "confusion", "cognitive"]):
        return Scenario.POD
    
    if any(kw in question_lower for kw in ["chest tube", "drain", "pleural", "thoracic"]):
        return Scenario.CHEST_TUBE
    
    # Infer from patient data structure
    if patient_fhir:
        # Check for PONV-related fields
        if any(key in patient_fhir for key in ["nausea_score", "vomiting_episodes"]):
            return Scenario.PONV
        
        # Check for POD-related fields
        if any(key in patient_fhir for key in ["nu_desc", "cam_score"]):
            return Scenario.POD
        
        # Check for chest tube fields
        if any(key in patient_fhir for key in ["drain_output_ml_24h", "chest_tube_days"]):
            return Scenario.CHEST_TUBE
    
    return Scenario.UNKNOWN
