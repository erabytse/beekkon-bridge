"""
BeekKon Bridge - P2P Discovery via UDP Broadcast
Custom implementation - no external dependencies
Agents automatically discover each other on the local network
"""

import socket
import time
import threading
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class PeerInfo:
    """Information about a discovered peer"""
    agent_id: str
    ip: str
    port: int
    capabilities: List[str]
    public_key_sign: str
    public_key_exchange: str
    last_seen: float = field(default_factory=time.time)
    trust_score: float = 0.5
    
    def is_alive(self, timeout: int = 30) -> bool:
        """Check if peer is still active"""
        return (time.time() - self.last_seen) < timeout


class BeekKonDiscovery:
    """
    P2P discovery for AI agents using UDP broadcast
    Agents announce their capabilities and discover others automatically
    """
    
    BROADCAST_PORT = 37020  # Standard broadcast port for BeekKon
    ANNOUNCE_INTERVAL = 2.0  # seconds between announcements
    BUFFER_SIZE = 4096
    
    def __init__(
        self,
        agent_id: str,
        capabilities: List[str],
        port: int = 8765,
        public_key_sign: str = "",
        public_key_exchange: str = "",
        host: str = "0.0.0.0"
    ):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.port = port
        self.public_key_sign = public_key_sign
        self.public_key_exchange = public_key_exchange
        self.host = host
        
        self.peers: Dict[str, PeerInfo] = {}
        self.lock = threading.Lock()
        
        # Callbacks
        self.on_peer_discovered: Optional[Callable[[PeerInfo], None]] = None
        self.on_peer_lost: Optional[Callable[[str], None]] = None
        
        # Threads
        self._announce_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Sockets
        self._announce_socket: Optional[socket.socket] = None
        self._listen_socket: Optional[socket.socket] = None
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _get_broadcast_ip(self) -> str:
        """Get broadcast address for current network"""
        local_ip = self._get_local_ip()
        parts = local_ip.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.255"
    
    def _build_announcement(self) -> dict:
        """Build announcement message"""
        return {
            "type": "announce",
            "agent_id": self.agent_id,
            "ip": self._get_local_ip(),
            "port": self.port,
            "capabilities": self.capabilities,
            "public_key_sign": self.public_key_sign,
            "public_key_exchange": self.public_key_exchange,
            "timestamp": time.time()
        }
    
    def _announce_loop(self):
        """Periodically broadcast announcements"""
        while self._running:
            try:
                msg = self._build_announcement()
                data = json.dumps(msg).encode('utf-8')
                broadcast_ip = self._get_broadcast_ip()
                self._announce_socket.sendto(data, (broadcast_ip, self.BROADCAST_PORT))
            except Exception as e:
                if self._running:
                    print(f"Announce error: {e}")
            
            # Sleep in small increments for responsive shutdown
            for _ in range(int(self.ANNOUNCE_INTERVAL * 10)):
                if not self._running:
                    break
                time.sleep(0.1)
    
    def _listen_loop(self):
        """Listen for announcements from other agents"""
        while self._running:
            try:
                self._listen_socket.settimeout(1.0)
                try:
                    data, addr = self._listen_socket.recvfrom(self.BUFFER_SIZE)
                except socket.timeout:
                    continue
                
                msg = json.loads(data.decode('utf-8'))
                
                if msg.get("type") != "announce":
                    continue
                
                # Skip self
                if msg.get("agent_id") == self.agent_id:
                    continue
                
                # Skip virtual IPs
                ip = msg.get("ip", "")
                if self._is_virtual_ip(ip):
                    continue
                
                self._process_announcement(msg)
            
            except Exception as e:
                if self._running:
                    print(f"Listen error: {e}")
    
    def _process_announcement(self, msg: dict):
        """Process a received announcement"""
        agent_id = msg.get("agent_id")
        if not agent_id:
            return
        
        peer = PeerInfo(
            agent_id=agent_id,
            ip=msg.get("ip", ""),
            port=msg.get("port", 0),
            capabilities=msg.get("capabilities", []),
            public_key_sign=msg.get("public_key_sign", ""),
            public_key_exchange=msg.get("public_key_exchange", ""),
            last_seen=time.time()
        )
        
        with self.lock:
            is_new = agent_id not in self.peers
            self.peers[agent_id] = peer
        
        if is_new and self.on_peer_discovered:
            try:
                self.on_peer_discovered(peer)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def _is_virtual_ip(self, ip: str) -> bool:
        """Check if IP is from virtual environment"""
        if not ip:
            return True
        virtual_prefixes = [
            "172.17.", "172.18.", "172.19.",
            "10.0.", "192.168.56.",
        ]
        return any(ip.startswith(prefix) for prefix in virtual_prefixes)
    
    def start(self):
        """Start discovery service"""
        if self._running:
            return
        
        self._running = True
        
        # Create announce socket (UDP, broadcast enabled)
        self._announce_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._announce_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Create listen socket (UDP, bound to broadcast port)
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Windows needs SO_REUSEADDR differently
        try:
            self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass  # Not supported on all platforms
        
        self._listen_socket.bind(("", self.BROADCAST_PORT))
        
        # Start threads
        self._announce_thread = threading.Thread(target=self._announce_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._announce_thread.start()
        self._listen_thread.start()
    
    def stop(self):
        """Stop discovery service"""
        self._running = False
        
        # Wait for threads
        if self._announce_thread:
            self._announce_thread.join(timeout=2.0)
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
        
        # Close sockets
        if self._announce_socket:
            try:
                self._announce_socket.close()
            except Exception:
                pass
        if self._listen_socket:
            try:
                self._listen_socket.close()
            except Exception:
                pass
        
        self._announce_socket = None
        self._listen_socket = None
        self._announce_thread = None
        self._listen_thread = None
    
    def get_peers(self, capability: Optional[str] = None) -> List[PeerInfo]:
        """Get list of discovered peers"""
        with self.lock:
            peers = list(self.peers.values())
        
        if capability:
            peers = [p for p in peers if capability in p.capabilities]
        
        peers = [p for p in peers if p.is_alive()]
        return peers
    
    def get_peer(self, agent_id: str) -> Optional[PeerInfo]:
        """Get a specific peer by agent_id"""
        with self.lock:
            peer = self.peers.get(agent_id)
            if peer and peer.is_alive():
                return peer
        return None
    
    def update_trust_score(self, agent_id: str, score: float):
        """Update trust score for a peer"""
        with self.lock:
            if agent_id in self.peers:
                self.peers[agent_id].trust_score = max(0.0, min(1.0, score))
    
    def refresh_peers(self):
        """Remove dead peers (not seen for >30s)"""
        with self.lock:
            dead_peers = [
                agent_id for agent_id, peer in self.peers.items()
                if not peer.is_alive()
            ]
            for agent_id in dead_peers:
                del self.peers[agent_id]
                if self.on_peer_lost:
                    try:
                        self.on_peer_lost(agent_id)
                    except Exception:
                        pass