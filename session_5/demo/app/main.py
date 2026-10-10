"""
DataKern Session 5 Demo — Enterprise RAG Microservice (FastAPI)
Exposes production HTTP endpoints with multi-turn query rewriting,
security-scoped hybrid retrieval, and prompt injection defenses.

Run via:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
from fastapi import FastAPI, HTTPException
from app.schema import EnterpriseRAGRequest, EnterpriseRAGResponse, ChatMessage, UserContext
from app.step2_rewrite import rewrite_query
from app.step3_hybrid_search import search_enterprise_chunks
from app.enterprise_pipeline import run_enterprise_rag

# Optional Phoenix tracing initialization
try:
    import phoenix as px
    from openinference.instrumentation.groq import GroqInstrumentor
    GroqInstrumentor().instrument()
    px.launch_app()
    print("[Phoenix] Observability active at http://localhost:6006")
except Exception:
    pass

app = FastAPI(
    title="Apex Financial — Enterprise RAG Service",
    description="DataKern Session 5: Advanced RAG with Hybrid RRF Search, Multi-turn History, and Access Scoping",
    version="2.0.0"
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "enterprise-rag",
        "session": 5,
        "features": [
            "hybrid_rrf_search",
            "query_rewriting",
            "access_control_scoping",
            "prompt_injection_defense",
            "phoenix_observability"
        ]
    }


@app.post("/api/v1/chat", response_model=EnterpriseRAGResponse)
def chat_endpoint(request: EnterpriseRAGRequest):
    """
    Main Enterprise RAG chat endpoint.
    Processes user request through the full 5-stage pipeline.
    """
    try:
        response = run_enterprise_rag(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/v1/rewrite")
def rewrite_endpoint(request: EnterpriseRAGRequest):
    """
    Diagnostic endpoint: see how query rewriter condenses conversation history.
    """
    history_dicts = [{"role": m.role, "content": m.content} for m in request.conversation_history]
    rewritten = rewrite_query(history_dicts, request.message)
    return {
        "original_message": request.message,
        "turns_in_history": len(request.conversation_history),
        "rewritten_query": rewritten
    }


@app.post("/api/v1/search/hybrid")
def search_endpoint(
    query: str,
    tier: int = 1,
    mode: str = "hybrid",
    top_k: int = 3
):
    """
    Direct search inspection endpoint: compare vector vs keyword vs hybrid results.
    """
    chunks = search_enterprise_chunks(
        query_text=query,
        user_tier=tier,
        top_k=top_k,
        mode=mode
    )
    return {
        "query": query,
        "mode": mode,
        "user_tier": tier,
        "results_count": len(chunks),
        "chunks": chunks
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
