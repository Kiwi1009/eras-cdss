"""Trace logging for requests and responses."""
import json
import os
from datetime import datetime
from typing import Dict, Any
import uuid
from app.config import settings


def new_trace_id() -> str:
    """Generate a new trace ID."""
    return f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


class TraceLogger:
    """Trace logger for request/response tracking."""
    
    def __init__(self, trace_root: str = None):
        self.trace_root = trace_root or settings.TRACE_ROOT
        os.makedirs(self.trace_root, exist_ok=True)
    
    def write(self, trace_id: str, payload: Dict[str, Any]) -> str:
        """
        Write trace payload to file.
        
        Args:
            trace_id: Trace identifier
            payload: Trace data (request, hits, agents, arbiter, response, etc.)
            
        Returns:
            Path to trace file
        """
        if not settings.TRACE_ENABLED:
            return ""
        
        trace_file = os.path.join(self.trace_root, f"{trace_id}.json")
        
        # Add timestamp
        payload["timestamp"] = datetime.now().isoformat()
        payload["trace_id"] = trace_id
        
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        return trace_file


# Global trace logger instance
trace_logger = TraceLogger()
