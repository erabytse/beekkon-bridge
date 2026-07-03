# BeekKon Bridge - Protocol Specification v1.0

## Overview

BeekKon Bridge is a peer-to-peer communication protocol for AI agents.
It provides zero-knowledge authentication, end-to-end encryption, and
automatic peer discovery.

## Architecture

```text
┌──────────────────────────────────────┐
│ Application Layer                    │
│ BeekKonAgent (handlers, requests)    │
├──────────────────────────────────────┤
│ Routing Layer                        │
│ BeekKonRouter (pattern matching)     │
├──────────────────────────────────────┤
│ Transport Layer                      │
│ BeekKonProtocol (TCP + MessagePack)  │
├──────────────────────────────────────┤
│ Security Layer                       │
│ BeekKonAuth (Ed25519 + Curve25519)   │
├──────────────────────────────────────┤
│ Discovery Layer                      │
│ BeekKonDiscovery (UDP Broadcast)     │
└──────────────────────────────────────┘
```

## 1. Discovery Protocol (UDP)

### Announcement Format

```json
{
  "type": "announce",
  "agent_id": "agent_name",
  "ip": "192.168.1.10",
  "port": 8765,
  "capabilities": ["task1", "task2"],
  "public_key_sign": "hex_encoded_ed25519_public_key",
  "public_key_exchange": "hex_encoded_curve25519_public_key",
  "timestamp": 1234567890.123
}
```

- Transport: UDP broadcast on port 37020
- Interval: Every 2 seconds
- TTL: Peers expire after 30 seconds of silence

## 2. Authentication Protocol (TCP)

### Handshake Flow

```
Client                          Server
  |                               |
  |--- HELLO -------------------->|
  |   {agent_id, user_id,         |
  |    public_key_sign,           |
  |    public_key_exchange}       |
  |                               |
  |<-- CHALLENGE -----------------|
  |   {challenge_id, nonce,       |
  |    public_key_sign}           |
  |                               |
  |--- RESPONSE ----------------->|
  |   {challenge_id, hmac,        |
  |    signature,                 |
  |    public_key_sign,           |
  |    public_key_exchange}       |
  |                               |
  |<-- ACK -----------------------|
  |   {public_key_exchange}       |
  |                               |
  |=== SESSION ESTABLISHED =======|
```

## Security Properties

- Zero-knowledge: Server stores only **user_id** (PBKDF2-derived), never **master_secret**
- HMAC: **HMAC-SHA256(user_id, nonce)** proves knowledge of secret
- Ed25519: Signs HMAC to bind identity to cryptographic key
- Curve25519: Diffie-Hellman for forward-secure session key

## 3. Transport Protocol (TCP)

### Message Frame

```
[4 bytes: length (uint32, big-endian)] [N bytes: MessagePack payload]
```

### Message Structure

```json
{
  "version": 1,
  "type": "request|response|event|error",
  "id": "uuid-v4",
  "timestamp": 1234567890,
  "source": "agent_id",
  "target": "agent_id",
  "payload": {},
  "signature": "ed25519_hex",
  "ttl": 3600
}
```

### Encryption

- All post-handshake messages encrypted with AES-256-GCM (via NaCl SecretBox)
- Session key derived from Curve25519 Diffie-Hellman
- Each message has unique nonce (managed by NaCl)

## 4. Request/Response Pattern

### Request

```json
{
  "type": "request",
  "payload": {
    "task": "validate_contract",
    "data": { "contract_id": "12345" }
  }
}
```

### Response

```json
{
  "type": "response",
  "payload": {
    "request_id": "uuid-of-request",
    "success": true,
    "data": { "status": "approved" },
    "error": null
  }
}
```

## 5. Error Codes

| Code            | Description                   |
| --------------- | ----------------------------- |
| AUTH_FAILED     | Authentication failed         |
| UNKNOWN_TASK    | No handler for requested task |
| TIMEOUT         | Response timeout              |
| INVALID_MESSAGE | Malformed message             |
| INTERNAL_ERROR  | Server-side error             |
| PEER_NOT_FOUND  | Target peer not discovered    |
