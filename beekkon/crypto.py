"""
BeekKon Bridge - Cryptographic Utilities
High-level wrapper around PyNaCl for E2E encryption
"""

from typing import Tuple
from nacl.public import PrivateKey, PublicKey, Box
from nacl.signing import SigningKey, VerifyKey
from nacl.secret import SecretBox
from nacl.utils import random
import hashlib


class BeekKonCrypto:
    """
    Cryptographic utilities for BeekKon Bridge
    
    Provides:
    - Key generation (Ed25519 for signatures, Curve25519 for encryption)
    - E2E encryption (AES-256-GCM via NaCl)
    - Digital signatures (Ed25519)
    - Key derivation (PBKDF2)
    """
    
    @staticmethod
    def generate_signing_keys() -> Tuple[SigningKey, VerifyKey]:
        """Generate Ed25519 signing key pair"""
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key
        return signing_key, verify_key
    
    @staticmethod
    def generate_exchange_keys() -> Tuple[PrivateKey, PublicKey]:
        """Generate Curve25519 key pair for key exchange"""
        private_key = PrivateKey.generate()
        public_key = private_key.public_key
        return private_key, public_key
    
    @staticmethod
    def derive_shared_key(private_key: PrivateKey, peer_public_key: PublicKey) -> bytes:
        """Derive shared secret via Curve25519 Diffie-Hellman"""
        box = Box(private_key, peer_public_key)
        return box.shared_key()
    
    @staticmethod
    def encrypt_with_shared_key(shared_key: bytes, plaintext: bytes) -> bytes:
        """Encrypt with shared key (AES-256-GCM)"""
        box = SecretBox(shared_key)
        return box.encrypt(plaintext)
    
    @staticmethod
    def decrypt_with_shared_key(shared_key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt with shared key"""
        box = SecretBox(shared_key)
        return box.decrypt(ciphertext)
    
    @staticmethod
    def sign(signing_key: SigningKey, message: bytes) -> bytes:
        """Sign a message with Ed25519"""
        signed = signing_key.sign(message)
        return signed.signature
    
    @staticmethod
    def verify(verify_key: VerifyKey, message: bytes, signature: bytes) -> bool:
        """Verify an Ed25519 signature"""
        try:
            verify_key.verify(message, signature)
            return True
        except Exception:
            return False
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes = None, iterations: int = 100_000) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password via PBKDF2-HMAC-SHA512
        
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = random(16)
        
        dk = hashlib.pbkdf2_hmac(
            'sha512',
            password.encode('utf-8'),
            salt,
            iterations,
            dklen=32
        )
        
        return dk, salt
    
    @staticmethod
    def generate_random_bytes(length: int = 32) -> bytes:
        """Generate cryptographically secure random bytes"""
        return random(length)
    
    @staticmethod
    def hash_data(data: bytes, algorithm: str = 'sha256') -> str:
        """Hash data with specified algorithm"""
        h = hashlib.new(algorithm)
        h.update(data)
        return h.hexdigest()