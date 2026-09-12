"""
=======================================================================
  DataKern AI Engineering Masterclass — Session 1
  EXPERIMENT 7: Temperature — Controlling Creativity
=======================================================================

YOUR TASK:
  Demonstrate how the `temperature` parameter changes the output.
  A low temperature (0.0) makes the model deterministic and boring.
  A high temperature (1.0+) makes the model creative and unpredictable.
=======================================================================
"""

import os
import sys
from groq import Groq

if not os.environ.get("GROQ_API_KEY"):
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"


def _call(system: str, user: str, temp: float, label: str = ""):
    print(f"\n📌 {label} (Temperature: {temp})\n{'─'*50}")
    
    # Notice we pass the `temperature` parameter here!
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system.strip()},
            {"role": "user",   "content": user.strip()},
        ],
        model=MODEL,
        temperature=temp, 
    )
    
    print(resp.choices[0].message.content)
    print(f"{'─'*50}\n")


def run():
    # TODO: Step 1 - The Prompt
    # Write a prompt asking the AI to "Write a 3-sentence creative story about a robot learning to paint."
    SYSTEM_PROMPT = "You are a creative writer."
    USER_PROMPT = """
    
    """

    # TODO: Step 2 - Call with Temperature 0.0 (Deterministic)
    # _call(SYSTEM_PROMPT, USER_PROMPT, temp=0.0, label="Low Temperature")
    
    # TODO: Step 3 - Call with Temperature 1.5 (Highly Creative)
    # _call(SYSTEM_PROMPT, USER_PROMPT, temp=1.5, label="High Temperature")


    # -----------------------------------------------------------------------
    # VARIANTS TO TRY AFTER YOU GET IT WORKING:
    # -----------------------------------------------------------------------
    # VARIANT A: Run the script 3 times in a row. Notice how the Temperature 0.0 
    #            story is almost identical every time, but the Temperature 1.5 
    #            story changes wildly.
    #
    # VARIANT B: Push the temperature to 2.0 (the maximum). Watch the model 
    #            completely break down into gibberish!

if __name__ == "__main__":
    run()
