import time
from fastapi import FastAPI
from exercise_01_schemas import ChatRequest, ChatResponse
from exercise_02_llm import get_chat_reply

app = FastAPI(title="RiverBank AI Service")

@app.get("/health")
def health():
    # Returns a 200 OK by default with this dictionary
    return {"status": "healthy"}

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    start = time.monotonic()
    
    # Delegate to the isolated AI logic
    reply = get_chat_reply(request.message, request.temperature)
    
    latency_ms = (time.monotonic() - start) * 1000
    
    return ChatResponse(
        reply=reply,
        model="llama-3.1-8b-instant",
        latency_ms=round(latency_ms, 2)
    )
