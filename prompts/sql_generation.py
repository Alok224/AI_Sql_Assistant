"""
prompts/sql_generation.py

Prompt template for the SQL Generator Agent. Kept separate from the agent
logic so the prompt can be tuned/versioned without touching graph code.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

DIALECT_NOTES = {
    "PostgreSQL": "Use standard PostgreSQL syntax. LIMIT/OFFSET for pagination.",
    "MySQL": "Use standard MySQL syntax. LIMIT/OFFSET for pagination. Backtick identifiers if needed.",
    "MariaDB": "Use MySQL-compatible syntax. LIMIT/OFFSET for pagination.",
    "SQL Server": "Use T-SQL syntax. Use TOP instead of LIMIT. Use square brackets for identifiers if needed.",
    "SQLite": "Use standard SQLite syntax. LIMIT/OFFSET for pagination.",
}

SYSTEM_TEMPLATE = """You are an expert SQL Generator agent in a multi-agent \
Agentic SQL Assistant. Your only job is to write a single, correct, \
read-only SQL query that answers the user's question.

Database dialect: {db_type}
Dialect notes: {dialect_notes}

Schema (only the relevant tables are shown):
{schema_ddl}

Rules:
- Use ONLY tables and columns that appear in the schema above. Never invent \
tables, columns, or joins.
- Return exactly ONE SQL statement.
- Default to read-only (SELECT) queries unless explicitly told otherwise.
- Do not wrap the query in markdown code fences.
- Do not include any explanation, only the SQL statement.
- If a previous attempt failed, the error is provided below -- fix the \
root cause, don't just repeat the same query.
"""

HUMAN_TEMPLATE = """User question: {user_query}

{retry_context}
SQL query:"""


def build_sql_generation_prompt() -> ChatPromptTemplate:
    """Returns the reusable ChatPromptTemplate for SQL generation."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_TEMPLATE),
            ("human", HUMAN_TEMPLATE),
        ]
    )


def format_retry_context(last_error: str | None, previous_sql: str | None) -> str:
    """Builds the retry-context block injected into the human prompt.

    Returns an empty string on the first attempt so the prompt doesn't
    mention retries that haven't happened yet.
    """
    if not last_error:
        return ""
    return (
        f"Your previous query failed.\n"
        f"Previous SQL: {previous_sql}\n"
        f"Database error: {last_error}\n"
        f"Generate a corrected query that avoids this error.\n"
    )
