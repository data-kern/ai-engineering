from pydantic import BaseModel

# ==============================================================================
# EXERCISE 1: The Bouncer (Pydantic Contracts)
#
# Goal: Define the exact shape of the data your API will accept and return.
# FastAPI will use these schemas to automatically validate incoming HTTP requests
# and reject bad ones (like missing fields) with a 422 error.
# ==============================================================================

# TODO 1: Create a class called `ChatRequest` that inherits from `BaseModel`.
# It needs two fields:
# - `message`: a required string.
# - `temperature`: a float with a default value of 0.7.
# -> Write your code below:



# TODO 2: Create a class called `ChatResponse` that inherits from `BaseModel`.
# It needs three fields:
# - `reply`: a string (the AI's response).
# - `model`: a string (the name of the model used).
# - `latency_ms`: a float (how long the request took).
# -> Write your code below:



if __name__ == "__main__":
    print("Schemas loaded successfully! Run `uvicorn exercise_03_main:app --reload` to test the full API.")
