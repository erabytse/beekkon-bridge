"""
BeekKon Bridge - Local Memory Storage
SQLite-based storage for shared context between agents
"""

import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MemoryEntry:
    """A single memory entry"""
    key: str
    value: Any
    owner: str
    readers: List[str]
    writers: List[str]
    created_at: float
    updated_at: float
    ttl: Optional[int] = None  # seconds
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        return (time.time() - self.updated_at) > self.ttl
    
    def can_read(self, agent_id: str) -> bool:
        """Check if agent can read this entry"""
        return agent_id in self.readers or agent_id == self.owner
    
    def can_write(self, agent_id: str) -> bool:
        """Check if agent can write this entry"""
        return agent_id in self.writers or agent_id == self.owner


class BeekKonMemory:
    """
    Local memory storage for BeekKon agents
    
    Features:
    - SQLite-based persistence
    - Access control (readers/writers)
    - TTL (time-to-live) support
    - JSON serialization
    """
    
    def __init__(self, db_path: str = "./beekon_memory.db"):
        """
        Initialize memory storage
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                owner TEXT NOT NULL,
                readers TEXT NOT NULL,
                writers TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                ttl INTEGER
            )
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_owner ON memory(owner)
        """)
        
        self.conn.commit()
    
    def store(
        self,
        key: str,
        value: Any,
        owner: str,
        readers: List[str] = None,
        writers: List[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store a value in memory
        
        Args:
            key: Unique key
            value: Value to store (must be JSON-serializable)
            owner: Owner agent ID
            readers: List of agent IDs that can read
            writers: List of agent IDs that can write
            ttl: Time-to-live in seconds (None = no expiration)
        
        Returns:
            True if stored successfully
        """
        now = time.time()
        readers = readers or [owner]
        writers = writers or [owner]
        
        try:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO memory 
                (key, value, owner, readers, writers, created_at, updated_at, ttl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    json.dumps(value),
                    owner,
                    json.dumps(readers),
                    json.dumps(writers),
                    now,
                    now,
                    ttl
                )
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Memory store error: {e}")
            return False
    
    def retrieve(self, key: str, agent_id: str) -> Optional[Any]:
        """
        Retrieve a value from memory
        
        Args:
            key: Key to retrieve
            agent_id: Agent requesting the value
        
        Returns:
            Value or None if not found/no permission
        """
        try:
            cursor = self.conn.execute(
                "SELECT value, owner, readers, writers, created_at, updated_at, ttl FROM memory WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            entry = MemoryEntry(
                key=key,
                value=json.loads(row[0]),
                owner=row[1],
                readers=json.loads(row[2]),
                writers=json.loads(row[3]),
                created_at=row[4],
                updated_at=row[5],
                ttl=row[6]
            )
            
            # Check expiration
            if entry.is_expired():
                self.delete(key)
                return None
            
            # Check read permission
            if not entry.can_read(agent_id):
                return None
            
            return entry.value
        
        except Exception as e:
            print(f"Memory retrieve error: {e}")
            return None
    
    def update(self, key: str, value: Any, agent_id: str) -> bool:
        """
        Update a value in memory
        
        Args:
            key: Key to update
            value: New value
            agent_id: Agent updating the value
        
        Returns:
            True if updated successfully
        """
        try:
            # Check if entry exists and agent has write permission
            cursor = self.conn.execute(
                "SELECT writers, owner FROM memory WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if not row:
                return False
            
            writers = json.loads(row[0])
            owner = row[1]
            
            if agent_id not in writers and agent_id != owner:
                return False
            
            # Update
            now = time.time()
            self.conn.execute(
                "UPDATE memory SET value = ?, updated_at = ? WHERE key = ?",
                (json.dumps(value), now, key)
            )
            self.conn.commit()
            return True
        
        except Exception as e:
            print(f"Memory update error: {e}")
            return False
    
    def delete(self, key: str, agent_id: str = None) -> bool:
        """
        Delete a value from memory
        
        Args:
            key: Key to delete
            agent_id: Agent deleting (optional, for permission check)
        
        Returns:
            True if deleted successfully
        """
        try:
            if agent_id:
                # Check permission
                cursor = self.conn.execute(
                    "SELECT owner, writers FROM memory WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                owner = row[0]
                writers = json.loads(row[1])
                
                if agent_id != owner and agent_id not in writers:
                    return False
            
            self.conn.execute("DELETE FROM memory WHERE key = ?", (key,))
            self.conn.commit()
            return True
        
        except Exception as e:
            print(f"Memory delete error: {e}")
            return False
    
    def list_keys(self, owner: str = None) -> List[str]:
        """
        List all keys in memory
        
        Args:
            owner: Filter by owner (optional)
        
        Returns:
            List of keys
        """
        try:
            if owner:
                cursor = self.conn.execute(
                    "SELECT key FROM memory WHERE owner = ?",
                    (owner,)
                )
            else:
                cursor = self.conn.execute("SELECT key FROM memory")
            
            return [row[0] for row in cursor.fetchall()]
        
        except Exception as e:
            print(f"Memory list error: {e}")
            return []
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries
        
        Returns:
            Number of entries removed
        """
        try:
            now = time.time()
            cursor = self.conn.execute(
                "SELECT key, updated_at, ttl FROM memory WHERE ttl IS NOT NULL"
            )
            
            expired_keys = []
            for row in cursor.fetchall():
                key, updated_at, ttl = row
                if (now - updated_at) > ttl:
                    expired_keys.append(key)
            
            if expired_keys:
                placeholders = ','.join('?' * len(expired_keys))
                self.conn.execute(
                    f"DELETE FROM memory WHERE key IN ({placeholders})",
                    expired_keys
                )
                self.conn.commit()
            
            return len(expired_keys)
        
        except Exception as e:
            print(f"Memory cleanup error: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()