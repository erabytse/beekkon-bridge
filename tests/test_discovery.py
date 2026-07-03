"""
Unit tests for BeekKonDiscovery
"""

import time
import pytest
from beekkon.discovery import BeekKonDiscovery, PeerInfo


class TestPeerInfo:
    def test_peer_info_creation(self):
        peer = PeerInfo(
            agent_id="agent_test",
            ip="192.168.1.10",
            port=8765,
            capabilities=["parse_invoice", "calculate_vat"],
            public_key_sign="abc123",
            public_key_exchange="def456"
        )
        assert peer.agent_id == "agent_test"
        assert peer.ip == "192.168.1.10"
        assert peer.port == 8765
        assert "parse_invoice" in peer.capabilities
        assert peer.trust_score == 0.5
    
    def test_peer_is_alive(self):
        peer = PeerInfo(
            agent_id="agent_test",
            ip="192.168.1.10",
            port=8765,
            capabilities=[],
            public_key_sign="",
            public_key_exchange="",
            last_seen=time.time()
        )
        assert peer.is_alive() is True
        peer.last_seen = time.time() - 60
        assert peer.is_alive() is False


class TestBeekKonDiscovery:
    def test_init(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=["parse_invoice"],
            port=8765,
            public_key_sign="abc123",
            public_key_exchange="def456"
        )
        assert discovery.agent_id == "agent_test"
        assert discovery.port == 8765
        assert "parse_invoice" in discovery.capabilities
    
    def test_get_local_ip(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        ip = discovery._get_local_ip()
        assert ip is not None
        assert len(ip.split('.')) == 4
    
    def test_is_virtual_ip(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        assert discovery._is_virtual_ip("192.168.1.10") is False
        assert discovery._is_virtual_ip("172.17.0.1") is True
        assert discovery._is_virtual_ip("192.168.56.1") is True
    
    def test_build_announcement(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=["parse_invoice", "calculate_vat"],
            port=8765,
            public_key_sign="abc123",
            public_key_exchange="def456"
        )
        msg = discovery._build_announcement()
        assert msg["type"] == "announce"
        assert msg["agent_id"] == "agent_test"
        assert msg["port"] == 8765
        assert "parse_invoice" in msg["capabilities"]
        assert msg["public_key_sign"] == "abc123"
    
    def test_get_peers_empty(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        assert discovery.get_peers() == []
    
    def test_get_peers_with_capability_filter(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        peer1 = PeerInfo(
            agent_id="agent1",
            ip="192.168.1.10",
            port=8765,
            capabilities=["parse_invoice", "calculate_vat"],
            public_key_sign="",
            public_key_exchange=""
        )
        peer2 = PeerInfo(
            agent_id="agent2",
            ip="192.168.1.11",
            port=8765,
            capabilities=["send_email"],
            public_key_sign="",
            public_key_exchange=""
        )
        discovery.peers["agent1"] = peer1
        discovery.peers["agent2"] = peer2
        
        peers = discovery.get_peers(capability="parse_invoice")
        assert len(peers) == 1
        assert peers[0].agent_id == "agent1"
        
        peers = discovery.get_peers(capability="send_email")
        assert len(peers) == 1
        assert peers[0].agent_id == "agent2"
    
    def test_get_peer(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        peer = PeerInfo(
            agent_id="agent1",
            ip="192.168.1.10",
            port=8765,
            capabilities=[],
            public_key_sign="",
            public_key_exchange=""
        )
        discovery.peers["agent1"] = peer
        
        result = discovery.get_peer("agent1")
        assert result is not None
        assert result.agent_id == "agent1"
        
        result = discovery.get_peer("agent2")
        assert result is None
    
    def test_update_trust_score(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        peer = PeerInfo(
            agent_id="agent1",
            ip="192.168.1.10",
            port=8765,
            capabilities=[],
            public_key_sign="",
            public_key_exchange=""
        )
        discovery.peers["agent1"] = peer
        
        discovery.update_trust_score("agent1", 0.9)
        assert discovery.peers["agent1"].trust_score == 0.9
        
        discovery.update_trust_score("agent1", 1.5)
        assert discovery.peers["agent1"].trust_score == 1.0
        
        discovery.update_trust_score("agent1", -0.5)
        assert discovery.peers["agent1"].trust_score == 0.0
    
    def test_refresh_peers(self):
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        peer1 = PeerInfo(
            agent_id="agent1",
            ip="192.168.1.10",
            port=8765,
            capabilities=[],
            public_key_sign="",
            public_key_exchange="",
            last_seen=time.time()
        )
        discovery.peers["agent1"] = peer1
        
        peer2 = PeerInfo(
            agent_id="agent2",
            ip="192.168.1.11",
            port=8765,
            capabilities=[],
            public_key_sign="",
            public_key_exchange="",
            last_seen=time.time() - 60
        )
        discovery.peers["agent2"] = peer2
        
        discovery.refresh_peers()
        
        assert "agent1" in discovery.peers
        assert "agent2" not in discovery.peers
    
    def test_process_announcement(self):
        """Test processing a valid announcement"""
        discovery = BeekKonDiscovery(
            agent_id="agent_test",
            capabilities=[],
            port=8765
        )
        
        msg = {
            "type": "announce",
            "agent_id": "remote_agent",
            "ip": "192.168.1.50",
            "port": 9000,
            "capabilities": ["cap1", "cap2"],
            "public_key_sign": "sign_key",
            "public_key_exchange": "exchange_key",
            "timestamp": time.time()
        }
        
        discovery._process_announcement(msg)
        
        peer = discovery.get_peer("remote_agent")
        assert peer is not None
        assert peer.ip == "192.168.1.50"
        assert peer.port == 9000
        assert "cap1" in peer.capabilities


class TestIntegration:
    def test_full_discovery_flow(self):
        """Test complete discovery flow"""
        discovery1 = BeekKonDiscovery(
            agent_id="agent_comptable",
            capabilities=["parse_invoice", "calculate_vat"],
            port=8765,
            public_key_sign="key1_sign",
            public_key_exchange="key1_exchange"
        )
        
        # Simulate receiving announcement from agent_juridique
        msg = {
            "type": "announce",
            "agent_id": "agent_juridique",
            "ip": "192.168.1.11",
            "port": 8766,
            "capabilities": ["validate_contract"],
            "public_key_sign": "key2_sign",
            "public_key_exchange": "key2_exchange",
            "timestamp": time.time()
        }
        discovery1._process_announcement(msg)
        
        peers = discovery1.get_peers()
        assert len(peers) == 1
        assert peers[0].agent_id == "agent_juridique"
        
        peers = discovery1.get_peers(capability="validate_contract")
        assert len(peers) == 1