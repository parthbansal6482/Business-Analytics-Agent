import os
import sys
from unittest.mock import patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

import logging
logging.basicConfig(level=logging.INFO)

from agent.nodes.intent_classifier import intent_classifier
from agent.state import AgentState

def test_intent_classifier_followup():
    print("Testing Intent Classifier with follow-up (MOCKED LLM)...")
    
    # Mock state for a follow-up query
    state: AgentState = {
        "session_id": "test-session",
        "user_id": "test-user",
        "query": "What about the price?",
        "mode": "quick",
        "user_preferences": {},
        "conversation_history": [
            {"role": "user", "content": "Analyze my bluetooth speakers."},
            {"role": "assistant", "content": "I've analyzed your bluetooth speakers. They have good reviews but high competition from SoundMax."}
        ],
        "total_tokens_used": 0,
        "completed_nodes": []
    }
    
    # Run the classifier with mocked LLM and SSE
    with patch("agent.nodes.intent_classifier.call_llm_with_retry") as mock_llm, \
         patch("agent.nodes.intent_classifier.publish_step") as mock_sse:
        
        mock_llm.return_value = "MODE: quick\nINTENT: pricing review\nDATA_NEEDED: pricing\nCOMPLEXITY: simple"
        
        try:
            updated_state = intent_classifier(state)
            
            print("\n--- RESULTS ---")
            print(f"Original Query: {state['query']}")
            print(f"Updated Query: {updated_state['query']}")
            print(f"Mode: {updated_state['mode']}")
            print(f"Is Followup: {updated_state['is_followup']}")
            
            # Verify context is in updated_query
            if "Context from previous analysis" in updated_state['query']:
                print("\n✅ Context successfully prepended!")
            else:
                print("\n❌ Context NOT prepended!")
                
            if "What about the price?" in updated_state['query']:
                print("✅ Raw query preserved!")
            else:
                print("❌ Raw query lost!")
                
            # Verify the mock was called with the prepended context
            called_prompt = mock_llm.call_args[0][0]
            if "Context from previous analysis" in called_prompt:
                print("✅ LLM was called WITH context!")
            else:
                print("❌ LLM was called WITHOUT context!")
                
            # Verify token tracking
            if updated_state.get("total_tokens_used", 0) > 0:
                print(f"✅ Tokens tracked: {updated_state['total_tokens_used']}")
            else:
                print("❌ Tokens NOT tracked!")
                
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    # Ensure env vars are set if needed, though get_llm loads .env
    test_intent_classifier_followup()
