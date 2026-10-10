"""
DataKern Session 5 Demo — Schema Definitions
Defines Pydantic models for multi-turn chats, access tiers, and enterprise RAG requests/responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class UserContext(BaseModel):
    user_id: str = "adv-101"
    name: str = "Alex Mercer"
    role: str = "Junior Advisor"
    access_tier: int = Field(1, ge=1, le=4, description="1: Public, 3: Senior Client Data, 4: Compliance")


class ChunkResult(BaseModel):
    id: int
    doc_title: str
    access_tier: int
    chunk_text: str
    vector_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    rrf_score: float = 0.0


class EnterpriseRAGRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    user_context: Optional[UserContext] = Field(default_factory=UserContext)
    chunk_strategy: str = "structural"
    use_hybrid: bool = True
    sanitize_input: bool = True
    top_k: int = 3


class EnterpriseRAGResponse(BaseModel):
    answer: str
    rewritten_query: Optional[str] = None
    was_rewritten: bool = False
    retrieved_chunks: List[ChunkResult]
    security_flagged: bool = False
    security_notes: Optional[str] = None
    latency_breakdown_ms: Dict[str, float] = Field(default_factory=dict)
