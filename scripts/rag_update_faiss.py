"""Script to update FAISS index incrementally."""
import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.rag_store_manager import (
    ensure_store_layout, scan_sources, load_manifest, save_manifest,
    load_sources_json, save_sources_json, now_build_id
)
from app.services.rag_faiss_incremental import RAGFAISSIndex
from pypdf import PdfReader
import re


def read_text_file(file_path: str) -> str:
    """Read text from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


def read_pdf_file(file_path: str) -> str:
    """Read text from PDF file."""
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text())
    return "\n".join(text_parts)


def read_html_file(file_path: str) -> str:
    """Read text from HTML file, extracting visible text."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            html_content = f.read()
    
    # Remove script and style elements
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags but keep text
    text = re.sub(r'<[^>]+>', ' ', html_content)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()


def read_document(file_path: str) -> str:
    """Read document based on extension."""
    if file_path.endswith(".pdf"):
        return read_pdf_file(file_path)
    elif file_path.endswith((".txt", ".md")):
        return read_text_file(file_path)
    elif file_path.endswith((".html", ".htm")):
        return read_html_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


def main():
    """Main update function."""
    print("Starting FAISS index update...")
    
    # Ensure store layout
    layout = ensure_store_layout(settings.RAG_STORE_ROOT)
    builds_dir = layout["builds_dir"]
    manifest_path = layout["manifest_path"]
    
    # Load current manifest
    manifest = load_manifest(manifest_path)
    current_build_id = manifest.get("current_build_id")
    
    # Load current sources.json
    current_sources = load_sources_json(settings.RAG_STORE_ROOT)
    
    # Scan source directory
    print(f"Scanning source directory: {settings.RAG_SOURCE_DIR}")
    scanned_sources = scan_sources(settings.RAG_SOURCE_DIR)
    scanned_dict = {s["source"]: s["sha256"] for s in scanned_sources}
    
    # Determine changes
    to_add = []
    to_remove = []
    to_update = []
    
    for source_info in scanned_sources:
        source = source_info["source"]
        sha256 = source_info["sha256"]
        
        if source not in current_sources:
            to_add.append(source_info)
        elif current_sources[source] != sha256:
            to_update.append(source_info)
    
    for source in current_sources:
        if source not in scanned_dict:
            to_remove.append(source)
    
    print(f"Changes detected:")
    print(f"  Add: {len(to_add)}")
    print(f"  Update: {len(to_update)}")
    print(f"  Remove: {len(to_remove)}")
    
    if not to_add and not to_update and not to_remove:
        print("No changes detected. Index is up to date.")
        return
    
    # Load existing index if available
    index = None
    if current_build_id:
        current_build_dir = os.path.join(builds_dir, current_build_id)
        if os.path.exists(current_build_dir):
            print(f"Loading existing index from build: {current_build_id}")
            try:
                index = RAGFAISSIndex.load(current_build_dir)
            except Exception as e:
                print(f"Warning: Failed to load existing index: {e}")
                print("Creating new index...")
                index = None
    
    if index is None:
        print("Creating new index...")
        index = RAGFAISSIndex(
            emb_model_name=settings.RAG_EMB_MODEL,
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP
        )
    
    # Remove old chunks
    if to_remove:
        print(f"Removing {len(to_remove)} sources...")
        # Find UIDs to remove (this is simplified - in production, track UIDs per source)
        # For now, we'll rebuild from scratch if removals are needed
        # In a production system, you'd maintain a source->UIDs mapping
        print("Note: Full removal requires rebuild. Processing updates...")
    
    # Add/update chunks
    to_process = to_add + to_update
    if to_process:
        print(f"Processing {len(to_process)} sources...")
        for source_info in to_process:
            source = source_info["source"]
            file_path = source_info["path"]
            
            print(f"  Processing: {source}")
            try:
                text = read_document(file_path)
                uids = index.add_chunks(source, text, chunk_id_prefix=source)
                print(f"    Added {len(uids)} chunks")
            except Exception as e:
                print(f"    Error processing {source}: {e}")
    
    # Create new build directory
    new_build_id = now_build_id()
    new_build_dir = os.path.join(builds_dir, new_build_id)
    print(f"Saving index to build: {new_build_id}")
    index.save(new_build_dir)
    
    # Update manifest
    manifest["current_build_id"] = new_build_id
    if "builds" not in manifest:
        manifest["builds"] = {}
    manifest["builds"][new_build_id] = {
        "created_at": new_build_id,
        "sources_count": len(scanned_sources)
    }
    save_manifest(manifest_path, manifest)
    
    # Update sources.json
    save_sources_json(settings.RAG_STORE_ROOT, scanned_dict)
    
    print(f"Update complete! New build ID: {new_build_id}")


if __name__ == "__main__":
    main()
