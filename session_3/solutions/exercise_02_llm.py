import os
import sys
from groq import Groq

# ── Guard: API key ──────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY"):
    print("\n❌ GROQ_API_KEY not found. Run: export GROQ_API_KEY='your_key'\n")
    sys.exit(1)

# Initialize the Groq client at the module level for efficiency
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_chat_reply(message: str, temperature: float) -> str:
    # Call the Groq API
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": message}],
        temperature=temperature
    )
    # Extract and return the string content
    return response.choices[0].message.content
