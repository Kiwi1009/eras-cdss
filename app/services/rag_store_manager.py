"""RAG store management and versioning."""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def ensure_store_layout(store_root: str) -> Dict[str, str]:
    """
    Ensure RAG store directory structure exists.
    
    Returns:
        Dict with 'builds_dir' and 'manifest_path'
    """
    builds_dir = os.path.join(store_root, "builds")
    os.makedirs(builds_dir, exist_ok=True)
    os.makedirs(store_root, exist_ok=True)
    
    manifest_path = os.path.join(store_root, "manifest.json")
    
    return {
        "builds_dir": builds_dir,
        "manifest_path": manifest_path
    }


def scan_sources(source_dir: str) -> List[Dict[str, Any]]:
    """
    Scan source directory for documents.
    
    Returns:
        List of dicts with 'source', 'path', 'sha256'
    """
    sources = []
    
    if not os.path.exists(source_dir):
        return sources
    
    for root, dirs, files in os.walk(source_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
        
        for file in files:
            # Skip manifest and chunks files
            if file in ['_manifest.json', 'manifest.json', 'chunks.jsonl']:
                continue
            
            if file.endswith((".pdf", ".txt", ".md", ".html", ".htm")):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)
                
                # Calculate SHA256
                sha256 = calculate_sha256(file_path)
                
                sources.append({
                    "source": rel_path,
                    "path": file_path,
                    "sha256": sha256
                })
    
    return sources


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def now_build_id() -> str:
    """Generate build ID from current timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """Load manifest.json."""
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "current_build_id": None,
        "builds": {}
    }


def save_manifest(manifest_path: str, manifest: Dict[str, Any]):
    """Save manifest.json."""
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def load_sources_json(store_root: str) -> Dict[str, str]:
    """Load sources.json mapping source -> sha256."""
    sources_path = os.path.join(store_root, "sources.json")
    if os.path.exists(sources_path):
        with open(sources_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sources_json(store_root: str, sources_dict: Dict[str, str]):
    """Save sources.json."""
    sources_path = os.path.join(store_root, "sources.json")
    with open(sources_path, "w", encoding="utf-8") as f:
        json.dump(sources_dict, f, indent=2, ensure_ascii=False)
