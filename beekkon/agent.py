"""
BeekKon Bridge - High-Level Agent API
Simple interface for creating AI agents with automatic discovery, authentication, and communication
"""

import asyncio
import threading
import time
from typing import Dict, List, Callable, Any, Optional
from .auth import BeekKonAuth
from .discovery import BeekKonDiscovery, PeerInfo
from .protocol import BeekKonProtocol, BeekKonServer
from .models import BeekKonMessage


class BeekKonAgent:
    """
    High-level API for creating AI agents
    
    Example:
        agent = BeekKonAgent(
            name="agent_comptable",
            secret="my-super-secret-12345678901234567890",
            capabilities=["parse_invoice", "calculate_vat"]
        )
        
        @agent.handler("validate_contract")
        async def handle_validation(data):
            return {"status": "approved"}
        
        agent.start()  # Starts discovery, auth, and listening
    """
    
    def __init__(
        self,
        name: str,
        secret: str,
        capabilities: List[str],
        port: int = 8765,
        host: str = "0.0.0.0"
    ):
        """
        Initialize a BeekKon agent
        
        Args:
            name: Agent name (public identifier)
            secret: Master secret (min 32 chars, NEVER share)
            capabilities: List of agent capabilities
            port: Port to listen on
            host: Host to bind to
        """
        self.name = name
        self.secret = secret
        self.capabilities = capabilities
        self.port = port
        self.host = host
        
        # Initialize components
        self.auth = BeekKonAuth(name, secret)
        self.discovery = BeekKonDiscovery(
            agent_id=name,
            capabilities=capabilities,
            port=port,
            public_key_sign=self.auth.verify_key.encode().hex(),
            public_key_exchange=self.auth.public_key.encode().hex()
        )
        self.server = BeekKonServer(self.auth, host=host, port=port)
        
        # State
        self.handlers: Dict[str, Callable] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.connections: Dict[str, BeekKonProtocol] = {}
    
    def authorize_agent(self, agent_name: str, agent_secret: str) -> None:
        """
        Authorize a remote agent (server-side only)
        Call this before start() for each agent you want to accept
        
        Args:
            agent_name: Remote agent's name
            agent_secret: Remote agent's master secret (used to derive user_id)
        """
        temp_auth = BeekKonAuth(agent_name, agent_secret)
        self.auth.add_authorized_agent(agent_name, temp_auth.user_id)
    
    def handler(self, task_name: str):
        """
        Decorator to register a handler for a task
        
        Example:
            @agent.handler("parse_invoice")
            async def handle_parse(data):
                return {"result": "parsed"}
        """
        def decorator(func: Callable):
            self.handlers[task_name] = func
            return func
        return decorator
    
    async def _handle_connection(self, protocol: BeekKonProtocol):
        """Handle a new incoming connection"""
        peer_id = protocol.peer_agent_id
        self.connections[peer_id] = protocol
        
        # Register request handler
        async def handle_request(msg):
            task = msg.payload.get("task")
            data = msg.payload.get("data", {})
            
            handler = self.handlers.get(task)
            if handler:
                try:
                    result = await handler(data) if asyncio.iscoroutinefunction(handler) else handler(data)
                    await protocol.send_response(
                        request_id=msg.id,
                        success=True,
                        data=result if isinstance(result, dict) else {"result": result}
                    )
                except Exception as e:
                    await protocol.send_response(
                        request_id=msg.id,
                        success=False,
                        error=str(e)
                    )
            else:
                await protocol.send_response(
                    request_id=msg.id,
                    success=False,
                    error=f"Unknown task: {task}"
                )
        
        protocol.register_handler("request", handle_request)
        
        # Start listening
        await protocol.listen()
    
    async def _run_async(self):
        """Async main loop"""
        self._loop = asyncio.get_running_loop()
        
        # Register connection handler
        self.server.on_connection(self._handle_connection)
        
        # Start server
        await self.server.start()
        
        # Start discovery
        self.discovery.start()
        
        print(f"🤖 Agent '{self.name}' started")
        print(f"   Capabilities: {self.capabilities}")
        print(f"   Port: {self.port}")
        
        # Keep running
        while self._running:
            await asyncio.sleep(0.1)
        
        # Cleanup
        self.discovery.stop()
        await self.server.stop()
    
    def start(self, blocking: bool = True):
        """
        Start the agent
        
        Args:
            blocking: If True, blocks the main thread. If False, runs in background thread.
        """
        self._running = True
        
        if blocking:
            asyncio.run(self._run_async())
        else:
            self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
            self._thread.start()
            time.sleep(0.5)  # Wait for startup
    
    def _run_in_thread(self):
        """Run async loop in background thread"""
        asyncio.run(self._run_async())
    
    def stop(self):
        """Stop the agent"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def get_peers(self, capability: Optional[str] = None) -> List[PeerInfo]:
        """Get discovered peers"""
        return self.discovery.get_peers(capability=capability)
    
    async def _request_async(self, target: str, task: str, data: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Async request to another agent"""
        peer = self.discovery.get_peer(target)
        if not peer:
            raise ValueError(f"Peer '{target}' not found")
        
        protocol = BeekKonProtocol(self.auth)
        listen_task = None
        
        try:
            # Connect to peer
            success = await protocol.connect(peer.ip, peer.port)
            if not success:
                raise ConnectionError(f"Failed to connect to {target}")
            
            # CRITICAL: Start listening in background to receive the response
            listen_task = asyncio.create_task(protocol.listen())
            await asyncio.sleep(0.1)  # Let listen() start
            
            # Send request and wait for response
            response = await protocol.send_request(target, task, data, timeout)
            return response.payload
        
        finally:
            # Cleanup
            if listen_task:
                listen_task.cancel()
                try:
                    await listen_task
                except asyncio.CancelledError:
                    pass
            await protocol.close()
    
    def request(self, target: str, task: str, data: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """
        Send a request to another agent (synchronous)
        
        Args:
            target: Target agent name
            task: Task name
            data: Task data
            timeout: Response timeout
        
        Returns:
            Response data
        """
        if not self._loop:
            raise RuntimeError("Agent not started")
        
        future = asyncio.run_coroutine_threadsafe(
            self._request_async(target, task, data, timeout),
            self._loop
        )
        return future.result(timeout=timeout + 1)