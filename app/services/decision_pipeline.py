"""Decision pipeline integrating all components."""
import asyncio
import time
import json
from typing import Dict, Any, List
from app.schemas import ERASRequest, ERASResponse, Citation
from app.services.scenario_router import infer_scenario, Scenario
from app.services.input_validator import validate_inputs
from app.services.retriever_hybrid import HybridRetriever
from app.services.retrieval_postproc import filter_and_dedupe_hits, format_hits_context
from app.services.schema_guard import parse_agent_decision, parse_arbiter_decision, AgentDecision, ArbiterDecision
from app.services.citation_guard import validate_citations, build_repair_prompt
from app.services.llm.factory import get_llm_backend
from app.services.llm.base import LLMGenConfig
from app.services.trace_logger import trace_logger, new_trace_id


# Agent schemas as JSON strings
AGENT_SCHEMA_JSON = json.dumps({
    "type": "object",
    "properties": {
        "recommendation": {"type": "string"},
        "actions": {"type": "array", "items": {"type": "string"}},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "chunk_id": {"type": "string"}
                },
                "required": ["source", "chunk_id"]
            }
        }
    },
    "required": ["recommendation", "citations"]
}, indent=2)

ARBITER_SCHEMA_JSON = json.dumps({
    "type": "object",
    "properties": {
        "final_recommendation": {"type": "string"},
        "final_actions": {"type": "array", "items": {"type": "string"}},
        "key_reasons": {"type": "array", "items": {"type": "string"}},
        "risks_and_notes": {"type": "array", "items": {"type": "string"}},
        "conflicts": {"type": "array", "items": {"type": "string"}},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "chunk_id": {"type": "string"}
                },
                "required": ["source", "chunk_id"]
            }
        }
    },
    "required": ["final_recommendation", "citations"]
}, indent=2)


def build_agent_prompt(
    agent_name: str,
    scenario: Scenario,
    question: str,
    patient_fhir: Dict[str, Any],
    hits_context: str
) -> str:
    """Build prompt for agent."""
    prompt = f"""You are a {agent_name} providing clinical decision support for ERAS (Enhanced Recovery After Surgery).

SCENARIO: {scenario.value}
CLINICAL QUESTION: {question}

PATIENT DATA:
{json.dumps(patient_fhir, indent=2)}

EVIDENCE CONTEXT:
{hits_context}

TASK:
Analyze the patient data and evidence to provide a recommendation. You MUST:
1. Output a single valid JSON object matching this schema:
{AGENT_SCHEMA_JSON}

2. Include at least one citation from the evidence context above. Each citation must have "source" and "chunk_id" matching exactly one entry in the evidence.

3. Provide clear recommendation, actions, reasons, and risks.

Output only the JSON object, no additional text."""
    return prompt


def build_arbiter_prompt(
    scenario: Scenario,
    question: str,
    patient_fhir: Dict[str, Any],
    hits_context: str,
    agent_decisions: List[Dict[str, Any]]
) -> str:
    """Build prompt for arbiter."""
    agents_text = "\n".join([
        f"\n[{i+1}] {agent['name']}:\n{json.dumps(agent['decision'], indent=2)}"
        for i, agent in enumerate(agent_decisions)
    ])
    
    prompt = f"""You are an ARBITER synthesizing multiple clinical expert opinions for ERAS decision support.

SCENARIO: {scenario.value}
CLINICAL QUESTION: {question}

PATIENT DATA:
{json.dumps(patient_fhir, indent=2)}

EVIDENCE CONTEXT:
{hits_context}

AGENT DECISIONS:
{agents_text}

TASK:
Synthesize the agent decisions into a final recommendation. You MUST:
1. Output a single valid JSON object matching this schema:
{ARBITER_SCHEMA_JSON}

2. Include at least one citation from the evidence context above. Each citation must have "source" and "chunk_id" matching exactly one entry in the evidence.

3. Identify any conflicts between agents in the "conflicts" field.

4. Provide final recommendation, actions, reasons, and risks.

Output only the JSON object, no additional text."""
    return prompt


async def generate_agent_decision(
    agent_name: str,
    prompt: str,
    hits: List[Dict[str, Any]],
    retry: bool = True
) -> tuple[Dict[str, Any], str]:
    """
    Generate agent decision with S2 repair if needed.
    
    Returns:
        (agent_dict, error_message) - error_message is None if successful
    """
    llm = get_llm_backend()
    config = LLMGenConfig(temperature=0.2, max_tokens=900)
    
    # First attempt
    result = await llm.generate(prompt, config)
    
    if result.error:
        return {
            "name": agent_name,
            "decision": {
                "recommendation": f"Error: {result.error}",
                "actions": [],
                "reasons": [],
                "risks": [f"LLM error: {result.error}"],
                "citations": []
            },
            "error": result.error
        }, result.error
    
    # Parse decision
    decision, parse_error = parse_agent_decision(result.text)
    
    if decision is None:
        if not retry:
            # Return conservative decision
            return {
                "name": agent_name,
                "decision": {
                    "recommendation": "Unable to parse decision. Manual review required.",
                    "actions": [],
                    "reasons": [],
                    "risks": [f"Parse error: {parse_error}"],
                    "citations": []
                },
                "error": parse_error
            }, parse_error
        
        # S2: Repair and retry
        repair_prompt = build_repair_prompt(prompt, hits, AGENT_SCHEMA_JSON)
        result2 = await llm.generate(repair_prompt, config)
        
        if result2.error:
            return {
                "name": agent_name,
                "decision": {
                    "recommendation": f"Error on retry: {result2.error}",
                    "actions": [],
                    "reasons": [],
                    "risks": [f"LLM error (retry): {result2.error}"],
                    "citations": []
                },
                "error": result2.error
            }, result2.error
        
        decision, parse_error2 = parse_agent_decision(result2.text)
        if decision is None:
            return {
                "name": agent_name,
                "decision": {
                    "recommendation": "Unable to parse decision after repair. Manual review required.",
                    "actions": [],
                    "reasons": [],
                    "risks": [f"Parse error (retry): {parse_error2}"],
                    "citations": []
                },
                "error": parse_error2
            }, parse_error2
    
    # Validate citations
    citations = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in decision.citations]
    cit_ok, cit_errors = validate_citations(citations, hits)
    
    if not cit_ok:
        if not retry:
            # Return with invalid citations (but still return decision)
            return {
                "name": agent_name,
                "decision": decision.dict(),
                "error": f"Citation validation failed: {', '.join(cit_errors)}"
            }, f"Citation errors: {', '.join(cit_errors)}"
        
        # S2: Repair citations
        repair_prompt = build_repair_prompt(prompt, hits, AGENT_SCHEMA_JSON)
        result2 = await llm.generate(repair_prompt, config)
        
        if result2.error:
            return {
                "name": agent_name,
                "decision": decision.dict(),
                "error": f"Citation repair failed: {result2.error}"
            }, result2.error
        
        decision2, parse_error2 = parse_agent_decision(result2.text)
        if decision2 is None:
            return {
                "name": agent_name,
                "decision": decision.dict(),
                "error": f"Citation repair parse failed: {parse_error2}"
            }, parse_error2
        
        citations2 = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in decision2.citations]
        cit_ok2, cit_errors2 = validate_citations(citations2, hits)
        if not cit_ok2:
            return {
                "name": agent_name,
                "decision": decision2.dict(),
                "error": f"Citation validation still failed: {', '.join(cit_errors2)}"
            }, f"Citation errors (retry): {', '.join(cit_errors2)}"
        
        decision = decision2
    
    return {
        "name": agent_name,
        "decision": decision.dict(),
        "error": None
    }, None


async def generate_arbiter_decision(
    prompt: str,
    hits: List[Dict[str, Any]],
    retry: bool = True
) -> tuple[Dict[str, Any], str]:
    """
    Generate arbiter decision with S2 repair if needed.
    
    Returns:
        (arbiter_dict, error_message) - error_message is None if successful
    """
    llm = get_llm_backend()
    config = LLMGenConfig(temperature=0.2, max_tokens=900)
    
    # First attempt
    result = await llm.generate(prompt, config)
    
    if result.error:
        return {
            "decision": {
                "final_recommendation": f"Error: {result.error}",
                "final_actions": [],
                "key_reasons": [],
                "risks_and_notes": [f"LLM error: {result.error}"],
                "conflicts": [],
                "citations": []
            },
            "error": result.error
        }, result.error
    
    # Parse decision
    decision, parse_error = parse_arbiter_decision(result.text)
    
    if decision is None:
        if not retry:
            return {
                "decision": {
                    "final_recommendation": "Unable to parse arbiter decision. Manual review required.",
                    "final_actions": [],
                    "key_reasons": [],
                    "risks_and_notes": [f"Parse error: {parse_error}"],
                    "conflicts": [],
                    "citations": []
                },
                "error": parse_error
            }, parse_error
        
        # S2: Repair and retry
        repair_prompt = build_repair_prompt(prompt, hits, ARBITER_SCHEMA_JSON)
        result2 = await llm.generate(repair_prompt, config)
        
        if result2.error:
            return {
                "decision": {
                    "final_recommendation": f"Error on retry: {result2.error}",
                    "final_actions": [],
                    "key_reasons": [],
                    "risks_and_notes": [f"LLM error (retry): {result2.error}"],
                    "conflicts": [],
                    "citations": []
                },
                "error": result2.error
            }, result2.error
        
        decision, parse_error2 = parse_arbiter_decision(result2.text)
        if decision is None:
            return {
                "decision": {
                    "final_recommendation": "Unable to parse arbiter decision after repair. Manual review required.",
                    "final_actions": [],
                    "key_reasons": [],
                    "risks_and_notes": [f"Parse error (retry): {parse_error2}"],
                    "conflicts": [],
                    "citations": []
                },
                "error": parse_error2
            }, parse_error2
    
    # Validate citations
    citations = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in decision.citations]
    cit_ok, cit_errors = validate_citations(citations, hits)
    
    if not cit_ok:
        if not retry:
            return {
                "decision": decision.dict(),
                "error": f"Citation validation failed: {', '.join(cit_errors)}"
            }, f"Citation errors: {', '.join(cit_errors)}"
        
        # S2: Repair citations
        repair_prompt = build_repair_prompt(prompt, hits, ARBITER_SCHEMA_JSON)
        result2 = await llm.generate(repair_prompt, config)
        
        if result2.error:
            return {
                "decision": decision.dict(),
                "error": f"Citation repair failed: {result2.error}"
            }, result2.error
        
        decision2, parse_error2 = parse_arbiter_decision(result2.text)
        if decision2 is None:
            return {
                "decision": decision.dict(),
                "error": f"Citation repair parse failed: {parse_error2}"
            }, parse_error2
        
        citations2 = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in decision2.citations]
        cit_ok2, cit_errors2 = validate_citations(citations2, hits)
        if not cit_ok2:
            return {
                "decision": decision2.dict(),
                "error": f"Citation validation still failed: {', '.join(cit_errors2)}"
            }, f"Citation errors (retry): {', '.join(cit_errors2)}"
        
        decision = decision2
    
    return {
        "decision": decision.dict(),
        "error": None
    }, None


async def run_decision(req: ERASRequest) -> Dict[str, Any]:
    """
    Run decision pipeline.
    
    Returns:
        Dict matching ERASResponse schema
    """
    start_time = time.time()
    trace_id = new_trace_id()
    
    # Initialize retriever
    retriever = HybridRetriever()
    
    # Step 1: Infer scenario
    scenario = infer_scenario(req.scenario, req.question, req.patient_fhir)
    
    # Step 2: Validate inputs
    validation = validate_inputs(scenario, req.patient_fhir)
    if not validation.ok:
        latency_ms = int((time.time() - start_time) * 1000)
        response = {
            "final_recommendation": "INSUFFICIENT_DATA",
            "final_actions": [],
            "key_reasons": [],
            "risks_and_notes": validation.errors,
            "missing_data": validation.missing,
            "conflicts": [],
            "citations": [],
            "agents": [],
            "metrics": {
                "latency_ms": latency_ms,
                "trace_id": trace_id,
                "scenario": scenario.value,
                "backend": get_llm_backend().name,
                "errors": validation.errors
            }
        }
        
        # Trace
        trace_logger.write(trace_id, {
            "request": req.dict(),
            "scenario": scenario.value,
            "validation": validation.dict(),
            "response": response
        })
        
        return response
    
    # Step 3: Retrieve hits
    hits = retriever.retrieve(req.question, k=req.top_k)
    
    if not hits:
        latency_ms = int((time.time() - start_time) * 1000)
        response = {
            "final_recommendation": "NEEDS_REVIEW",
            "final_actions": [],
            "key_reasons": ["No relevant evidence found in RAG store"],
            "risks_and_notes": [],
            "missing_data": [],
            "conflicts": [],
            "citations": [],
            "agents": [],
            "metrics": {
                "latency_ms": latency_ms,
                "trace_id": trace_id,
                "scenario": scenario.value,
                "backend": get_llm_backend().name,
                "errors": ["No retrieval hits"]
            }
        }
        
        trace_logger.write(trace_id, {
            "request": req.dict(),
            "scenario": scenario.value,
            "hits": [],
            "response": response
        })
        
        return response
    
    # Step 4: Post-process hits
    hits = filter_and_dedupe_hits(hits, min_chars=120, per_source_cap=3)
    hits_context = format_hits_context(hits)
    
    # Step 5: Generate agent decisions in parallel
    agent_names = ["SURGEON", "ANESTHESIOLOGIST", "NURSE"]
    agent_prompts = [
        build_agent_prompt(name, scenario, req.question, req.patient_fhir, hits_context)
        for name in agent_names
    ]
    
    agent_tasks = [
        generate_agent_decision(name, prompt, hits, retry=True)
        for name, prompt in zip(agent_names, agent_prompts)
    ]
    
    agent_results = await asyncio.gather(*agent_tasks)
    agent_decisions = [result[0] for result in agent_results]
    agent_errors = [result[1] for result in agent_results]
    
    # Step 6: Generate arbiter decision
    arbiter_prompt = build_arbiter_prompt(
        scenario, req.question, req.patient_fhir, hits_context, agent_decisions
    )
    arbiter_result, arbiter_error = await generate_arbiter_decision(arbiter_prompt, hits, retry=True)
    
    # Step 7: Build response
    arbiter_decision = arbiter_result["decision"]
    
    # Map citations to full text
    citations_with_text = []
    for cit in arbiter_decision.get("citations", []):
        # Find matching hit
        matching_hit = next(
            (h for h in hits if h["source"] == cit["source"] and h["chunk_id"] == cit["chunk_id"]),
            None
        )
        if matching_hit:
            citations_with_text.append(Citation(
                source=cit["source"],
                chunk_id=cit["chunk_id"],
                text=matching_hit["text"]
            ))
        else:
            # Fallback: use citation without text
            citations_with_text.append(Citation(
                source=cit["source"],
                chunk_id=cit["chunk_id"],
                text="[Text not found]"
            ))
    
    # Ensure at least one citation
    if not citations_with_text and hits:
        # Use first hit as fallback citation
        first_hit = hits[0]
        citations_with_text.append(Citation(
            source=first_hit["source"],
            chunk_id=first_hit["chunk_id"],
            text=first_hit["text"]
        ))
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    all_errors = [e for e in agent_errors if e] + ([arbiter_error] if arbiter_error else [])
    
    response = {
        "final_recommendation": arbiter_decision.get("final_recommendation", "No recommendation"),
        "final_actions": arbiter_decision.get("final_actions", []),
        "key_reasons": arbiter_decision.get("key_reasons", []),
        "risks_and_notes": arbiter_decision.get("risks_and_notes", []),
        "missing_data": [],
        "conflicts": arbiter_decision.get("conflicts", []),
        "citations": [c.dict() for c in citations_with_text],
        "agents": agent_decisions,
        "metrics": {
            "latency_ms": latency_ms,
            "trace_id": trace_id,
            "scenario": scenario.value,
            "backend": get_llm_backend().name,
            "errors": all_errors,
            "citations_count": len(citations_with_text),
            "hits_count": len(hits)
        }
    }
    
    # Step 8: Trace
    trace_logger.write(trace_id, {
        "request": req.dict(),
        "scenario": scenario.value,
        "hits": hits,
        "agents": agent_decisions,
        "arbiter": arbiter_result,
        "response": response
    })
    
    return response
