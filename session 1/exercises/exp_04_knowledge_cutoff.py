"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 4: Knowledge Cutoff — The Limits of Training Data
=======================================================================

YOUR TASK:
  Demonstrate the "Knowledge Cutoff" by asking the model about a 
  highly publicized event that happened recently (after its training).
=======================================================================
"""

import os
import sys
from groq import Groq

if not os.environ.get("GROQ_API_KEY"):
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"


def run():
    # TODO: Step 1 - Craft the Prompt
    # System: "You are a helpful assistant."
    # User: Ask a question about a very recent event (e.g., a sports game that happened yesterday, a newly released movie, or today's stock price of Apple).
    SYSTEM_PROMPT = """
    
    """
    USER_PROMPT = """
    
    """

    # TODO: Step 2 - Make the API Call
    # Create the `messages` list using the prompts above.
    # Call the API and extract the response text.

    # ai_response = ...

    print("🤖 AI RESPONSE:")
    print("─" * 50)
    # print(ai_response) # Uncomment when ready
    print("─" * 50)


    # -----------------------------------------------------------------------
    # VARIANTS TO TRY AFTER YOU GET IT WORKING:
    # -----------------------------------------------------------------------
    # VARIANT A: Ask it what its own knowledge cutoff date is! 
    #            (User: "What is your knowledge cutoff date?")
    #
    # VARIANT B: Ask about a very obscure, highly technical, but OLD concept.
    #            Notice how it knows obscure old things perfectly, but fails 
    #            on massive recent events.

if __name__ == "__main__":
    run()
