"""Input validation for patient data."""
from typing import Dict, Any, List
from pydantic import BaseModel
from .scenario_router import Scenario


class ValidationResult(BaseModel):
    """Validation result."""
    ok: bool
    missing: List[str]
    errors: List[str]


def validate_inputs(
    scenario: Scenario,
    patient_fhir: Dict[str, Any]
) -> ValidationResult:
    """
    Validate patient FHIR data for given scenario.
    
    Args:
        scenario: Clinical scenario
        patient_fhir: Patient FHIR data
        
    Returns:
        ValidationResult with ok status, missing fields, and errors
    """
    missing = []
    errors = []
    
    if scenario == Scenario.POD:
        # POD requires Nu-DESC scores (each 0-2)
        if "nu_desc" not in patient_fhir:
            missing.append("nu_desc")
        else:
            nu_desc = patient_fhir["nu_desc"]
            if not isinstance(nu_desc, dict):
                errors.append("nu_desc must be a dictionary")
            else:
                required_items = ["disorientation", "inappropriate_behavior", 
                                "inappropriate_communication", "psychomotor_retardation"]
                # Support both "illusions" and "illusions_hallucinations" for backward compatibility
                illusions_key = None
                if "illusions_hallucinations" in nu_desc:
                    illusions_key = "illusions_hallucinations"
                elif "illusions" in nu_desc:
                    illusions_key = "illusions"
                
                for item in required_items:
                    if item not in nu_desc:
                        missing.append(f"nu_desc.{item}")
                    else:
                        score = nu_desc[item]
                        if not isinstance(score, int) or score < 0 or score > 2:
                            errors.append(f"nu_desc.{item} must be integer 0-2, got {score}")
                
                # Check illusions/illusions_hallucinations
                if illusions_key is None:
                    missing.append("nu_desc.illusions_hallucinations (or nu_desc.illusions)")
                else:
                    score = nu_desc[illusions_key]
                    if not isinstance(score, int) or score < 0 or score > 2:
                        errors.append(f"nu_desc.{illusions_key} must be integer 0-2, got {score}")
        
        # Koivuranta requires surgery_duration_min
        if "surgery_duration_min" not in patient_fhir:
            missing.append("surgery_duration_min")
        else:
            dur = patient_fhir["surgery_duration_min"]
            if not isinstance(dur, int) or dur < 0:
                errors.append(f"surgery_duration_min must be non-negative integer, got {dur}")
    
    elif scenario == Scenario.CHEST_TUBE:
        # Chest tube removal validation (non-digital chest tube)
        required_fields = {
            "air_leak_present": bool,
            "drain_output_ml_24h": int,
            "fluid_quality": str,  # serous/serosanguineous/bloody/other
            "active_bleeding_suspected": bool,
            "lung_expanded": bool,
            "threshold_ml_24h": int  # default 450
        }
        
        for field, field_type in required_fields.items():
            if field not in patient_fhir:
                if field == "threshold_ml_24h":
                    # Set default if missing
                    patient_fhir[field] = 450
                else:
                    missing.append(field)
            else:
                val = patient_fhir[field]
                if field_type == int:
                    if not isinstance(val, int) or val < 0:
                        errors.append(f"{field} must be non-negative integer, got {val}")
                elif field_type == bool:
                    if not isinstance(val, bool):
                        errors.append(f"{field} must be boolean, got {val}")
                elif field_type == str:
                    if not isinstance(val, str):
                        errors.append(f"{field} must be string, got {val}")
                    elif field == "fluid_quality" and val not in ["serous", "serosanguineous", "bloody", "other"]:
                        errors.append(f"{field} must be one of: serous, serosanguineous, bloody, other")
    
    elif scenario == Scenario.PONV:
        # PONV Koivuranta score validation
        required_fields = [
            "female",  # bool
            "non_smoker",  # bool
            "hx_ponv",  # bool (history of PONV)
            "hx_motion_sickness",  # bool (history of motion sickness)
            "surgery_duration_min"  # int
        ]
        for field in required_fields:
            if field not in patient_fhir:
                missing.append(field)
            elif field == "surgery_duration_min":
                val = patient_fhir[field]
                if not isinstance(val, int) or val < 0:
                    errors.append(f"{field} must be non-negative integer, got {val}")
            else:
                val = patient_fhir[field]
                if not isinstance(val, bool):
                    errors.append(f"{field} must be boolean, got {val}")
    
    ok = len(missing) == 0 and len(errors) == 0
    
    return ValidationResult(ok=ok, missing=missing, errors=errors)
