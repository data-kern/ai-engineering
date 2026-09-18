"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 5: Statelessness — The AI Has No Memory
=======================================================================

YOUR TASK:
  Demonstrate that the API is "stateless". Every call is a blank slate.
  To give the AI "memory", you must manually pass the entire history
  of the conversation back to it every single time.
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
    print("\n--- Part A: The Amnesia Test ---")
    
    # TODO: Step 1 - Call 1 (Setting the state)
    # We ask the AI to remember a simple fact.
    messages_1 = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi! My secret code is 42. Please remember this."}
    ]
    
    # Make the API call using messages_1 and print the response
    # resp1 = client.chat.completions.create(...)
    # print("AI:", resp1.choices[0].message.content)

    # TODO: Step 2 - Call 2 (The forgotten state)
    # We create a BRAND NEW messages array. We DO NOT include the history.
    # Ask the AI what your secret code is.
    messages_2 = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is my secret code?"}
    ]
    
    # Make the API call using messages_2 and print the response. 
    # Notice how it has no idea what your code is!
    # resp2 = client.chat.completions.create(...)
    # print("AI:", resp2.choices[0].message.content)


    print("\n--- Part B: Fixing the Memory ---")

    # TODO: Step 3 - Call 3 (Passing the History)
    # To fix this, we must pass the ENTIRE conversation history in the messages array.
    # The array should look like this:
    # 1. System: "You are a helpful assistant"
    # 2. User: "Hi! My secret code is 42..."
    # 3. Assistant: [Whatever the AI replied in Call 1]
    # 4. User: "What is my secret code?"
    
    messages_3 = [
        # Fill this in! Notice we use the "assistant" role to pass the AI's previous reply.
    ]

    # Make the API call using messages_3 and print the response.
    # It should now correctly remember your secret code!
    # resp3 = client.chat.completions.create(...)
    # print("AI:", resp3.choices[0].message.content)


if __name__ == "__main__":
    run()
