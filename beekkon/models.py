"""
BeekKon Bridge - Message Models
Defines the structure of messages exchanged between agents
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
from enum import Enum
import time
import uuid


class MessageType(str, Enum):
    """Types of messages in BeekKon protocol"""
    HELLO = "hello"              # Handshake initiation
    CHALLENGE = "challenge"      # Auth challenge
    RESPONSE = "response"        # Auth response
    ACK = "ack"                  # Handshake acknowledgment
    REQUEST = "request"          # Service request
    RESPONSE_MSG = "response"    # Service response
    EVENT = "event"              # Asynchronous event
    ERROR = "error"              # Error message


@dataclass
class BeekKonMessage:
    """
    Base message structure for BeekKon protocol
    
    All messages follow this format:
    - version: Protocol version (for compatibility)
    - type: Message type (hello, request, response, etc.)
    - id: Unique message ID (UUID v4)
    - timestamp: Unix timestamp
    - source: Sender agent ID
    - target: Receiver agent ID (or "*" for broadcast)
    - payload: Message content (task-specific)
    - signature: Ed25519 signature of the message (hex)
    - ttl: Time-to-live in seconds (default: 3600)
    """
    type: str
    source: str
    target: str = "*"
    payload: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: int = field(default_factory=lambda: int(time.time()))
    signature: str = ""
    ttl: int = 3600
    
    def to_dict(self) -> dict:
        """Convert message to dictionary"""
        return asdict(self)
    
    def to_signable_bytes(self) -> bytes:
        """
        Get the bytes to sign (excludes signature field itself)
        This ensures signature integrity
        """
        data = self.to_dict()
        data.pop("signature", None)  # Remove signature before signing
        # Sort keys for deterministic serialization
        import json
        return json.dumps(data, sort_keys=True).encode('utf-8')
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BeekKonMessage':
        """Create message from dictionary"""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        return (time.time() - self.timestamp) > self.ttl


@dataclass
class RequestPayload:
    """Payload for request messages"""
    task: str
    data: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30  # seconds


@dataclass
class ResponsePayload:
    """Payload for response messages"""
    request_id: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ErrorPayload:
    """Payload for error messages"""
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


# Error codes
class ErrorCode:
    """Standard error codes"""
    AUTH_FAILED = "AUTH_FAILED"
    UNKNOWN_TASK = "UNKNOWN_TASK"
    TIMEOUT = "TIMEOUT"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    PEER_NOT_FOUND = "PEER_NOT_FOUND"