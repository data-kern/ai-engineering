import time
from fastapi import FastAPI
# TODO 0: You will need to import your schemas and llm function here!
# Uncomment these once you finish Exercise 1 and 2:
# from exercise_01_schemas import ChatRequest, ChatResponse
# from exercise_02_llm import get_chat_reply

# ==============================================================================
# EXERCISE 3: The Doors (FastAPI Endpoints)
#
# Goal: Build the actual HTTP API that consumers will call. 
# You will use the schemas from Exercise 1 and the logic from Exercise 2.
#
# To run this file: uvicorn exercise_03_main:app --reload
# To test it: open http://localhost:8000/docs
# ==============================================================================

# TODO 1: Initialize the FastAPI application.
app = FastAPI(title="RiverBank AI Service")

# TODO 2: Create a GET endpoint at "/health".
# It must return a dictionary: {"status": "healthy"}.
# Hint: use the @app.get() decorator.
# (Kubernetes will use this to know if your pod is alive!)
# -> Write your code below:



# TODO 3: Create a POST endpoint at "/api/v1/chat".
# It should accept a `request` of type `ChatRequest` and return a `ChatResponse`.
# Inside the function:
# 1. Record the start time (using time.monotonic())
# 2. Call `get_chat_reply(request.message, request.temperature)`
# 3. Calculate latency_ms
# 4. Return the ChatResponse object.
# -> Write your code below:


