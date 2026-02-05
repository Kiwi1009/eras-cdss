"""Post-processing for retrieval hits."""
from typing import List, Dict, Any


def clean_text_for_prompt(text: str) -> str:
    """Clean text for use in prompts."""
    # Remove excessive whitespace
    text = " ".join(text.split())
    # Remove control characters
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
    return text.strip()


def filter_and_dedupe_hits(
    hits: List[Dict[str, Any]],
    min_chars: int = 120,
    per_source_cap: int = 3
) -> List[Dict[str, Any]]:
    """
    Filter and deduplicate hits.
    
    Args:
        hits: List of retrieval hits
        min_chars: Minimum text length
        per_source_cap: Maximum hits per source
        
    Returns:
        Filtered and deduplicated hits
    """
    # Filter by minimum length
    filtered = [h for h in hits if len(h.get("text", "")) >= min_chars]
    
    # Deduplicate by (source, chunk_id)
    seen = set()
    deduped = []
    for hit in filtered:
        key = (hit["source"], hit["chunk_id"])
        if key not in seen:
            seen.add(key)
            deduped.append(hit)
    
    # Cap per source
    source_counts = {}
    capped = []
    for hit in deduped:
        source = hit["source"]
        count = source_counts.get(source, 0)
        if count < per_source_cap:
            source_counts[source] = count + 1
            capped.append(hit)
    
    return capped


def format_hits_context(hits: List[Dict[str, Any]]) -> str:
    """
    Format hits as context string for prompts.
    
    Args:
        hits: List of retrieval hits
        
    Returns:
        Formatted context string
    """
    if not hits:
        return "No relevant context found."
    
    context_parts = ["Available evidence from clinical guidelines:"]
    for i, hit in enumerate(hits, 1):
        source = hit.get("source", "unknown")
        chunk_id = hit.get("chunk_id", "unknown")
        text = clean_text_for_prompt(hit.get("text", ""))
        context_parts.append(
            f"\n[{i}] (source={source} chunk_id={chunk_id})\n{text}"
        )
    
    return "\n".join(context_parts)
