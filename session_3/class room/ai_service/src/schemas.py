from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    temperature:float = 0.7
    top_p:float = 0.9

    
class ChatResponse(BaseModel):
    reply:str
    model: str
    latency_ms:float