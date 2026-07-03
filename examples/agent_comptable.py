"""
Accounting Clerk Agent
Handles invoice generation, VAT calculation, and financial validation
"""

from beekkon import BeekKonAgent, BeekKonMemory
import time


def main():
    # Initialize agent
    agent = BeekKonAgent(
    name="accounting_clerk",
    secret="accounting-super-secret-key-1234567890-abcdef-xyz",  # 53 chars
    capabilities=["calculate_vat", "generate_invoice", "validate_payment"],
    port=8767
)

    # Authorize peers
    agent.authorize_agent("crm_officer", "crm-super-secret-key-0987654321-fedcba-xyz")
    agent.authorize_agent("legal_officer", "legal-super-secret-key-1122334455-aabbcc-xyz")
    agent.authorize_agent("workflow_client", "workflow-client-super-secret-key-1234567890-abcdef-xyz") 
    
    # Shared memory for contracts
    memory = BeekKonMemory(db_path="./accounting_memory.db")
    
    # Handler: Calculate VAT
    @agent.handler("calculate_vat")
    async def handle_calculate_vat(data):
        amount = data.get("amount", 0)
        country = data.get("country", "FR")
        
        vat_rates = {
            "FR": 0.20,
            "DE": 0.19,
            "US": 0.0,
            "UK": 0.20
        }
        
        vat_rate = vat_rates.get(country, 0.20)
        vat_amount = amount * vat_rate
        total = amount + vat_amount
        
        print(f"   💰 VAT calculated: {amount} + {vat_amount} ({vat_rate*100}%) = {total}")
        
        return {
            "amount": amount,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "total": total,
            "currency": "EUR"
        }
    
    # Handler: Generate invoice
    @agent.handler("generate_invoice")
    async def handle_generate_invoice(data):
        contract_id = data.get("contract_id")
        
        # Retrieve contract from shared memory
        contract = memory.retrieve(f"contract_{contract_id}", "accounting_clerk")
        if not contract:
            return {"success": False, "error": "Contract not found"}
        
        # Calculate VAT
        vat_result = await handle_calculate_vat({
            "amount": contract.get("amount", 0),
            "country": contract.get("country", "FR")
        })
        
        # Generate invoice
        invoice = {
            "invoice_id": f"INV-{contract_id}",
            "contract_id": contract_id,
            "client": contract.get("client"),
            "amount": vat_result["amount"],
            "vat": vat_result["vat_amount"],
            "total": vat_result["total"],
            "currency": vat_result["currency"],
            "status": "issued"
        }
        
        # Store invoice in memory
        memory.store(
            key=f"invoice_{contract_id}",
            value=invoice,
            owner="accounting_clerk",
            readers=["accounting_clerk", "crm_officer", "legal_officer"],
            writers=["accounting_clerk"]
        )
        
        print(f"   📄 Invoice generated: {invoice['invoice_id']}")
        print(f"      Total: {invoice['total']} {invoice['currency']}")
        
        return {"success": True, "invoice": invoice}
    
    # Handler: Validate payment
    @agent.handler("validate_payment")
    async def handle_validate_payment(data):
        invoice_id = data.get("invoice_id")
        amount = data.get("amount", 0)
        
        # Retrieve invoice
        invoice = memory.retrieve(f"invoice_{invoice_id.split('-')[-1]}", "accounting_clerk")
        if not invoice:
            return {"success": False, "error": "Invoice not found"}
        
        if abs(invoice["total"] - amount) < 0.01:
            print(f"   ✅ Payment validated: {amount} {invoice['currency']}")
            return {"success": True, "status": "paid"}
        else:
            print(f"   ❌ Payment mismatch: expected {invoice['total']}, got {amount}")
            return {"success": False, "error": "Amount mismatch"}
    
    print("=" * 60)
    print("🧮 Accounting Clerk Agent")
    print(f"   Capabilities: {agent.capabilities}")
    print(f"   Port: {agent.port}")
    print("=" * 60)
    
    # Start agent (blocking)
    try:
        agent.start(blocking=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopping Accounting Clerk...")
        agent.stop()
        memory.close()


if __name__ == "__main__":
    main()