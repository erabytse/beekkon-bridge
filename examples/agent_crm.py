"""
CRM Officer Agent
Handles client relationships and orchestrates workflows
"""

from beekkon import BeekKonAgent
import time


def main():
    # Initialize agent
    agent = BeekKonAgent(
    name="crm_officer",
    secret="crm-super-secret-key-0987654321-fedcba-xyz",  # 47 chars 
    capabilities=["create_lead", "manage_client", "orchestrate_workflow"],
    port=8765
)

    # Authorize peers
    agent.authorize_agent("accounting_clerk", "accounting-super-secret-key-1234567890-abcdef-xyz")
    agent.authorize_agent("legal_officer", "legal-super-secret-key-1122334455-aabbcc-xyz")
    agent.authorize_agent("workflow_client", "workflow-client-super-secret-key-1234567890-abcdef-xyz") 
    
    # Handler: Create lead
    @agent.handler("create_lead")
    async def handle_create_lead(data):
        client_name = data.get("client_name")
        project = data.get("project")
        
        print(f"   👤 New lead: {client_name} - {project}")
        
        return {
            "success": True,
            "lead_id": f"LEAD-{int(time.time())}",
            "client": client_name,
            "project": project,
            "status": "new"
        }
    
    # Handler: Orchestrate workflow (full client onboarding)
    @agent.handler("orchestrate_workflow")
    async def handle_orchestrate_workflow(data):
        client_name = data.get("client_name")
        project = data.get("project")
        amount = data.get("amount", 10000)
        country = data.get("country", "FR")
        
        print(f"\n🔄 Starting workflow for {client_name}")
        print(f"   Project: {project}")
        print(f"   Amount: {amount} {country}")
        
        # Step 1: Request legal validation
        print("\n📋 Step 1: Requesting legal validation...")
        try:
            legal_response = agent.request(
                target="legal_officer",
                task="validate_contract",
                data={
                    "client": client_name,
                    "project": project,
                    "amount": amount,
                    "country": country
                },
                timeout=10.0
            )
            
            if not legal_response.get("success"):
                return {"success": False, "error": "Legal validation failed"}
            
            contract_id = legal_response["data"]["contract_id"]
            print(f"   ✅ Contract validated: {contract_id}")
        
        except Exception as e:
            print(f"   ❌ Legal validation error: {e}")
            return {"success": False, "error": str(e)}
        
        # Step 2: Request invoice generation
        print("\n📋 Step 2: Requesting invoice generation...")
        try:
            invoice_response = agent.request(
                target="accounting_clerk",
                task="generate_invoice",
                data={"contract_id": contract_id},
                timeout=10.0
            )
            
            if not invoice_response.get("success"):
                return {"success": False, "error": "Invoice generation failed"}
            
            invoice = invoice_response["data"]["invoice"]
            print(f"   ✅ Invoice generated: {invoice['invoice_id']}")
        
        except Exception as e:
            print(f"   ❌ Invoice error: {e}")
            return {"success": False, "error": str(e)}
        
        # Step 3: Simulate payment validation
        print("\n📋 Step 3: Simulating payment validation...")
        try:
            payment_response = agent.request(
                target="accounting_clerk",
                task="validate_payment",
                data={
                    "invoice_id": invoice["invoice_id"],
                    "amount": invoice["total"]
                },
                timeout=10.0
            )
            
            if not payment_response.get("success"):
                return {"success": False, "error": "Payment validation failed"}
            
            print(f"   ✅ Payment validated")
        
        except Exception as e:
            print(f"   ❌ Payment error: {e}")
            return {"success": False, "error": str(e)}
        
        # Success!
        print("\n🎉 Workflow completed successfully!")
        
        return {
            "success": True,
            "client": client_name,
            "contract_id": contract_id,
            "invoice_id": invoice["invoice_id"],
            "total": invoice["total"],
            "status": "completed"
        }
    
    # Handler: Manage client (simple query)
    @agent.handler("manage_client")
    async def handle_manage_client(data):
        client_id = data.get("client_id")
        print(f"   🔍 Managing client: {client_id}")
        return {"success": True, "client_id": client_id, "status": "active"}
    
    print("=" * 60)
    print("👔 CRM Officer Agent")
    print(f"   Capabilities: {agent.capabilities}")
    print(f"   Port: {agent.port}")
    print("=" * 60)
    
    # Start agent (blocking)
    try:
        agent.start(blocking=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopping CRM Officer...")
        agent.stop()


if __name__ == "__main__":
    main()