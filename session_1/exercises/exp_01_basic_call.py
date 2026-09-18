"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 1: The Basic Call — "Hello World" for AI Engineering
=======================================================================

WHAT YOU WILL LEARN:
  How to make your first LLM API call by providing a System Prompt
  and a User Prompt.

YOUR TASK:
  Fill in the missing blocks below to complete the API call. 
  Follow the TODOs carefully.
=======================================================================
"""

import os
import sys
from groq import Groq

# -----------------------------------------------------------------------
# Guard: Check for API key before anything else
if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found.")
    print("   Run: export GROQ_API_KEY='your_key'")
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"


def run():
    # TODO: Step 1 - Define your Prompts
    # Create a system prompt telling the AI it is a friendly DataKern instructor 
    # who explains things to a 10-year-old using real-world analogies.
    SYSTEM_PROMPT = """
    
    """

    # Ask the AI to explain what a "variable" is in programming.
    USER_PROMPT = """
    
    """

    # TODO: Step 2 - Create the messages list
    # The 'messages' list needs two dictionaries:
    # 1. {"role": "system", "content": SYSTEM_PROMPT.strip()}
    # 2. {"role": "user", "content": USER_PROMPT.strip()}
    messages = [
        
    ]

    print("\n📤 SENDING REQUEST...")
    print(f"   Model: {MODEL}")
    print(f"   User:   {USER_PROMPT.strip()}\n")

    # TODO: Step 3 - Call the Groq API
    # Call `client.chat.completions.create(messages=messages, model=MODEL)`
    # Store the result in a variable named `response`
    
    # response = ...

    # TODO: Step 4 - Extract the text
    # Extract the string from `response.choices[0].message.content`
    # ai_response = ...

    print("🤖 AI RESPONSE:")
    print("─" * 50)
    # print(ai_response) # Uncomment when ready
    print("─" * 50)


    # -----------------------------------------------------------------------
    # VARIANTS TO TRY AFTER YOU GET IT WORKING:
    # -----------------------------------------------------------------------
    # VARIANT A: Change the SYSTEM_PROMPT to "You are a grumpy medieval wizard" 
    #            and run the script again. Notice how the tone shifts drastically!
    #
    # VARIANT B: Keep the wizard prompt, but change the USER_PROMPT to ask 
    #            "What is the best pizza topping?" 
    #            Notice how the AI stays in character even for off-topic questions.
    #
    # VARIANT C: Pass an EMPTY string to SYSTEM_PROMPT. Notice how the AI 
    #            reverts to its generic, default personality.

if __name__ == "__main__":
    run()
