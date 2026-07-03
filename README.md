<img width="1664" height="928" alt="logo" src="https://github.com/user-attachments/assets/95f8e334-7b6a-4e66-aebd-49cd664d3abc" alt="BKB" />
<div align="center">
<strong><p><h3>The Protocol for AI Agents - Secure communication protocol for the
post-AI era.</h3></p></strong>

</div>

## 🎯 What is BeekKon-Bridge?

BeekKon Bridge is a peer-to-peer communication protocol designed specifically for AI agents. It provides:

- 🔐 **Zero-knowledge authentication** (based on CryptoLogin V2)
- 🔒 **End-to-end encryption** (AES-256-GCM via Curve25519)
- ✍️ **Message signatures** (Ed25519)
- 🔍 **Automatic peer discovery** (UDP broadcast)
- 🤖 **Simple high-level API** (5 lines of code)

## 🚀 Quick Start

### Install

```bash
pip install beekon-bridge
```

## Create an Agent

```python
from beekkon import BeekKonAgent

# Create agent
agent = BeekKonAgent(
    name="my_agent",
    secret="my-super-secret-key-1234567890",  # min 32 chars
    capabilities=["parse_data", "generate_report"]
)

# Register handler
@agent.handler("process_request")
async def handle_request(data):
    return {"result": "processed", "input": data}

# Start agent
agent.start()
```

## Request Another Agent

```python
from beekkon import BeekKonAgent

agent = BeekKonAgent(
    name="client_agent",
    secret="client-secret-0987654321",
    capabilities=[]
)

agent.start(blocking=False)

# Send request
response = agent.request(
    target="my_agent",
    task="process_request",
    data={"value": 42}
)

print(response)  # {'success': True, 'data': {'result': 'processed', ...}}
```

## 🎬 Real-World Example: 3-Agent Workflow

See the `examples/` folder for a complete workflow with 3 specialized agents:

- **CRM Officer** (`agent_crm.py`): Client relationship management
- **Legal Officer** (`agent_juridique.py`): Contract validation & compliance
- **Accounting Clerk** (`agent_comptable.py`): Invoice generation & VAT calculation

### Run the demo

```bash
# Terminal 1: Start Accounting Clerk
python examples/agent_comptable.py

# Terminal 2: Start Legal Officer
python examples/agent_juridique.py

# Terminal 3: Start CRM Officer
python examples/agent_crm.py

# Terminal 4: Trigger workflow
python examples/run_workflow.py
```

<img width="1756" height="940" alt="BKB_Shower" src="https://github.com/user-attachments/assets/9e8d3557-e323-43d2-830b-20a9628425f7" />


### What happens

1. Client requests onboarding via CRM
2. CRM asks Legal to validate the contract
3. Legal validates and stores contract in shared memory
4. CRM asks Accounting to generate invoice
5. Accounting retrieves contract, calculates VAT, issues invoice
6. CRM validates payment
7. Workflow completes ✅

## 🔐 Security Model

- Zero-knowledge: Server never stores master secrets, only derived user_ids
- E2E encryption: All messages encrypted with AES-256-GCM
- Forward secrecy: Session keys derived via Curve25519 Diffie-Hellman
- Message integrity: Ed25519 signatures on all messages
- Local-first: No cloud, no central server, 100% P2P

## 📊 Architecture

```
┌─────────────────────────────────────────────────────┐
│                  BeekKonAgent (API)                 │
│  - agent.start()                                    │
│  - agent.request(target, task, data)                │
│  - @agent.handler("task")                           │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              BeekKonDiscovery (UDP)                 │
│  - Automatic peer discovery                         │
│  - Capability-based filtering                       │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              BeekKonProtocol (TCP)                  │
│  - Handshake (zero-knowledge auth)                  │
│  - Encrypted communication (AES-256-GCM)            │
│  - Request/Response pattern                         │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                BeekKonAuth (Crypto)                 │
│  - Ed25519 signatures                               │
│  - Curve25519 key exchange                          │
│  - PBKDF2-HMAC-SHA512 key derivation                │
└─────────────────────────────────────────────────────┘
```

## 🧪 Tests

```bash
pytest tests/ -v
# 36 tests passed
```

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 📧 Contact

GitHub: https://github.com/erabytse/BeekKon-Bridge

Issues: https://github.com/erabytse/BeekKon-Bridge/issues
