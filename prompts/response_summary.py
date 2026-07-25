"""
prompts/response_summary.py

Prompt template for the Response Agent: turns SQL execution results into
a concise natural-language answer instead of a raw table dump.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_TEMPLATE = """You are the Response Agent in an Agentic SQL Assistant. \
Convert SQL query results into a short, natural-language answer for a \
business user who did not see the SQL or the raw table.

Rules:
- 1-3 sentences. Be concise and conversational.
- Mention concrete numbers from the data (counts, totals, notable values) \
when relevant.
- Do not mention SQL, queries, tables, or databases explicitly -- answer \
as if you simply know the answer.
- If the result set is empty, say so plainly and suggest a possible reason.
"""

HUMAN_TEMPLATE = """User question: {user_query}

Row count: {row_count}
Result preview (up to 10 rows, as CSV):
{data_preview}

Answer:"""


def build_response_summary_prompt() -> ChatPromptTemplate:
    """Returns the reusable ChatPromptTemplate for response summarization."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_TEMPLATE),
            ("human", HUMAN_TEMPLATE),
        ]
    )
