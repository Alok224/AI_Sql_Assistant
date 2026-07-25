"""
agents/sql_generator_agent.py

SQL Generator Agent: turns (user question + schema context + dialect)
into a single SQL query, using the prompt defined in
prompts/sql_generation.py. Incorporates state["last_error"] on retries
so the model can self-correct instead of repeating the same mistake.
"""

from __future__ import annotations

import re

from graph.state import GraphState
from prompts.sql_generation import (
    DIALECT_NOTES,
    build_sql_generation_prompt,
    format_retry_context,
)

_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|```$", re.MULTILINE)


def _clean_sql(raw: str) -> str:
    """Strips markdown code fences and surrounding whitespace the LLM
    sometimes adds despite being told not to."""
    cleaned = _CODE_FENCE_RE.sub("", raw).strip()
    # Some models still prepend "SQL query:" etc. -- drop a leading label.
    cleaned = re.sub(r"^(sql query:|sql:)\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip().rstrip(";")


def sql_generator_node(state: GraphState, llm) -> GraphState:
    """Generates a SQL query for the current question.

    Args:
        state: current graph state. If `state["last_error"]` is set,
            this is a retry attempt and the prompt includes the previous
            error so the model can correct itself.
        llm: the chat model to use for generation, injected by the graph
            builder.
    """
    trace = state.get("agent_trace", [])
    trace.append("sql_generator_agent")

    db_type = state.get("db_type", "PostgreSQL")
    schema_ddl = state.get("schema_info", {}).get("table_ddl", "")
    retry_context = format_retry_context(
        state.get("last_error"), state.get("generated_sql")
    )

    prompt = build_sql_generation_prompt()
    messages = prompt.format_messages(
        db_type=db_type,
        dialect_notes=DIALECT_NOTES.get(db_type, ""),
        schema_ddl=schema_ddl,
        user_query=state["user_query"],
        retry_context=retry_context,
    )

    response = llm.invoke(messages)
    generated_sql = _clean_sql(response.content)

    return {
        "generated_sql": generated_sql,
        "agent_trace": trace,
    }
