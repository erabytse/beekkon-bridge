"""
BeekKon Bridge - TCP Protocol Transport
Handles secure TCP connections with MessagePack serialization
"""

import asyncio
import struct
import time
from typing import Optional, Callable, Dict, Any, Tuple
import msgpack
from .auth import BeekKonAuth
from .models import BeekKonMessage, MessageType


# Protocol constants
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB max
HANDSHAKE_TIMEOUT = 10.0  # seconds
MESSAGE_TIMEOUT = 30.0  # seconds


class BeekKonProtocol:
    """
    TCP protocol handler for BeekKon Bridge
    
    Message frame format:
    [4 bytes: message length (uint32, big-endian)] [N bytes: MessagePack data]
    """
    
    def __init__(self, auth: BeekKonAuth):
        """
        Initialize protocol handler
        
        Args:
            auth: BeekKonAuth instance for encryption/signing
        """
        self.auth = auth
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.peer_agent_id: Optional[str] = None
        self.connected = False
        self._message_handlers: Dict[str, Callable] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
    
    async def connect(self, host: str, port: int, timeout: float = HANDSHAKE_TIMEOUT) -> bool:
        """
        Connect to a peer and perform handshake
        
        Args:
            host: Peer IP address
            port: Peer port
            timeout: Connection timeout in seconds
        
        Returns:
            True if connection and handshake successful
        """
        try:
            # Connect TCP
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            
            # Perform handshake
            success = await self._client_handshake(timeout)
            if not success:
                await self.close()
                return False
            
            self.connected = True
            return True
        
        except Exception as e:
            print(f"Connection failed: {e}")
            await self.close()
            return False
    
    async def _client_handshake(self, timeout: float) -> bool:
        """Client-side handshake"""
        try:
            print(f"[DEBUG] Client handshake started")

            # Step 1: Send HELLO
            hello_data = self.auth.initiate_handshake()
            hello_msg = BeekKonMessage(
                type=MessageType.HELLO.value,
                source=self.auth.agent_id,
                target="*",
                payload=hello_data
            )
            await self._send_raw(hello_msg)
            print(f"[DEBUG] Sent HELLO as {self.auth.agent_id}")

            
            # Step 2: Receive CHALLENGE
            challenge_msg = await asyncio.wait_for(
                self._receive_raw(),
                timeout=timeout
            )
            print(f"[DEBUG] Received CHALLENGE")
            
            if challenge_msg.type != MessageType.CHALLENGE.value:
                return False
            
            # CRITICAL: Store server's verify key from CHALLENGE
            if "public_key_sign" in challenge_msg.payload:
                from nacl.signing import VerifyKey
                self.auth.peer_verify_key = VerifyKey(
                    bytes.fromhex(challenge_msg.payload["public_key_sign"])
                )
            
            # Step 3: Send RESPONSE
            challenge_id = challenge_msg.payload["challenge_id"]
            nonce = challenge_msg.payload["nonce"]
            response_data = self.auth.respond_to_challenge(challenge_id, nonce)
            
            response_msg = BeekKonMessage(
                type=MessageType.RESPONSE.value,
                source=self.auth.agent_id,
                target=challenge_msg.source,
                payload=response_data
            )
            await self._send_raw(response_msg)
            
            # Step 4: Receive ACK
            ack_msg = await asyncio.wait_for(
                self._receive_raw(),
                timeout=timeout
            )
            if ack_msg.type != MessageType.ACK.value:
                return False
            
            # Step 5: Establish session
            peer_public_key = ack_msg.payload["public_key_exchange"]
            if not self.auth.establish_session(peer_public_key):
                return False
            
            self.peer_agent_id = ack_msg.source
            return True
        
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            print(f"Handshake failed: {e}")
            return False


    async def _server_handshake(self, timeout: float) -> bool:
        """Server-side handshake"""
        try:
            print(f"[DEBUG] Server handshake started with {self.writer.get_extra_info('peername')}")

            # Step 1: Receive HELLO
            hello_msg = await asyncio.wait_for(
                self._receive_raw(),
                timeout=timeout
            )
            print(f"[DEBUG] Received HELLO from: {hello_msg.source}")

            if hello_msg.type != MessageType.HELLO.value:
                print(f"[DEBUG] ERROR: Not a HELLO message, type={hello_msg.type}")
                return False
            
            # Step 2: Send CHALLENGE with our public_key_sign
            challenge_id, nonce = self.auth.generate_challenge()
            challenge_msg = BeekKonMessage(
                type=MessageType.CHALLENGE.value,
                source=self.auth.agent_id,
                target=hello_msg.source,
                payload={
                    "challenge_id": challenge_id,
                    "nonce": nonce,
                    "public_key_sign": self.auth.verify_key.encode().hex()
                }
            )
            await self._send_raw(challenge_msg)
            print(f"[DEBUG] Sent CHALLENGE to {hello_msg.source}")

            # Step 3: Receive RESPONSE
            response_msg = await asyncio.wait_for(
                self._receive_raw(),
                timeout=timeout
            )
            print(f"[DEBUG] Received RESPONSE from: {response_msg.source}")

            if response_msg.type != MessageType.RESPONSE.value:
                print(f"[DEBUG] ERROR: Not a RESPONSE message")
                return False
            
            # CRITICAL: Store client's verify key from RESPONSE
            if "public_key_sign" in response_msg.payload:
                from nacl.signing import VerifyKey
                self.auth.peer_verify_key = VerifyKey(
                    bytes.fromhex(response_msg.payload["public_key_sign"])
                )
            
            # Verify response
            peer_agent_id = hello_msg.source
            print(f"[DEBUG] Verifying agent: {peer_agent_id}")
            print(f"[DEBUG] Authorized agents: {list(self.auth.authorized_agents.keys())}")

            if not self.auth.verify_response(response_msg.payload, nonce, peer_agent_id):
                print(f"[DEBUG] ERROR: Verification failed for {peer_agent_id}")
                return False
            
            print(f"[DEBUG] Verification successful!")

            # Step 4: Send ACK
            ack_msg = BeekKonMessage(
                type=MessageType.ACK.value,
                source=self.auth.agent_id,
                target=hello_msg.source,
                payload={
                    "public_key_exchange": self.auth.public_key.encode().hex()
                }
            )
            await self._send_raw(ack_msg)
            
            # Step 5: Establish session
            peer_public_key = response_msg.payload["public_key_exchange"]
            if not self.auth.establish_session(peer_public_key):
                return False
            
            self.peer_agent_id = hello_msg.source
            return True
        
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            print(f"Server handshake failed: {e}")
            return False
        
    async def _send_raw(self, message: BeekKonMessage) -> None:
        """Send a message (unencrypted, for handshake)"""
        data = msgpack.packb(message.to_dict(), use_bin_type=True)
        
        if len(data) > MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {len(data)} > {MAX_MESSAGE_SIZE}")
        
        # Length prefix (4 bytes, big-endian)
        length_prefix = struct.pack('>I', len(data))
        self.writer.write(length_prefix + data)
        await self.writer.drain()
    
    async def _receive_raw(self) -> BeekKonMessage:
        """Receive a message (unencrypted, for handshake)"""
        # Read length prefix
        length_bytes = await self.reader.readexactly(4)
        length = struct.unpack('>I', length_bytes)[0]
        
        if length > MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {length} > {MAX_MESSAGE_SIZE}")
        
        # Read message data
        data = await self.reader.readexactly(length)
        msg_dict = msgpack.unpackb(data, raw=False)
        return BeekKonMessage.from_dict(msg_dict)
    
    async def send(self, message: BeekKonMessage) -> None:
        """
        Send an encrypted message
        
        Args:
            message: Message to send
        """
        if not self.connected:
            raise RuntimeError("Not connected")
        
        # Sign the message
        signable = message.to_signable_bytes()
        message.signature = self.auth.sign_message(signable)
        
        # Encrypt the message
        data = msgpack.packb(message.to_dict(), use_bin_type=True)
        encrypted = self.auth.encrypt(data)
        
        # Length prefix + encrypted data
        length_prefix = struct.pack('>I', len(encrypted))
        self.writer.write(length_prefix + encrypted)
        await self.writer.drain()
    
    async def receive(self, timeout: float = MESSAGE_TIMEOUT) -> Optional[BeekKonMessage]:
        """
        Receive an encrypted message
        
        Args:
            timeout: Receive timeout in seconds
        
        Returns:
            Received message or None if timeout/error
        """
        
        if not self.connected:
            return None
        
        try:
            # Read length prefix
            length_bytes = await asyncio.wait_for(
                self.reader.readexactly(4),
                timeout=timeout
            )
            length = struct.unpack('>I', length_bytes)[0]
            
            if length > MAX_MESSAGE_SIZE:
                raise ValueError(f"Message too large: {length}")
            
            # Read encrypted data
            encrypted = await asyncio.wait_for(
                self.reader.readexactly(length),
                timeout=timeout
            )
            
            # Decrypt
            data = self.auth.decrypt(encrypted)
            msg_dict = msgpack.unpackb(data, raw=False)
            message = BeekKonMessage.from_dict(msg_dict)
            
            # Verify signature
            if message.signature:
                signable = message.to_signable_bytes()
                if not self.auth.verify_peer_signature(signable, message.signature):
                    raise ValueError("Invalid message signature")
            
            # Check expiration
            if message.is_expired():
                raise ValueError("Message expired")
            
            return message
        
        except asyncio.TimeoutError:
            return None
        except asyncio.IncompleteReadError:
            # Peer closed connection - normal case
            self.connected = False
            return None
        except ConnectionResetError:
            # Peer reset connection - normal case
            self.connected = False
            return None
        except Exception as e:
            # Only log unexpected errors
            if self.connected:
                print(f"Receive error: {e}")
            self.connected = False
            return None
    
    async def send_request(self, target: str, task: str, data: Dict[str, Any], timeout: float = 30.0) -> BeekKonMessage:
        """
        Send a request and wait for response
        
        Args:
            target: Target agent ID
            task: Task name
            data: Task data
            timeout: Response timeout
        
        Returns:
            Response message
        """
        request_msg = BeekKonMessage(
            type=MessageType.REQUEST.value,  # Force string
            source=self.auth.agent_id,
            target=target,
            payload={"task": task, "data": data}
        )
        
        # Modern asyncio (Python 3.10+)
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_responses[request_msg.id] = future
        
        try:
            await self.send(request_msg)
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        finally:
            self._pending_responses.pop(request_msg.id, None)
  
    
    async def send_response(self, request_id: str, success: bool, data: Dict[str, Any] = None, error: str = None) -> None:
        """Send a response to a request"""
        response_msg = BeekKonMessage(
            type=MessageType.RESPONSE_MSG,
            source=self.auth.agent_id,
            target=self.peer_agent_id or "*",
            payload={
                "request_id": request_id,
                "success": success,
                "data": data or {},
                "error": error
            }
        )
        await self.send(response_msg)
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a message type (normalizes to string)"""
        # Normalize enum to string value
        key = message_type.value if hasattr(message_type, 'value') else str(message_type)
        self._message_handlers[key] = handler
    
    async def dispatch(self, message: BeekKonMessage) -> None:
        """Dispatch a message to the appropriate handler"""
        # Normalize incoming type
        msg_type = message.type.value if hasattr(message.type, 'value') else str(message.type)
        
        # Check if it's a response to a pending request
        if msg_type == MessageType.RESPONSE_MSG.value:
            request_id = message.payload.get("request_id")
            if request_id in self._pending_responses:
                self._pending_responses[request_id].set_result(message)
                return
        
        # Dispatch to registered handler
        handler = self._message_handlers.get(msg_type)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
    
    async def listen(self) -> None:
        """Listen for incoming messages and dispatch them"""
        while self.connected:
            message = await self.receive()
            if message is None:
                break
            await self.dispatch(message)
    
    async def close(self) -> None:
        """Close the connection"""
        self.connected = False
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.writer = None
        self.reader = None


class BeekKonServer:
    """
    TCP server for BeekKon Bridge
    Accepts incoming connections and performs handshake
    """
    
    def __init__(self, auth: BeekKonAuth, host: str = "0.0.0.0", port: int = 8765):
        self.auth = auth
        self.host = host
        self.port = port
        self.server: Optional[asyncio.AbstractServer] = None
        self.connections: Dict[str, BeekKonProtocol] = {}
        self._on_connection: Optional[Callable] = None
    
    def on_connection(self, callback: Callable) -> None:
        """Register callback for new connections"""
        self._on_connection = callback
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle a new client connection"""
        protocol = BeekKonProtocol(self.auth)
        protocol.reader = reader
        protocol.writer = writer
        
        try:
            # Perform server-side handshake
            success = await asyncio.wait_for(
                protocol._server_handshake(HANDSHAKE_TIMEOUT),
                timeout=HANDSHAKE_TIMEOUT + 1
            )
            
            if not success:
                await protocol.close()
                return
            
            protocol.connected = True
            self.connections[protocol.peer_agent_id] = protocol
            
            # Call callback (for handler registration)
            if self._on_connection:
                if asyncio.iscoroutinefunction(self._on_connection):
                    await self._on_connection(protocol)
                else:
                    self._on_connection(protocol)
            
            # CRITICAL: Do NOT start listen() automatically
            # Do NOT read from stream - let the test or callback do it
            # Just wait for connection to close
            try:
                while protocol.connected and not writer.is_closing():
                    await asyncio.sleep(0.5)
            except (ConnectionResetError, asyncio.CancelledError, BrokenPipeError):
                pass
        
        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            if protocol.peer_agent_id in self.connections:
                del self.connections[protocol.peer_agent_id]
            await protocol.close()
        
    async def start(self) -> None:
        """Start the server"""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        print(f"BeekKon server started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close all connections
        for protocol in list(self.connections.values()):
            await protocol.close()
        self.connections.clear()
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()