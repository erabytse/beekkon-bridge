"""
Unit tests for BeekKonMemory
"""

import pytest
import time
import os
from pathlib import Path
from beekkon.memory import BeekKonMemory, MemoryEntry


class TestMemoryEntry:
    def test_entry_creation(self):
        """Test MemoryEntry creation"""
        entry = MemoryEntry(
            key="test_key",
            value={"data": "test"},
            owner="agent_a",
            readers=["agent_a", "agent_b"],
            writers=["agent_a"],
            created_at=time.time(),
            updated_at=time.time(),
            ttl=3600
        )
        assert entry.key == "test_key"
        assert entry.owner == "agent_a"
    
    def test_entry_expiration(self):
        """Test entry expiration"""
        now = time.time()
        entry = MemoryEntry(
            key="test",
            value={},
            owner="a",
            readers=["a"],
            writers=["a"],
            created_at=now,
            updated_at=now,
            ttl=1
        )
        assert entry.is_expired() is False
        
        entry.updated_at = now - 10
        assert entry.is_expired() is True
    
    def test_entry_permissions(self):
        """Test entry read/write permissions"""
        entry = MemoryEntry(
            key="test",
            value={},
            owner="agent_a",
            readers=["agent_a", "agent_b"],
            writers=["agent_a"],
            created_at=time.time(),
            updated_at=time.time()
        )
        
        # Read permissions
        assert entry.can_read("agent_a") is True
        assert entry.can_read("agent_b") is True
        assert entry.can_read("agent_c") is False
        
        # Write permissions
        assert entry.can_write("agent_a") is True
        assert entry.can_write("agent_b") is False


class TestBeekKonMemory:
    @pytest.fixture
    def memory(self, tmp_path):
        """Create a temporary memory instance"""
        db_path = str(tmp_path / "test_memory.db")
        mem = BeekKonMemory(db_path)
        yield mem
        mem.close()
    
    def test_store_and_retrieve(self, memory):
        """Test basic store and retrieve"""
        success = memory.store(
            key="test_key",
            value={"data": "test_value"},
            owner="agent_a",
            readers=["agent_a"],
            writers=["agent_a"]
        )
        assert success is True
        
        value = memory.retrieve("test_key", "agent_a")
        assert value == {"data": "test_value"}
    
    def test_retrieve_no_permission(self, memory):
        """Test retrieve without permission"""
        memory.store(
            key="secret",
            value={"data": "secret"},
            owner="agent_a",
            readers=["agent_a"]
        )
        
        value = memory.retrieve("secret", "agent_b")
        assert value is None
    
    def test_update(self, memory):
        """Test value update"""
        memory.store(
            key="test",
            value={"v": 1},
            owner="agent_a",
            writers=["agent_a"]
        )
        
        success = memory.update("test", {"v": 2}, "agent_a")
        assert success is True
        
        value = memory.retrieve("test", "agent_a")
        assert value == {"v": 2}
    
    def test_update_no_permission(self, memory):
        """Test update without permission"""
        memory.store(
            key="test",
            value={"v": 1},
            owner="agent_a",
            writers=["agent_a"]
        )
        
        success = memory.update("test", {"v": 2}, "agent_b")
        assert success is False
    
    def test_delete(self, memory):
        """Test deletion"""
        memory.store(
            key="test",
            value={"data": "test"},
            owner="agent_a"
        )
        
        success = memory.delete("test")
        assert success is True
        
        value = memory.retrieve("test", "agent_a")
        assert value is None
    
    def test_list_keys(self, memory):
        """Test listing keys"""
        memory.store("key1", {"a": 1}, "agent_a")
        memory.store("key2", {"b": 2}, "agent_a")
        memory.store("key3", {"c": 3}, "agent_b")
        
        all_keys = memory.list_keys()
        assert len(all_keys) == 3
        
        agent_a_keys = memory.list_keys(owner="agent_a")
        assert len(agent_a_keys) == 2
    
    def test_ttl_expiration(self, memory):
        """Test TTL expiration"""
        memory.store(
            key="expiring",
            value={"data": "test"},
            owner="agent_a",
            ttl=1  # 1 second TTL
        )
        
        # Should be available immediately
        value = memory.retrieve("expiring", "agent_a")
        assert value is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be expired
        value = memory.retrieve("expiring", "agent_a")
        assert value is None
    
    def test_cleanup_expired(self, memory):
        """Test cleanup of expired entries"""
        memory.store("key1", {"a": 1}, "agent_a", ttl=1)
        memory.store("key2", {"b": 2}, "agent_a", ttl=1)
        memory.store("key3", {"c": 3}, "agent_a", ttl=3600)
        
        time.sleep(1.5)
        
        removed = memory.cleanup_expired()
        assert removed == 2
        
        keys = memory.list_keys()
        assert len(keys) == 1
        assert keys[0] == "key3"
    
    def test_shared_context_between_agents(self, memory):
        """Test shared context scenario"""
        # Agent A stores a contract
        memory.store(
            key="contract_123",
            value={"id": 123, "status": "draft"},
            owner="agent_juridique",
            readers=["agent_juridique", "agent_comptable"],
            writers=["agent_juridique"]
        )
        
        # Agent Comptable can read
        value = memory.retrieve("contract_123", "agent_comptable")
        assert value is not None
        assert value["status"] == "draft"
        
        # Agent Comptable cannot write
        success = memory.update("contract_123", {"status": "approved"}, "agent_comptable")
        assert success is False
        
        # Agent Juridique can write
        success = memory.update("contract_123", {"status": "approved"}, "agent_juridique")
        assert success is True
        
        # Both can now see the update
        value = memory.retrieve("contract_123", "agent_comptable")
        assert value["status"] == "approved"