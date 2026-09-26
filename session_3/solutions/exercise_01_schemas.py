from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    temperature: float = 0.7

class ChatResponse(BaseModel):
    reply: str
    model: str
    latency_ms: float

if __name__ == "__main__":
    print("Schemas loaded successfully! Run `uvicorn exercise_03_main:app --reload` to test the full API.")
