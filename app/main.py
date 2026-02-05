"""FastAPI main application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.schemas import ERASRequest, ERASResponse
from app.services.decision_pipeline import run_decision
from app.services.retriever_hybrid import HybridRetriever
from app.services.rag_store_manager import load_manifest, ensure_store_layout
from app.services.llm.factory import get_llm_backend
from app.config import settings
import os

app = FastAPI(title="ERAS CDSS", version="1.0.0")

# CORS: allow frontend from any origin (same host or different)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """Serve frontend index page."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "ERAS CDSS API", "frontend": "Please ensure static files are available"}


def _get_patients_path():
    """Resolve data/patients.jsonl from project root (works from any cwd)."""
    import json
    from pathlib import Path
    # Project root: parent of app/ (where main.py lives)
    app_dir = Path(__file__).resolve().parent
    project_root = app_dir.parent
    candidates = [
        project_root / "data" / "patients.jsonl",
        Path.cwd() / "data" / "patients.jsonl",
        Path.cwd() / "eras-cdss" / "data" / "patients.jsonl",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


@app.get("/api/patients")
async def get_patients():
    """Return 30 demo patients from data/patients.jsonl."""
    import json
    patients_path = _get_patients_path()
    if not patients_path:
        raise HTTPException(
            status_code=404,
            detail="data/patients.jsonl not found. Please add data/patients.jsonl to the project."
        )
    patients = []
    try:
        with open(patients_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    patients.append(json.loads(line))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read patients file: {str(e)}")
    return patients


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    # Get current build ID
    layout = ensure_store_layout(settings.RAG_STORE_ROOT)
    manifest = load_manifest(layout["manifest_path"])
    current_build_id = manifest.get("current_build_id", "none")
    
    # Get LLM backend name
    try:
        backend = get_llm_backend()
        backend_name = backend.name
    except Exception as e:
        backend_name = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "rag_current_build_id": current_build_id,
        "llm_backend": backend_name
    }


@app.post("/eras/evaluate", response_model=ERASResponse)
async def evaluate(req: ERASRequest):
    """
    Evaluate patient using ERAS CDSS.
    
    Returns ERASResponse with recommendation, actions, citations, etc.
    """
    try:
        result = await run_decision(req)
        return ERASResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
