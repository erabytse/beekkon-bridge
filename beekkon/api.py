"""
BeekKon Bridge - REST API (Optional)
HTTP API for remote access to BeekKon agents
"""

from typing import Dict, Any, Optional
from .agent import BeekKonAgent
import json


class BeekKonAPI:
    """
    REST API wrapper for BeekKon agents
    
    NOTE: This is a placeholder for future HTTP API support.
    Currently, agents communicate via TCP protocol only.
    
    Future features:
    - HTTP endpoints for remote control
    - WebSocket for real-time events
    - Authentication tokens
    - Rate limiting
    """
    
    def __init__(self, agent: BeekKonAgent, host: str = "0.0.0.0", port: int = 8080):
        """
        Initialize API server
        
        Args:
            agent: BeekKonAgent instance
            host: Host to bind to
            port: Port to listen on
        """
        self.agent = agent
        self.host = host
        self.port = port
        
        # TODO: Implement HTTP server (Flask/FastAPI)
        print(f"⚠️  BeekKonAPI is a placeholder. HTTP API not yet implemented.")
        print(f"   Use agent.request() for TCP communication.")
    
    def start(self):
        """Start API server (placeholder)"""
        print(f"🌐 API server would start on {self.host}:{self.port}")
        print(f"   Endpoints:")
        print(f"   - POST /request {{target, task, data}}")
        print(f"   - GET /peers")
        print(f"   - GET /status")
    
    def stop(self):
        """Stop API server (placeholder)"""
        print(f"🌐 API server stopped")