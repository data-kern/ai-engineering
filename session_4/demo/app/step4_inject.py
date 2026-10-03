"""
step4_inject.py — Pipeline Step 4: Build the Augmented Prompt

This is the core of RAG — the retrieved policy chunks are injected
into the system prompt *before* the LLM sees the question.

This module builds two versions of the system prompt:

  build_direct_prompt()
    → no policy context
    → the LLM answers from training knowledge only
    → used by the /ask endpoint (to show what goes wrong)

  build_rag_prompt()
    → with retrieved policy chunks embedded
    → the LLM is instructed to ground its answer in the policy text
    → used by the /ask/rag endpoint (to show the solution)

WHY THIS WORKS:
  LLMs are instruction followers. If you give them the rules in the
  system prompt, they follow them. If you don't, they fall back on
  whatever general knowledge they were trained on — which does not
  include your private company policy.

  RAG is just: retrieve the right rules → put them in the prompt.
  The LLM does not need to be retrained or fine-tuned.

Usage:
    from app.step4_inject import build_direct_prompt, build_rag_prompt

    # Without policy context:
    prompt = build_direct_prompt(client_profile)

    # With retrieved policy chunks:
    prompt = build_rag_prompt(client_profile, policy_chunks)
"""


def build_direct_prompt(client_profile: str) -> str:
    """
    Build a system prompt WITHOUT any policy context.

    The LLM will answer based on its general financial training knowledge.
    It has no information about Apex Financial's specific rules.

    Args:
        client_profile: The client's name, risk category, and holdings.

    Returns:
        A system prompt string ready to send to the LLM.
    """
    return f"""You are a financial advisor assistant at Apex Financial.

CLIENT PROFILE:
{client_profile}

Answer the advisor's question based on your general financial knowledge.
Be specific and actionable in your recommendation.
"""


def build_rag_prompt(client_profile: str, policy_chunks: list[str]) -> str:
    """
    Build a system prompt WITH retrieved policy chunks injected.

    The chunks are formatted as numbered policy sections and placed
    directly in the system prompt. The LLM is instructed to ground
    its answer in these sections and cite the applicable rule.

    Args:
        client_profile: The client's name, risk category, and holdings.
        policy_chunks:  A list of chunk texts from step3_search.

    Returns:
        A system prompt string with policy context embedded — ready to
        send to the LLM. Print this to see exactly what the LLM receives.
    """
    formatted_chunks = "\n\n---\n\n".join(
        f"[Policy Section {i + 1}]\n{chunk}"
        for i, chunk in enumerate(policy_chunks)
    )

    return f"""You are a financial advisor assistant at Apex Financial.
You MUST follow the company's internal risk policy when making recommendations.

CLIENT PROFILE:
{client_profile}

RELEVANT POLICY SECTIONS (retrieved from internal policy documents):
{formatted_chunks}

Instructions:
- Your answer MUST comply with the policy sections above.
- If the policy restricts a recommendation, clearly state the restriction.
- Quote the specific policy rule that applies.
- Do not recommend anything that violates the client's risk category.
"""
