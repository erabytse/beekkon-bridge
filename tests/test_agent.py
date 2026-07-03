"""
Unit tests for BeekKonAgent
"""

import pytest
import time
from beekkon.agent import BeekKonAgent


class TestBeekKonAgent:
    def test_agent_creation(self):
        """Test agent initialization"""
        agent = BeekKonAgent(
            name="test_agent",
            secret="test-secret-12345678901234567890",
            capabilities=["test_cap"]
        )
        assert agent.name == "test_agent"
        assert "test_cap" in agent.capabilities
    
    def test_handler_decorator(self):
        """Test handler registration"""
        agent = BeekKonAgent(
            name="test_agent",
            secret="test-secret-12345678901234567890",
            capabilities=[]
        )
        
        @agent.handler("test_task")
        async def handle_test(data):
            return {"result": "ok"}
        
        assert "test_task" in agent.handlers
    
    def test_authorize_agent(self):
        """Test agent authorization"""
        agent = BeekKonAgent(
            name="server_agent",
            secret="server-secret-12345678901234567890",
            capabilities=[]
        )
        
        agent.authorize_agent("client_agent", "client-secret-0987654321098765432109")
        
        # Check that client is authorized
        client_auth = agent.auth.authorized_agents.get("client_agent")
        assert client_auth is not None