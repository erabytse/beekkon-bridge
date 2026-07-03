"""
Unit tests for BeekKonCrypto
"""

import pytest
from beekkon.crypto import BeekKonCrypto


class TestBeekKonCrypto:
    def test_generate_signing_keys(self):
        """Test Ed25519 key pair generation"""
        signing_key, verify_key = BeekKonCrypto.generate_signing_keys()
        assert signing_key is not None
        assert verify_key is not None
    
    def test_generate_exchange_keys(self):
        """Test Curve25519 key pair generation"""
        private_key, public_key = BeekKonCrypto.generate_exchange_keys()
        assert private_key is not None
        assert public_key is not None
    
    def test_sign_and_verify(self):
        """Test message signing and verification"""
        signing_key, verify_key = BeekKonCrypto.generate_signing_keys()
        message = b"Hello, World!"
        
        signature = BeekKonCrypto.sign(signing_key, message)
        assert signature is not None
        
        is_valid = BeekKonCrypto.verify(verify_key, message, signature)
        assert is_valid is True
        
        # Tampered message should fail
        is_valid = BeekKonCrypto.verify(verify_key, b"Tampered", signature)
        assert is_valid is False
    
    def test_encrypt_decrypt_with_shared_key(self):
        """Test E2E encryption with shared key"""
        # Generate key pairs for 2 parties
        priv_a, pub_a = BeekKonCrypto.generate_exchange_keys()
        priv_b, pub_b = BeekKonCrypto.generate_exchange_keys()
        
        # Derive shared keys (should be identical)
        shared_a = BeekKonCrypto.derive_shared_key(priv_a, pub_b)
        shared_b = BeekKonCrypto.derive_shared_key(priv_b, pub_a)
        
        assert shared_a == shared_b
        
        # Encrypt and decrypt
        plaintext = b"Secret message"
        ciphertext = BeekKonCrypto.encrypt_with_shared_key(shared_a, plaintext)
        decrypted = BeekKonCrypto.decrypt_with_shared_key(shared_b, ciphertext)
        
        assert decrypted == plaintext
    
    def test_derive_key_from_password(self):
        """Test PBKDF2 key derivation"""
        password = "my-super-secret-password"
        
        # Derive with auto-generated salt
        key1, salt1 = BeekKonCrypto.derive_key_from_password(password)
        assert len(key1) == 32
        assert len(salt1) == 16
        
        # Same password + same salt = same key (deterministic)
        key2, _ = BeekKonCrypto.derive_key_from_password(password, salt1)
        assert key1 == key2
        
        # Different password = different key
        key3, _ = BeekKonCrypto.derive_key_from_password("different-password", salt1)
        assert key1 != key3
    
    def test_generate_random_bytes(self):
        """Test random bytes generation"""
        random_bytes = BeekKonCrypto.generate_random_bytes(32)
        assert len(random_bytes) == 32
        
        # Should be different each time
        random_bytes2 = BeekKonCrypto.generate_random_bytes(32)
        assert random_bytes != random_bytes2
    
    def test_hash_data(self):
        """Test data hashing"""
        data = b"Hello, World!"
        
        hash1 = BeekKonCrypto.hash_data(data, 'sha256')
        assert len(hash1) == 64  # SHA256 = 64 hex chars
        
        hash2 = BeekKonCrypto.hash_data(data, 'sha256')
        assert hash1 == hash2  # Deterministic
        
        hash3 = BeekKonCrypto.hash_data(b"Different", 'sha256')
        assert hash1 != hash3