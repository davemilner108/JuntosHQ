"""RAG module for Ben's Counsel chatbot.

Queries the franklin_passages pgvector table using Ollama nomic-embed-text
(the same model used to seed the corpus via seed_franklin.py).

Falls back gracefully when Ollama is unavailable or the table is empty.
"""

import logging
import pathlib

from sqlalchemy import text

logger = logging.getLogger(__name__)

EMBED_MODEL = "nomic-embed-text"
FREE_TRIAL_LIMIT = 5

_SYSTEM_PROMPT_PATH = (
    pathlib.Path(__file__).parent.parent.parent / "scripts" / "ben_system_prompt.txt"
)


def _load_system_prompt() -> str:
    try:
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning("ben_system_prompt.txt not found, using minimal fallback")
        return (
            "You are Benjamin Franklin. Remain fully in character at all times. "
            "Never mention being an AI. Be witty, direct, practical, and concise."
        )


def _embed_query(query: str) -> list[float] | None:
    """Embed a query string with Ollama. Returns None on failure."""
    try:
        import ollama

        response = ollama.embed(model=EMBED_MODEL, input=[query])
        return response["embeddings"][0]
    except Exception as exc:
        logger.warning("Ollama embed failed (RAG disabled for this request): %s", exc)
        return None


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return top-k Franklin passages most relevant to query.

    Uses pgvector cosine similarity. Returns [] on any failure so the
    chatbot continues to work even without RAG context.
    """
    embedding = _embed_query(query)
    if embedding is None:
        return []

    # Format as pgvector literal: '[0.1,0.2,...]'
    emb_literal = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"

    try:
        from juntos.models import db

        with db.engine.connect() as conn:
            # Inline the embedding literal — it's pure floats so no injection risk.
            # SQLAlchemy's :name syntax clashes with psycopg's ::vector cast.
            sql = text(
                f"""
                SELECT content, source,
                       1 - (embedding <=> '{emb_literal}'::vector) AS similarity
                FROM franklin_passages
                ORDER BY embedding <=> '{emb_literal}'::vector
                LIMIT :k
                """
            )
            result = conn.execute(sql, {"k": top_k})
            return [
                {
                    "text": row.content,
                    "source": row.source,
                    "similarity": float(row.similarity),
                }
                for row in result
            ]
    except Exception as exc:
        logger.warning("pgvector search failed: %s", exc)
        return []


def build_system_prompt(
    junto=None,
    current_question: str | None = None,
    rag_passages: list[dict] | None = None,
) -> str:
    """Assemble full system prompt with RAG context and optional junto info."""
    parts = [_load_system_prompt()]

    if rag_passages:
        parts.append(
            "\n\n---\n"
            "The following passages from your own writings may be relevant to this conversation:\n"
        )
        for p in rag_passages:
            parts.append(f'[{p["source"]}] {p["text"]}')
        parts.append("---")

    if junto:
        parts.append(
            f'\n\nYou are speaking with a member of a modern junto called "{junto.name}".'
        )
        if junto.description:
            parts.append(f"Their junto's stated purpose: {junto.description}")

    if current_question:
        parts.append(
            f'\nThis week\'s Junto question for their group: "{current_question}"'
        )

    return "\n".join(parts)


def build_messages(
    history,
    user_message: str,
    junto=None,
    current_question: str | None = None,
) -> tuple[str, list[dict]]:
    """Build (system_prompt, messages) ready for the Anthropic API.

    Args:
        history: iterable of ChatMessage ORM objects (already in DB, excluding
                 the message we're about to send).
        user_message: the new user message text.
        junto: optional Junto ORM object for context injection.
        current_question: optional Franklin question of the week text.

    Returns:
        (system_prompt_str, messages_list) where messages_list is in
        Anthropic format: [{"role": "user"|"assistant", "content": str}, ...]
    """
    rag_passages = search(user_message)

    system = build_system_prompt(
        junto=junto,
        current_question=current_question,
        rag_passages=rag_passages,
    )

    # Cap at last 20 messages to control token cost
    recent = list(history)[-20:]
    messages = [{"role": m.role, "content": m.content} for m in recent]
    messages.append({"role": "user", "content": user_message})

    return system, messages
