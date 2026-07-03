# BeekKon Bridge - Quick Start Guide

## Installation

```bash
pip install beekkon-bridge
```

## Create Your First Agent

```python
from beekkon import BeekKonAgent

# 1. Create an agent
agent = BeekKonAgent(
    name="my_agent",
    secret="my-super-secret-key-at-least-32-chars!!",
    capabilities=["process_data", "analyze"]
)

# 2. Register a handler
@agent.handler("process_data")
async def handle_process(data):
    result = sum(data.get("numbers", []))
    return {"sum": result}

# 3. Authorize peers (server-side)
agent.authorize_agent("client_agent", "client-secret-at-least-32-chars!!")

# 4. Start the agent
agent.start()
```

## Create a Client Agent

```python
from beekkon import BeekKonAgent
import time

client = BeekKonAgent(
    name="client_agent",
    secret="client-secret-at-least-32-chars!!",
    capabilities=[]
)

client.start(blocking=False)
time.sleep(3)  # Wait for discovery

# Send a request
response = client.request(
    target="my_agent",
    task="process_data",
    data={"numbers": [1, 2, 3, 4, 5]}
)

print(response)
# {'request_id': '...', 'success': True, 'data': {'sum': 15}, 'error': None}

client.stop()
```

## Using Memory (Shared Context)

```python
from beekkon import BeekKonMemory

memory = BeekKonMemory(db_path="./my_memory.db")

# Store shared context
memory.store(
    key="contract_123",
    value={"status": "draft", "amount": 10000},
    owner="legal_agent",
    readers=["legal_agent", "accounting_agent"],
    writers=["legal_agent"],
    ttl=86400  # 24 hours
)

# Retrieve
data = memory.retrieve("contract_123", "accounting_agent")
print(data)  # {'status': 'draft', 'amount': 10000}

# Cleanup
memory.close()
```

## Using Crypto Utilities

```python
from beekon import BeekKonCrypto

# Generate keys
signing_key, verify_key = BeekKonCrypto.generate_signing_keys()
private_key, public_key = BeekKonCrypto.generate_exchange_keys()

# Sign and verify
signature = BeekKonCrypto.sign(signing_key, b"important data")
is_valid = BeekKonCrypto.verify(verify_key, b"important data", signature)

# Encrypt and decrypt
shared_key = BeekKonCrypto.derive_shared_key(private_key, public_key)
encrypted = BeekKonCrypto.encrypt_with_shared_key(shared_key, b"secret")
decrypted = BeekKonCrypto.decrypt_with_shared_key(shared_key, encrypted)
```

### Next Steps

- Read the API Reference for full documentation
- Read the Protocol Specification for technical details
- Check the examples/ folder for real-world scenarios
