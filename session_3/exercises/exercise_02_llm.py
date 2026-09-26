import os
import sys
from groq import Groq

# ==============================================================================
# EXERCISE 2: The Brain (Isolated AI Logic)
#
# Goal: Write the AI logic completely isolated from the web framework (FastAPI) 
# and the UI (Streamlit). This file takes strings and returns strings.
# ==============================================================================

# ── Guard: API key ──────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found. Run: export GROQ_API_KEY='your_key'\n")
    sys.exit(1)

# TODO 1: Initialize the Groq client here at the module level.
# (Why here? Creating it once at startup is faster than creating it on every request).
# -> Write your code below:
client = None 

# TODO 2: Write a function called `get_chat_reply`.
# It should take two parameters: `message` (str) and `temperature` (float).
# It should return a string (the AI's reply).
def get_chat_reply(message: str, temperature: float) -> str:
    # -> Write your code below to call Groq (use 'llama-3.1-8b-instant'):
    
    
    
    # -> Extract and return the reply content:
    return "..."

