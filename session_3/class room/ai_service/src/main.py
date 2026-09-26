import time
from fastapi import FastAPI
from src.schemas import ChatRequest, ChatResponse
from src.llm import get_chat_reply

app = FastAPI(title="River Bank AI Service", version="1.0.0")

@app.get("/api/v1/health")
def health():
    return {"status":"ok","service":"ai_service"}

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    start_time = time.monotonic()
    reply ,model_used = get_chat_reply(
        message=request.message, 
        temperature=request.temperature, 
        top_p=request.top_p
        )
    latency_ms = round((time.monotonic() - start_time) * 1000, 2)
    return ChatResponse(
        reply=reply, 
        model=model_used, 
        latency_ms=latency_ms
    )