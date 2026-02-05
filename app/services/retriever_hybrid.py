"""Hybrid retriever that loads FAISS index."""
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.rag_store_manager import load_manifest, ensure_store_layout
from app.services.rag_faiss_incremental import RAGFAISSIndex
import os


class HybridRetriever:
    """Hybrid retriever with FAISS backend."""
    
    def __init__(self, store_root: str = None):
        self.store_root = store_root or settings.RAG_STORE_ROOT
        self.index: Optional[RAGFAISSIndex] = None
        self.current_build_id: Optional[str] = None
        
        if settings.RAG_ENABLED:
            self._load_index()
    
    def _load_index(self):
        """Load current FAISS index from store."""
        try:
            layout = ensure_store_layout(self.store_root)
            manifest = load_manifest(layout["manifest_path"])
            
            current_build_id = manifest.get("current_build_id")
            if not current_build_id:
                return
            
            self.current_build_id = current_build_id
            build_dir = os.path.join(layout["builds_dir"], current_build_id)
            
            if os.path.exists(build_dir):
                self.index = RAGFAISSIndex.load(build_dir)
        except Exception as e:
            # Log error but don't crash
            print(f"Warning: Failed to load RAG index: {e}")
            self.index = None
    
    def retrieve(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for query.
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of hits with score, source, chunk_id, text
        """
        if not self.index:
            return []
        
        try:
            hits = self.index.search(query, top_k=k)
            return hits
        except Exception as e:
            print(f"Warning: Retrieval error: {e}")
            return []
