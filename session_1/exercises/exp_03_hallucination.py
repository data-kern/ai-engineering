"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 3: Hallucination — When the Model Lies Confidently
=======================================================================

YOUR TASK:
  Intentionally trick the AI into generating a detailed response about 
  something that does not exist. 
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
    # TODO: Step 1 - Craft a Hallucination Prompt
    # System: "You are a helpful and knowledgeable historian."
    # User: Ask the AI to write a detailed 3-paragraph summary of 
    #       "The Great Martian War of 2023". 
    #       (A completely fictional event)
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
    # VARIANT A: Try to FIX the hallucination! Change the SYSTEM prompt to:
    #            "You are a strict factual assistant. If you do not know the 
    #            answer, or if the premise of the question is false, reply 
    #            ONLY with 'I don't know'."
    #
    # VARIANT B: Ask about a completely fictional library in a real programming 
    #            language (e.g., "How do I use the Python 'quantum_django' library?")

if __name__ == "__main__":
    run()
