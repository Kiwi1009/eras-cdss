"""Citation validation and repair logic."""
from typing import List, Dict, Any, Tuple


def validate_citations(
    citations: List[Dict[str, str]],
    hits: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    Validate that citations reference valid hits.
    
    Args:
        citations: List of citation dicts with 'source' and 'chunk_id'
        hits: List of retrieval hits with 'source' and 'chunk_id'
        
    Returns:
        (ok, errors) - ok is True if all citations are valid
    """
    if not citations:
        return False, ["At least one citation is required"]
    
    # Build set of valid (source, chunk_id) pairs
    valid_pairs = {(hit["source"], hit["chunk_id"]) for hit in hits}
    
    errors = []
    for i, cit in enumerate(citations):
        if "source" not in cit or "chunk_id" not in cit:
            errors.append(f"Citation {i} missing source or chunk_id")
            continue
        
        pair = (cit["source"], cit["chunk_id"])
        if pair not in valid_pairs:
            errors.append(
                f"Citation {i} references invalid hit: source={cit['source']}, "
                f"chunk_id={cit['chunk_id']}"
            )
    
    ok = len(errors) == 0
    return ok, errors


def build_repair_prompt(
    original_task: str,
    hits: List[Dict[str, Any]],
    schema_json: str
) -> str:
    """
    Build repair prompt for S2 retry.
    
    Args:
        original_task: Original task prompt
        hits: Available retrieval hits
        schema_json: JSON schema string
        
    Returns:
        Repair prompt string
    """
    # Format hits list
    hits_list = []
    for i, hit in enumerate(hits):
        hits_list.append(
            f"  {i+1}. source={hit['source']}, chunk_id={hit['chunk_id']}, "
            f"text={hit['text'][:100]}..."
        )
    hits_text = "\n".join(hits_list)
    
    repair_prompt = f"""Your previous response did not meet the requirements. Please fix it.

REQUIREMENTS:
1. Output must be valid JSON matching this schema:
{schema_json}

2. You MUST include at least one citation from the following available hits:
{hits_text}

3. Each citation must have both "source" and "chunk_id" matching exactly one of the hits above.

ORIGINAL TASK:
{original_task}

Please provide a corrected response that follows the schema and uses valid citations from the hits list above."""
    
    return repair_prompt
