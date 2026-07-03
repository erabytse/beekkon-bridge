# BeekKon Bridge - API Reference

## BeekKonAgent

High-level API for creating AI agents.

### Constructor

```python
BeekKonAgent(
    name: str,           # Public agent identifier
    secret: str,         # Master secret (min 32 chars)
    capabilities: list,  # List of capability strings
    port: int = 8765,    # TCP port
    host: str = "0.0.0.0"
)
```

## Methods

| Method                               | Description                              |
| ------------------------------------ | ---------------------------------------- |
| start(blocking=True)                 | Start the agent (blocking or background) |
| stop()                               | Stop the agent                           |
| handler(task_name)                   | Decorator to register a task handler     |
| authorize_agent(name, secret)        | Authorize a remote agent                 |
| request(target, task, data, timeout) | Send request to another agent            |
| get_peers(capability=None)           | Get discovered peers                     |

## Decorators

```python
@agent.handler("task_name")
async def handle_task(data: dict) -> dict:
    return {"result": "ok"}
```

## BeekKonAuth

### Zero-knowledge authentication.

## Constructor

```python
BeekKonAuth(agent_id: str, master_secret: str)
```

## Methods

| Method                                     | Description                   |
| ------------------------------------------ | ----------------------------- |
| initiate_handshake()                       | Generate HELLO message        |
| generate_challenge()                       | Generate challenge nonce      |
| respond_to_challenge(id, nonce)            | Respond with HMAC + signature |
| verify_response(response, nonce, agent_id) | Verify challenge response     |
| establish_session(peer_public_key)         | Establish encrypted session   |
| encrypt(plaintext)                         | Encrypt with session key      |
| decrypt(ciphertext)                        | Decrypt with session key      |
| sign_message(message)                      | Sign with Ed25519             |
| verify_peer_signature(message, signature)  | Verify peer signature         |
| add_authorized_agent(agent_id, user_id)    | Authorize agent (server)      |

## BeekKonDiscovery

### P2P peer discovery via UDP broadcast.

## Constructor

```python
BeekKonDiscovery(
    agent_id: str,
    capabilities: list,
    port: int = 8765,
    public_key_sign: str = "",
    public_key_exchange: str = ""
)
```

## Methods

| Method                              | Description             |
| ----------------------------------- | ----------------------- |
| start()                             | Start discovery service |
| stop()                              | Stop discovery service  |
| get_peers(capability=None)          | Get discovered peers    |
| get_peer(agent_id)                  | Get specific peer       |
| update_trust_score(agent_id, score) | Update peer trust score |
| refresh_peers()                     | Remove dead peers       |

### Callbacks

```python
discovery.on_peer_discovered = lambda peer: print(f"Found: {peer.agent_id}")
discovery.on_peer_lost = lambda agent_id: print(f"Lost: {agent_id}")
```

## BeekKonMemory

### SQLite-based shared memory storage.

## Constructor

```python
BeekKonMemory(db_path: str = "./beekon_memory.db")
```

## Methods

| Method                                          | Description            |
| ----------------------------------------------- | ---------------------- |
| store(key, value, owner, readers, writers, ttl) | Store a value          |
| retrieve(key, agent_id)                         | Retrieve a value       |
| update(key, value, agent_id)                    | Update a value         |
| delete(key, agent_id=None)                      | Delete a value         |
| list_keys(owner=None)                           | List all keys          |
| cleanup_expired()                               | Remove expired entries |
| close()                                         | Close database         |

## BeekKonCrypto

### Cryptographic utilities.

## Static Methods

| Method                                   | Description                  |
| ---------------------------------------- | ---------------------------- |
| generate_signing_keys()                  | Generate Ed25519 key pair    |
| generate_exchange_keys()                 | Generate Curve25519 key pair |
| derive_shared_key(private, public)       | Diffie-Hellman shared key    |
| encrypt_with_shared_key(key, plaintext)  | AES-256-GCM encrypt          |
| decrypt_with_shared_key(key, ciphertext) | AES-256-GCM decrypt          |
| sign(signing_key, message)               | Ed25519 sign                 |
| verify(verify_key, message, signature)   | Ed25519 verify               |
| derive_key_from_password(password, salt) | PBKDF2 key derivation        |
| generate_random_bytes(length)            | Secure random bytes          |
| hash_data(data, algorithm)               | Hash data                    |

## BeekKonRouter

### Message routing with pattern matching.

## Methods

| Method                                | Description              |
| ------------------------------------- | ------------------------ |
| add_route(pattern, handler, priority) | Add routing rule         |
| add_middleware(middleware)            | Add middleware           |
| route(message)                        | Route a message          |
| register_request(request_id, future)  | Register pending request |
| resolve_request(request_id, response) | Resolve pending request  |

## Data Models

### BeekKonMessage

```python
BeekKonMessage(
    type: str,          # Message type
    source: str,        # Sender agent ID
    target: str = "*",  # Receiver agent ID
    payload: dict = {}, # Message content
    version: int = 1,   # Protocol version
    id: str = uuid4(),  # Unique message ID
    timestamp: int,     # Unix timestamp
    signature: str = "",# Ed25519 signature
    ttl: int = 3600     # Time-to-live
)
```

### PeerInfo

```python
PeerInfo(
    agent_id: str,
    ip: str,
    port: int,
    capabilities: list,
    public_key_sign: str,
    public_key_exchange: str,
    last_seen: float,
    trust_score: float = 0.5
)
```
