"""FAISS-based RAG index with incremental updates."""
import os
import json
import hashlib
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.config import settings


class RAGFAISSIndex:
    """FAISS index for RAG with incremental updates."""
    
    def __init__(
        self,
        emb_model_name: str = None,
        dim: int = 384,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.emb_model_name = emb_model_name or settings.RAG_EMB_MODEL
        self.dim = dim
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
        
        # Load embedding model
        self.emb_model = SentenceTransformer(self.emb_model_name)
        # Update dim from model
        self.dim = self.emb_model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        # Use IndexIDMap2 to support add/remove by ID
        base_index = faiss.IndexFlatIP(self.dim)  # Inner product for cosine similarity
        self.index = faiss.IndexIDMap2(base_index)
        
        # Metadata: uid -> {source, chunk_id, text}
        self.metadata: Dict[int, Dict[str, Any]] = {}
    
    def _generate_uid(self, source: str, offset: int, text: str) -> int:
        """Generate unique ID from source:offset:text."""
        uid_str = f"{source}:{offset}:{text}"
        sha1 = hashlib.sha1(uid_str.encode()).digest()
        # Use first 8 bytes as int64
        return int.from_bytes(sha1[:8], byteorder="big", signed=True)
    
    def _chunk_text(self, text: str) -> List[tuple[int, str]]:
        """Chunk text into overlapping segments."""
        chunks = []
        offset = 0
        
        while offset < len(text):
            chunk = text[offset:offset + self.chunk_size]
            if not chunk.strip():
                break
            chunks.append((offset, chunk))
            offset += self.chunk_size - self.chunk_overlap
        
        return chunks
    
    def add_chunks(
        self,
        source: str,
        text: str,
        chunk_id_prefix: str = None
    ) -> List[int]:
        """
        Add chunks from text to index.
        
        Returns:
            List of UIDs added
        """
        chunks = self._chunk_text(text)
        uids = []
        embeddings = []
        
        for offset, chunk_text in chunks:
            uid = self._generate_uid(source, offset, chunk_text)
            chunk_id = chunk_id_prefix or f"{source}_{offset}"
            
            # Embed chunk
            emb = self.emb_model.encode(chunk_text, normalize_embeddings=True)
            emb = emb.astype(np.float32)
            
            # Store metadata
            self.metadata[uid] = {
                "source": source,
                "chunk_id": chunk_id,
                "text": chunk_text,
                "offset": offset
            }
            
            uids.append(uid)
            embeddings.append(emb)
        
        if embeddings:
            # Add to FAISS index
            embeddings_array = np.array(embeddings, dtype=np.float32)
            uids_array = np.array(uids, dtype=np.int64)
            self.index.add_with_ids(embeddings_array, uids_array)
        
        return uids
    
    def remove_uids(self, uids: List[int]):
        """Remove chunks by UIDs."""
        for uid in uids:
            if uid in self.metadata:
                del self.metadata[uid]
        
        # FAISS doesn't support direct removal, so we rebuild
        # For production, consider using IndexIDMap with remove_ids (if available)
        # For now, we'll mark as removed in metadata and filter during search
        # This is a limitation - full rebuild would be needed for true removal
    
    def search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """
        Search index for similar chunks.
        
        Returns:
            List of hits with score, source, chunk_id, text
        """
        # Embed query
        query_emb = self.emb_model.encode(query, normalize_embeddings=True)
        query_emb = query_emb.astype(np.float32).reshape(1, -1)
        
        # Search
        k = min(top_k, self.index.ntotal) if self.index.ntotal > 0 else 0
        if k == 0:
            return []
        
        scores, indices = self.index.search(query_emb, k)
        
        hits = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for invalid indices
                continue
            
            if idx not in self.metadata:
                continue
            
            meta = self.metadata[idx]
            hits.append({
                "score": float(score),
                "source": meta["source"],
                "chunk_id": meta["chunk_id"],
                "text": meta["text"]
            })
        
        return hits
    
    def save(self, store_dir: str):
        """Save index and metadata to directory."""
        os.makedirs(store_dir, exist_ok=True)
        
        # Save FAISS index
        index_path = os.path.join(store_dir, "index.faiss")
        faiss.write_index(self.index, index_path)
        
        # Save metadata
        metadata_path = os.path.join(store_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        
        # Save config
        config_path = os.path.join(store_dir, "config.json")
        config = {
            "emb_model": self.emb_model_name,
            "dim": self.dim,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def load(cls, store_dir: str) -> "RAGFAISSIndex":
        """Load index and metadata from directory."""
        # Load config
        config_path = os.path.join(store_dir, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Create instance
        instance = cls(
            emb_model_name=config["emb_model"],
            dim=config["dim"],
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"]
        )
        
        # Load FAISS index
        index_path = os.path.join(store_dir, "index.faiss")
        instance.index = faiss.read_index(index_path)
        
        # Load metadata
        metadata_path = os.path.join(store_dir, "metadata.json")
        with open(metadata_path, "r", encoding="utf-8") as f:
            instance.metadata = {int(k): v for k, v in json.load(f).items()}
        
        return instance
