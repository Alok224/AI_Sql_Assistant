"""
agents/sql_validator_agent.py

SQL Validator Agent: checks generated SQL before it's ever executed.

Unlike the other stubs in this step, the dangerous-statement / read-only
check below is real and active immediately -- safety checks shouldn't
wait for a "later step". Schema-aware checks (missing tables/columns,
malformed SQL) are still TODO and will be added once the Schema Agent's
real implementation lands.
"""

from __future__ import annotations

import re

from graph.state import GraphState, ValidationResult

# Statements that mutate or destroy data/schema. Blocked by default;
# a future "Allow write operations" toggle in the sidebar can pass
# allow_write_ops=True to permit them for a specific session.
DANGEROUS_KEYWORDS = [
    "DROP",
    "DELETE",
    "UPDATE",
    "ALTER",
    "TRUNCATE",
    "INSERT",
    "CREATE",
    "GRANT",
    "REVOKE",
]


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def sql_validator_node(state: GraphState, allow_write_ops: bool = False) -> GraphState:
    """Validates `state["generated_sql"]` before execution.

    Args:
        state: current graph state.
        allow_write_ops: if False (default / Read Only mode), any
            statement containing a dangerous keyword is rejected.

    TODO (later step): add schema-aware checks -- verify every table and
    column referenced in the SQL actually exists in state["schema_info"].
    """
    trace = state.get("agent_trace", [])
    trace.append("sql_validator_agent")

    sql = state.get("generated_sql", "")
    cleaned = _strip_comments(sql).strip()
    errors: list[str] = []

    if not cleaned:
        errors.append("Generated SQL is empty.")

    if not allow_write_ops:
        upper = cleaned.upper()
        found = [kw for kw in DANGEROUS_KEYWORDS if re.search(rf"\b{kw}\b", upper)]
        if found:
            errors.append(
                f"Statement contains disallowed keyword(s) in Read Only mode: "
                f"{', '.join(found)}"
            )

    is_valid = len(errors) == 0
    validation_result: ValidationResult = {
        "is_valid": is_valid,
        "is_read_only": not allow_write_ops,
        "errors": errors,
    }

    return {
        "validation_result": validation_result,
        "agent_trace": trace,
    }
