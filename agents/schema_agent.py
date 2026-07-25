"""
agents/schema_agent.py

Schema Agent: inspects the connected database and produces a trimmed-down
schema context (relevant tables, DDL, keys) for the SQL Generator.

Stub for now -- returns the full schema via LangChain's SQLDatabase
helper so the graph is runnable. The real version (next step) will:
  * accept the DB engine via dependency injection rather than a global,
  * select only tables relevant to the user's question,
  * cache schema per-connection to avoid re-inspecting on every turn.
"""

from __future__ import annotations

from graph.state import GraphState, SchemaInfo


def schema_node(state: GraphState, db) -> GraphState:
    """Builds schema context for the current query.

    Args:
        state: current graph state.
        db: a langchain_community.utilities.SQLDatabase instance, passed
            in by the graph builder rather than read from a global, so
            this node stays testable in isolation.

    TODO (next step): filter `table_ddl` down to only the tables relevant
    to `state["user_query"]`, and cache the result keyed by connection.
    """
    trace = state.get("agent_trace", [])
    trace.append("schema_agent")

    schema_info: SchemaInfo = {
        "relevant_tables": db.get_usable_table_names(),
        "table_ddl": db.get_table_info(),
        "primary_keys": {},
        "foreign_keys": {},
    }

    return {
        "schema_info": schema_info,
        "agent_trace": trace,
    }
