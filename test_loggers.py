
import sys
import os
import pathlib

# Add backend to path
sys.path.append(str(pathlib.Path(__file__).parent / "backend"))

try:
    print("Testing utils.llm...")
    from backend.utils.llm import get_llm, call_llm_with_retry
    print("utils.llm imported.")
    
    print("Testing agent.nodes.intent_classifier...")
    from backend.agent.nodes.intent_classifier import intent_classifier
    print("intent_classifier imported.")
    
    # Test a dummy call if possible, or just check the globals
    import backend.utils.llm as llm
    if hasattr(llm, 'logger'):
        print(f"llm.logger is defined: {llm.logger}")
    else:
        print("llm.logger is NOT defined!")

    import backend.agent.nodes.intent_classifier as ic
    if hasattr(ic, 'logger'):
        print(f"ic.logger is defined: {ic.logger}")
    else:
        print("ic.logger is NOT defined!")

except Exception as e:
    import traceback
    traceback.print_exc()
