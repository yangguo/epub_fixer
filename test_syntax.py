"""Quick syntax check for agent system"""
import sys

try:
    print("Checking agent_system modules...")
    
    import agent_system.validation_agent
    print("✓ validation_agent.py - OK")
    
    import agent_system.fixing_agent
    print("✓ fixing_agent.py - OK")
    
    import agent_system.custom_fix_agent
    print("✓ custom_fix_agent.py - OK")
    
    import agent_system.drm_agent
    print("✓ drm_agent.py - OK")
    
    import agent_system.orchestrator
    print("✓ orchestrator.py - OK")
    
    import agent_system.agent_config
    print("✓ agent_config.py - OK")
    
    print("\n✅ All modules loaded successfully!")
    
except SyntaxError as e:
    print(f"\n❌ Syntax Error: {e}")
    sys.exit(1)
except ImportError as e:
    print(f"\n⚠️  Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
