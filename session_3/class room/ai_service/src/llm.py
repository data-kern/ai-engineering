import os
from groq import Groq
from phoenix.otel import register
from openinference.instrumentation.groq import GroqInstrumentor

PHOENIX_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
MODEL_NAME = "openai/gpt-oss-120b"

tracer_provider = register(
    project_name = "riverbank-ai-service",
    endpoint = PHOENIX_ENDPOINT,
    
)

GroqInstrumentor().instrument(tracer_provider=tracer_provider)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_chat_reply(message: str, temperature: float, top_p: float) -> tuple[str, str]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role":"user","content":message}],
        temperature=temperature,
        top_p=top_p
    )
    return response.choices[0].message.content, response.model
