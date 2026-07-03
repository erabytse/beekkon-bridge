"""
Demo: Trigger the 3-agent workflow
This script is a CLIENT that orchestrates agents already running in other terminals.

Usage:
  Terminal 1: python agent_comptable.py
  Terminal 2: python agent_juridique.py
  Terminal 3: python agent_crm.py
  Terminal 4: python run_workflow.py  <-- this script
"""

from beekkon import BeekKonAgent
import time


def main():
    print("=" * 60)
    print("🎬 BeekKon Bridge - Workflow Client")
    print("=" * 60)
    print("\n💡 Make sure the 3 agents are already running:")
    print("   Terminal 1: python agent_comptable.py")
    print("   Terminal 2: python agent_juridique.py")
    print("   Terminal 3: python agent_crm.py")
    print()
    
    
    # Create a CLIENT agent (just to send requests)
    print("\n👤 Creating client agent...")
    client = BeekKonAgent(
        name="workflow_client",
        secret="workflow-client-super-secret-key-1234567890-abcdef-xyz",  # 54 chars
        capabilities=[],
        port=8768
    )
    
    # Authorize the CRM officer (we'll talk to it)
    client.authorize_agent("crm_officer", "crm-super-secret-key-0987654321-fedcba-xyz")
    
    # Start client (non-blocking)
    print("🚀 Starting workflow client...")
    client.start(blocking=False)
    
    # Wait for discovery
    print("   Waiting for agent discovery...")
    for i in range(10):
        peers = client.get_peers()
        if len(peers) >= 3:
            break
        print(f"   Discovered {len(peers)} peers... ({i+1}/10)")
        time.sleep(1)
    
    peers = client.get_peers()
    print(f"\n🔍 Discovered peers: {[p.agent_id for p in peers]}")
    
    if len(peers) < 3:
        print("\n⚠️  Not all agents discovered. Make sure all 3 are running.")
        print("   Continuing anyway...")
    
    # Check if CRM is available (use get_peers() instead of get_peer())
    crm_peer = next((p for p in peers if p.agent_id == "crm_officer"), None)
    
    if not crm_peer:
        print("\n❌ CRM Officer not found. Cannot continue.")
        print(f"   Available peers: {[p.agent_id for p in peers]}")
        client.stop()
        return
    
    print(f"✅ CRM Officer found at {crm_peer.ip}:{crm_peer.port}")
    
    # Trigger the workflow
    print("\n" + "=" * 60)
    print("🎯 Triggering workflow: New client onboarding")
    print("=" * 60)
    
    try:
        response = client.request(
            target="crm_officer",
            task="orchestrate_workflow",
            data={
                "client_name": "Acme Corporation",
                "project": "AI Integration Platform",
                "amount": 25000,
                "country": "FR"
            },
            timeout=30.0
        )
        
        print("\n" + "=" * 60)
        print("📊 Workflow Result:")
        print("=" * 60)
        
        if response.get("success"):
            print(f"   ✅ Client: {response.get('client')}")
            print(f"   📜 Contract: {response.get('contract_id')}")
            print(f"   📄 Invoice: {response.get('invoice_id')}")
            print(f"   💰 Total: {response.get('total')} EUR")
            print(f"   🎉 Status: {response.get('status')}")
            print("\n🏆 WORKFLOW SUCCESSFUL!")
        else:
            print(f"   ❌ Error: {response.get('error')}")
            print("\n💡 Check the agent terminals for details.")
    
    except TimeoutError:
        print("\n❌ Workflow timed out")
        print("💡 Make sure all agents are running and responsive")
    
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        print("💡 Check the agent terminals for details")
    
    # Cleanup
    print("\n🛑 Stopping workflow client...")
    client.stop()
    
    print("\n💡 The 3 agents are still running in their terminals.")
    print("   Press Ctrl+C in each terminal to stop them.")


if __name__ == "__main__":
    main()