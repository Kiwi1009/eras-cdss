"""Evaluate 30 patients from JSONL file."""
import os
import sys
import json
import csv
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas import ERASRequest
from app.services.decision_pipeline import run_decision


async def evaluate_patient(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single patient."""
    req = ERASRequest(
        scenario=patient_data.get("scenario"),
        question=patient_data.get("question", "What is the recommended clinical decision?"),
        top_k=patient_data.get("top_k", 6),
        patient_fhir=patient_data.get("patient_fhir", {})
    )
    
    result = await run_decision(req)
    return result


async def main():
    """Main evaluation function."""
    patients_jsonl = os.getenv("PATIENTS_JSONL", "data/patients.jsonl")
    
    if not os.path.exists(patients_jsonl):
        print(f"Error: Patients file not found: {patients_jsonl}")
        print("Please set PATIENTS_JSONL environment variable or create the file.")
        return
    
    print(f"Reading patients from: {patients_jsonl}")
    
    # Read patients
    patients = []
    with open(patients_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                patients.append(json.loads(line))
    
    print(f"Found {len(patients)} patients")
    
    # Evaluate each patient
    results = []
    for i, patient in enumerate(patients, 1):
        patient_id = patient.get("patient_id", f"patient_{i}")
        print(f"\n[{i}/{len(patients)}] Evaluating {patient_id}...")
        
        try:
            result = await evaluate_patient(patient)
            result["patient_id"] = patient_id
            result["scenario"] = result.get("metrics", {}).get("scenario", "UNKNOWN")
            results.append(result)
            print(f"  ✓ Completed (latency: {result.get('metrics', {}).get('latency_ms', 0)}ms)")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "patient_id": patient_id,
                "error": str(e),
                "scenario": patient.get("scenario", "UNKNOWN"),
                "final_recommendation": "ERROR",
                "metrics": {"latency_ms": 0, "errors": [str(e)]}
            })
    
    # Write results.jsonl
    results_file = "results.jsonl"
    print(f"\nWriting results to: {results_file}")
    with open(results_file, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    # Write summary.csv
    summary_file = "summary.csv"
    print(f"Writing summary to: {summary_file}")
    
    with open(summary_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "patient_id", "scenario", "final_recommendation",
            "latency_ms", "citations_n", "trace_id", "errors_arbiter"
        ])
        writer.writeheader()
        
        for result in results:
            metrics = result.get("metrics", {})
            citations = result.get("citations", [])
            
            # Extract arbiter errors
            errors = metrics.get("errors", [])
            arbiter_errors = [e for e in errors if "arbiter" in str(e).lower()] or ["none"]
            
            writer.writerow({
                "patient_id": result.get("patient_id", "unknown"),
                "scenario": result.get("scenario", "UNKNOWN"),
                "final_recommendation": result.get("final_recommendation", "N/A"),
                "latency_ms": metrics.get("latency_ms", 0),
                "citations_n": len(citations),
                "trace_id": metrics.get("trace_id", "N/A"),
                "errors_arbiter": "; ".join(arbiter_errors)
            })
    
    print(f"\nEvaluation complete!")
    print(f"  Results: {results_file}")
    print(f"  Summary: {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())
