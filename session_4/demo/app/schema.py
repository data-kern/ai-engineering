"""
schema.py — Request and Response shapes for the API

Pydantic models define the shape of data coming in and going out.
FastAPI uses these automatically for input validation and API docs.

QuestionRequest  → what you POST to /ask or /ask/rag
AnswerResponse   → what the service returns
"""

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    """The shape of every incoming request."""
    question: str   # The advisor's question — required


class AnswerResponse(BaseModel):
    """The shape of every outgoing response."""
    question:        str        # The original question echoed back
    answer:          str        # The LLM's generated answer
    mode:            str        # "direct" or "rag" — which pipeline was used
    chunks_used:     list[str]  # Retrieved policy chunks (empty for direct mode)
    retrieved_count: int        # How many chunks were retrieved (0 for direct mode)
