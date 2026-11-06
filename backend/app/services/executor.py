
import re

from app.database import get_connection


def validate_query(query: str):
    query = query.strip()

    if not query:
        raise ValueError("Query cannot be empty.")

    # Allow only a single SQL statement.
    query_without_trailing_semicolon = query.rstrip(";").strip()

    if ";" in query_without_trailing_semicolon:
        raise ValueError("Multiple SQL statements are not allowed.")

    # First milestone: read-only SELECT queries.
    if not re.match(r"(?is)^SELECT\b", query_without_trailing_semicolon):
        raise ValueError("Only SELECT queries are allowed.")

    forbidden_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "COPY",
        "CALL",
        "DO",
    ]

    upper_query = query_without_trailing_semicolon.upper()

    for keyword in forbidden_keywords:
        if re.search(rf"\b{keyword}\b", upper_query):
            raise ValueError(
                f"Forbidden SQL keyword detected: {keyword}"
            )

    return query_without_trailing_semicolon


def execute_query(query: str):
    validated_query = validate_query(query)

    connection = get_connection()

    try:
        connection.set_session(
            readonly=True,
            autocommit=False
        )

        with connection.cursor() as cursor:
            explain_query = f"""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            {validated_query}
            """

            cursor.execute(explain_query)

            plan = cursor.fetchone()[0][0]

            return {
                "query": validated_query,
                "execution_time_ms": plan["Execution Time"],
                "planning_time_ms": plan["Planning Time"],
                "plan": plan,
            }

    finally:
        connection.rollback()
        connection.close()