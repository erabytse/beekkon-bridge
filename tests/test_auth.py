"""
Unit tests for BeekKonAuth
"""

import pytest
from beekkon.auth import BeekKonAuth


class TestBeekKonAuth:
    """Comprehensive tests for authentication"""
    
    def test_init_with_valid_secret(self):
        """Test initialization with valid secret"""
        auth = BeekKonAuth("agent_test", "my-super-secret-master-key-1234567890")
        assert auth.agent_id == "agent_test"
        assert len(auth.user_id) == 64  # SHA512 = 64 hex chars
        assert auth.signing_key is not None
        assert auth.private_key is not None
    
    def test_init_with_short_secret_raises(self):
        """Test that too short secret raises an error"""
        with pytest.raises(ValueError, match="at least 32 characters"):
            BeekKonAuth("agent_test", "short")
    
    def test_derive_user_id_deterministic(self):
        """Test that user_id is deterministic (same secret = same user_id)"""
        auth1 = BeekKonAuth("agent1", "same-secret-12345678901234567890")
        auth2 = BeekKonAuth("agent2", "same-secret-12345678901234567890")
        assert auth1.user_id == auth2.user_id
    
    def test_derive_user_id_different_secrets(self):
        """Test that different secrets = different user_ids"""
        auth1 = BeekKonAuth("agent1", "secret-one-1234567890123456789012")
        auth2 = BeekKonAuth("agent2", "secret-two-0987654321098765432109")
        assert auth1.user_id != auth2.user_id
    
    def test_initiate_handshake(self):
        """Test HELLO message generation"""
        auth = BeekKonAuth("agent_test", "my-super-secret-master-key-1234567890")
        hello = auth.initiate_handshake()
        
        assert hello["type"] == "hello"
        assert hello["agent_id"] == "agent_test"
        assert hello["user_id"] == auth.user_id
        assert "public_key_sign" in hello
        assert "public_key_exchange" in hello
        assert "timestamp" in hello
        assert len(hello["public_key_sign"]) == 64
        assert len(hello["public_key_exchange"]) == 64
    
    def test_generate_challenge(self):
        """Test challenge generation"""
        auth = BeekKonAuth("agent_test", "my-super-secret-master-key-1234567890")
        challenge_id, nonce = auth.generate_challenge()
        
        assert len(challenge_id) == 32
        assert len(nonce) == 64
    
    def test_full_handshake_success(self):
        """Test complete: 2 agents authenticate successfully"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        # B authorizes A (stores only A's user_id)
        agent_b.add_authorized_agent("agent_a", agent_a.user_id)
        
        challenge_id, nonce = agent_b.generate_challenge()
        response_a = agent_a.respond_to_challenge(challenge_id, nonce)
        
        is_valid = agent_b.verify_response(response_a, nonce, "agent_a")
        assert is_valid is True
    
    def test_full_handshake_wrong_nonce(self):
        """Test that wrong nonce = authentication fails"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        agent_b.add_authorized_agent("agent_a", agent_a.user_id)
        
        challenge_id, nonce = agent_b.generate_challenge()
        response_a = agent_a.respond_to_challenge(challenge_id, nonce)
        
        wrong_nonce = "0" * 64
        is_valid = agent_b.verify_response(response_a, wrong_nonce, "agent_a")
        assert is_valid is False
    
    def test_full_handshake_unauthorized_agent(self):
        """Test that unauthorized agent = authentication fails"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        # B does NOT authorize A
        challenge_id, nonce = agent_b.generate_challenge()
        response_a = agent_a.respond_to_challenge(challenge_id, nonce)
        
        is_valid = agent_b.verify_response(response_a, nonce, "agent_a")
        assert is_valid is False
    
    def test_establish_session(self):
        """Test encrypted session establishment"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        hello_a = agent_a.initiate_handshake()
        hello_b = agent_b.initiate_handshake()
        
        assert agent_a.establish_session(hello_b["public_key_exchange"]) is True
        assert agent_b.establish_session(hello_a["public_key_exchange"]) is True
    
    def test_encrypt_decrypt(self):
        """Test E2E encryption/decryption"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        hello_a = agent_a.initiate_handshake()
        hello_b = agent_b.initiate_handshake()
        
        agent_a.establish_session(hello_b["public_key_exchange"])
        agent_b.establish_session(hello_a["public_key_exchange"])
        
        message = b"Hello Agent B!"
        encrypted = agent_a.encrypt(message)
        decrypted = agent_b.decrypt(encrypted)
        assert decrypted == message
    
    def test_encrypt_without_session_raises(self):
        """Test that encrypting without session raises an error"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        
        with pytest.raises(RuntimeError, match="Session not established"):
            agent_a.encrypt(b"test")
    
    def test_sign_and_verify_message(self):
        """Test message signature and verification"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        message = b"Important message"
        signature = agent_a.sign_message(message)
        
        agent_b.peer_verify_key = agent_a.verify_key
        is_valid = agent_b.verify_peer_signature(message, signature)
        assert is_valid is True
    
    def test_verify_peer_signature_without_auth_raises(self):
        """Test that verifying without authentication raises an error"""
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        with pytest.raises(RuntimeError, match="Peer not authenticated"):
            agent_b.verify_peer_signature(b"test", "0" * 128)


class TestIntegration:
    """Complete integration tests"""
    
    def test_full_communication_flow(self):
        """Test complete: authentication + session + communication"""
        agent_a = BeekKonAuth("agent_comptable", "secret-comptable-12345678901234567890")
        agent_b = BeekKonAuth("agent_juridique", "secret-juridique-0987654321098765432109")
        
        # B authorizes A
        agent_b.add_authorized_agent("agent_comptable", agent_a.user_id)
        
        # Handshake
        hello_a = agent_a.initiate_handshake()
        challenge_id, nonce = agent_b.generate_challenge()
        response_a = agent_a.respond_to_challenge(challenge_id, nonce)
        
        # Verify
        is_valid = agent_b.verify_response(response_a, nonce, "agent_comptable")
        assert is_valid is True
        
        # Session
        hello_b = agent_b.initiate_handshake()
        agent_a.establish_session(hello_b["public_key_exchange"])
        agent_b.establish_session(hello_a["public_key_exchange"])
        
        # Encrypted communication
        message = b"Can you validate contract #12345?"
        encrypted = agent_a.encrypt(message)
        decrypted = agent_b.decrypt(encrypted)
        assert decrypted == message
        
        response = b"Contract validated"
        encrypted_response = agent_b.encrypt(response)
        decrypted_response = agent_a.decrypt(encrypted_response)
        assert decrypted_response == response
    
    def test_unicode_message_support(self):
        """Test that Unicode messages work (encoded as UTF-8)"""
        agent_a = BeekKonAuth("agent_a", "secret-agent-a-12345678901234567890")
        agent_b = BeekKonAuth("agent_b", "secret-agent-b-0987654321098765432109")
        
        hello_a = agent_a.initiate_handshake()
        hello_b = agent_b.initiate_handshake()
        
        agent_a.establish_session(hello_b["public_key_exchange"])
        agent_b.establish_session(hello_a["public_key_exchange"])
        
        unicode_message = "Contrat validé - Vertrag bestätigt - 合同已确认"
        message_bytes = unicode_message.encode('utf-8')
        
        encrypted = agent_a.encrypt(message_bytes)
        decrypted = agent_b.decrypt(encrypted)
        
        assert decrypted.decode('utf-8') == unicode_message