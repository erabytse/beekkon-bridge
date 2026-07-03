"""
Legal Officer Agent
Handles contract validation, compliance checks, and legal documentation
"""

from beekkon import BeekKonAgent, BeekKonMemory
import time


def main():
    # Initialize agent
    agent = BeekKonAgent(
    name="legal_officer",
    secret="legal-super-secret-key-1122334455-aabbcc-xyz",  # 50 chars
    capabilities=["validate_contract", "check_compliance", "draft_legal_doc"],
    port=8766
)

    # Authorize peers
    agent.authorize_agent("crm_officer", "crm-super-secret-key-0987654321-fedcba-xyz")
    agent.authorize_agent("accounting_clerk", "accounting-super-secret-key-1234567890-abcdef-xyz")
    agent.authorize_agent("workflow_client", "workflow-client-super-secret-key-1234567890-abcdef-xyz") 

    
    # Shared memory for contracts
    memory = BeekKonMemory(db_path="./legal_memory.db")
    
    # Handler: Validate contract
    @agent.handler("validate_contract")
    async def handle_validate_contract(data):
        client = data.get("client")
        project = data.get("project")
        amount = data.get("amount", 0)
        country = data.get("country", "FR")
        
        print(f"\n📜 Validating contract:")
        print(f"   Client: {client}")
        print(f"   Project: {project}")
        print(f"   Amount: {amount}")
        print(f"   Country: {country}")
        
        # Simulate compliance checks
        compliance_checks = []
        
        # GDPR check for EU countries
        if country in ["FR", "DE", "UK"]:
            compliance_checks.append("GDPR compliance: ✅")
        
        # Amount threshold check
        if amount > 50000:
            compliance_checks.append("High-value review: ⚠️ Requires manager approval")
        else:
            compliance_checks.append("Amount threshold: ✅")
        
        # Client verification (simulated)
        compliance_checks.append("Client verification: ✅")
        
        for check in compliance_checks:
            print(f"   {check}")
        
        # Generate contract ID
        contract_id = f"CTR-{int(time.time())}"
        
        # Store contract in shared memory
        contract = {
            "contract_id": contract_id,
            "client": client,
            "project": project,
            "amount": amount,
            "country": country,
            "status": "validated",
            "compliance": compliance_checks,
            "validated_at": time.time(),
            "validated_by": "legal_officer"
        }
        
        memory.store(
            key=f"contract_{contract_id}",
            value=contract,
            owner="legal_officer",
            readers=["legal_officer", "accounting_clerk", "crm_officer"],
            writers=["legal_officer"]
        )
        
        print(f"   ✅ Contract stored: {contract_id}")
        
        return {
            "success": True,
            "contract_id": contract_id,
            "status": "validated",
            "compliance": compliance_checks
        }
    
    # Handler: Check compliance
    @agent.handler("check_compliance")
    async def handle_check_compliance(data):
        contract_id = data.get("contract_id")
        
        contract = memory.retrieve(f"contract_{contract_id}", "legal_officer")
        if not contract:
            return {"success": False, "error": "Contract not found"}
        
        print(f"   🔍 Compliance check for {contract_id}")
        
        return {
            "success": True,
            "contract_id": contract_id,
            "compliance": contract.get("compliance", []),
            "status": "compliant"
        }
    
    # Handler: Draft legal document
    @agent.handler("draft_legal_doc")
    async def handle_draft_legal_doc(data):
        doc_type = data.get("type", "nda")
        client = data.get("client")
        
        print(f"   📝 Drafting {doc_type} for {client}")
        
        return {
            "success": True,
            "doc_id": f"DOC-{int(time.time())}",
            "type": doc_type,
            "status": "drafted"
        }
    
    print("=" * 60)
    print("⚖️  Legal Officer Agent")
    print(f"   Capabilities: {agent.capabilities}")
    print(f"   Port: {agent.port}")
    print("=" * 60)
    
    # Start agent (blocking)
    try:
        agent.start(blocking=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopping Legal Officer...")
        agent.stop()
        memory.close()


if __name__ == "__main__":
    main()