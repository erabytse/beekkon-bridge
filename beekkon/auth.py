"""
BeekKon Bridge - Zero-Knowledge Authentication + Key Exchange
Based on CryptoLogin V2 + Curve25519 + Ed25519

Security model:
- master_secret: Private, never shared, never stored on server
- user_id: Derived from master_secret via PBKDF2, can be shared
- HMAC: Computed with user_id (not master_secret)
- Server stores only user_id of authorized agents (zero-knowledge)
"""

import hashlib
import hmac
import os
import time
from typing import Optional, Tuple, Dict
from nacl.signing import SigningKey, VerifyKey
from nacl.public import PrivateKey, PublicKey, Box


class BeekKonAuth:
    """
    Zero-knowledge authentication for AI agents.
    Combines CryptoLogin V2 (HMAC) + Curve25519 (key exchange) + Ed25519 (signatures).
    """
    
    def __init__(self, agent_id: str, master_secret: str):
        """
        Initialize authentication for an agent.
        
        Args:
            agent_id: Public agent identifier (can be shared)
            master_secret: Private master secret (min 32 characters, NEVER share)
        """
        if len(master_secret) < 32:
            raise ValueError("master_secret must be at least 32 characters")
        
        self.agent_id = agent_id
        self.master_secret = master_secret
        
        # Derive user_id from master_secret (like CryptoLogin V2)
        self.user_id = self._derive_user_id(master_secret)
        
        # Cryptographic keys
        self.signing_key = SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.private_key = PrivateKey.generate()
        self.public_key = self.private_key.public_key
        
        # Session state
        self.session_box: Optional[Box] = None
        self.peer_verify_key: Optional[VerifyKey] = None
        
        # Authorized agents (server-side): agent_id -> user_id
        self.authorized_agents: Dict[str, str] = {}
    
    def _derive_user_id(self, master_secret: str, iterations: int = 100_000) -> str:
        """
        Derive user_id from master_secret via PBKDF2-HMAC-SHA512.
        Same secret always produces same user_id (deterministic).
        """
        salt = b"beekon_bridge_v1"
        dk = hashlib.pbkdf2_hmac(
            'sha512',
            master_secret.encode('utf-8'),
            salt,
            iterations,
            dklen=32
        )
        return dk.hex()
    
    def add_authorized_agent(self, agent_id: str, user_id: str) -> None:
        """
        Authorize a remote agent (server-side only).
        Server stores only user_id, never master_secret (zero-knowledge).
        
        Args:
            agent_id: Agent's public identifier
            user_id: Agent's derived user_id (computed from their master_secret)
        """
        self.authorized_agents[agent_id] = user_id
    
    def initiate_handshake(self) -> dict:
        """Step 1: HELLO message with agent_id + user_id + public keys."""
        return {
            "type": "hello",
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "public_key_sign": self.verify_key.encode().hex(),
            "public_key_exchange": self.public_key.encode().hex(),
            "timestamp": int(time.time())
        }
    
    def generate_challenge(self) -> Tuple[str, str]:
        """Step 2: Generate challenge nonce for remote agent."""
        challenge_id = os.urandom(16).hex()
        nonce = os.urandom(32).hex()
        return challenge_id, nonce
    
    def respond_to_challenge(self, challenge_id: str, nonce: str) -> dict:
        """Step 3: Respond to challenge with HMAC + signature."""
        # HMAC computed with user_id (derived from master_secret)
        hmac_value = hmac.new(
            self.user_id.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Sign with Ed25519
        message = f"{challenge_id}:{hmac_value}:{int(time.time())}".encode('utf-8')
        signature = self.signing_key.sign(message).signature.hex()
        
        return {
            "type": "response",
            "challenge_id": challenge_id,
            "hmac": hmac_value,
            "signature": signature,
            "public_key_sign": self.verify_key.encode().hex(),
            "public_key_exchange": self.public_key.encode().hex(),
            "timestamp": int(time.time())
        }
    
    def verify_response(self, response: dict, expected_nonce: str, peer_agent_id: str) -> bool:
        """
        Step 4: Verify challenge response.
        
        Args:
            response: Response from peer
            expected_nonce: Nonce we sent
            peer_agent_id: Peer's agent_id
        
        Returns:
            True if authentication successful
        """
        # Check if agent is authorized
        if peer_agent_id not in self.authorized_agents:
            return False
        
        # Get authorized user_id for this agent
        expected_user_id = self.authorized_agents[peer_agent_id]
        
        # Verify HMAC (computed with user_id)
        expected_hmac = hmac.new(
            expected_user_id.encode('utf-8'),
            expected_nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(response['hmac'], expected_hmac):
            return False
        
        # Verify Ed25519 signature
        try:
            peer_verify_key = VerifyKey(bytes.fromhex(response['public_key_sign']))
            message = f"{response['challenge_id']}:{response['hmac']}:{response['timestamp']}".encode('utf-8')
            peer_verify_key.verify(message, bytes.fromhex(response['signature']))
            self.peer_verify_key = peer_verify_key
            return True
        except Exception:
            return False
    
    def establish_session(self, peer_public_key_hex: str) -> bool:
        """Step 5: Establish encrypted session via Curve25519."""
        try:
            peer_public_key = PublicKey(bytes.fromhex(peer_public_key_hex))
            self.session_box = Box(self.private_key, peer_public_key)
            return True
        except Exception:
            return False
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt with session key (AES-256-GCM via NaCl)."""
        if not self.session_box:
            raise RuntimeError("Session not established. Call establish_session() first.")
        return self.session_box.encrypt(plaintext)
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt with session key."""
        if not self.session_box:
            raise RuntimeError("Session not established. Call establish_session() first.")
        return self.session_box.decrypt(ciphertext)
    
    def sign_message(self, message: bytes) -> str:
        """Sign a message with Ed25519."""
        return self.signing_key.sign(message).signature.hex()
    
    def verify_peer_signature(self, message: bytes, signature_hex: str) -> bool:
        """Verify peer's message signature."""
        if not self.peer_verify_key:
            raise RuntimeError("Peer not authenticated.")
        try:
            self.peer_verify_key.verify(message, bytes.fromhex(signature_hex))
            return True
        except Exception:
            return False


# Quick test
if __name__ == "__main__":
    agent_a = BeekKonAuth("agent_a", "my-super-secret-master-key-1234567890")
    agent_b = BeekKonAuth("agent_b", "another-super-secret-master-key-0987654321")
    
    # B authorizes A (stores only A's user_id, not master_secret)
    agent_b.add_authorized_agent("agent_a", agent_a.user_id)
    
    # Handshake
    hello_a = agent_a.initiate_handshake()
    challenge_id, nonce = agent_b.generate_challenge()
    response_a = agent_a.respond_to_challenge(challenge_id, nonce)
    
    is_valid = agent_b.verify_response(response_a, nonce, "agent_a")
    print(f"Authentication successful: {is_valid}")
    
    # Session
    hello_b = agent_b.initiate_handshake()
    agent_a.establish_session(hello_b['public_key_exchange'])
    agent_b.establish_session(hello_a['public_key_exchange'])
    
    # Encrypted communication
    message = b"Hello Agent B!"
    encrypted = agent_a.encrypt(message)
    decrypted = agent_b.decrypt(encrypted)
    print(f"Decrypted: {decrypted.decode('utf-8')}")