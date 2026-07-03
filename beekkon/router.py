"""
BeekKon Bridge - Message Router
Handles routing of messages between agents
"""

from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
import asyncio
from .models import BeekKonMessage


@dataclass
class Route:
    """A routing rule"""
    pattern: str  # Message type or task pattern
    handler: Callable
    priority: int = 0  # Higher priority = checked first


class BeekKonRouter:
    """
    Message router for BeekKon agents
    
    Features:
    - Pattern-based routing
    - Priority-based matching
    - Middleware support
    - Async handlers
    """
    
    def __init__(self):
        self.routes: List[Route] = []
        self.middlewares: List[Callable] = []
        self._pending_requests: Dict[str, asyncio.Future] = {}
    
    def add_route(self, pattern: str, handler: Callable, priority: int = 0):
        """
        Add a routing rule
        
        Args:
            pattern: Message type or task pattern to match
            handler: Handler function (sync or async)
            priority: Priority (higher = checked first)
        """
        route = Route(pattern=pattern, handler=handler, priority=priority)
        self.routes.append(route)
        # Sort by priority (descending)
        self.routes.sort(key=lambda r: r.priority, reverse=True)
    
    def add_middleware(self, middleware: Callable):
        """
        Add a middleware function
        
        Middleware signature: async def middleware(message, next_handler)
        """
        self.middlewares.append(middleware)
    
    def register_request(self, request_id: str, future: asyncio.Future):
        """Register a pending request"""
        self._pending_requests[request_id] = future
    
    def resolve_request(self, request_id: str, response: BeekKonMessage):
        """Resolve a pending request with a response"""
        if request_id in self._pending_requests:
            self._pending_requests[request_id].set_result(response)
            del self._pending_requests[request_id]
    
    async def route(self, message: BeekKonMessage) -> Optional[BeekKonMessage]:
        """
        Route a message to the appropriate handler
        
        Args:
            message: Message to route
        
        Returns:
            Response message or None
        """
        # Check if it's a response to a pending request
        if message.type == "response":
            request_id = message.payload.get("request_id")
            if request_id and request_id in self._pending_requests:
                self.resolve_request(request_id, message)
                return None
        
        # Find matching route
        handler = None
        for route in self.routes:
            if self._matches(message, route.pattern):
                handler = route.handler
                break
        
        if not handler:
            return None
        
        # Apply middlewares
        async def final_handler(msg):
            if asyncio.iscoroutinefunction(handler):
                return await handler(msg)
            else:
                return handler(msg)
        
        current_handler = final_handler
        for middleware in reversed(self.middlewares):
            current_handler = self._wrap_middleware(middleware, current_handler)
        
        return await current_handler(message)
    
    def _matches(self, message: BeekKonMessage, pattern: str) -> bool:
        """Check if message matches pattern"""
        # Simple pattern matching
        if pattern == "*":
            return True
        
        if pattern == message.type:
            return True
        
        # Task-based matching for requests
        if message.type == "request":
            task = message.payload.get("task", "")
            if pattern == task:
                return True
        
        return False
    
    def _wrap_middleware(self, middleware: Callable, next_handler: Callable) -> Callable:
        """Wrap a handler with middleware"""
        async def wrapped(message: BeekKonMessage):
            async def call_next(msg):
                return await next_handler(msg)
            
            if asyncio.iscoroutinefunction(middleware):
                return await middleware(message, call_next)
            else:
                return middleware(message, call_next)
        
        return wrapped