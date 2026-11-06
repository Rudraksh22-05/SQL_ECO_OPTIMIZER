
import json

from app.database import get_benchmark_connection


def save_benchmark_result(
    query: str,
    table: str,
    column: str,
    baseline: dict,
    optimized: dict,
    improvement_percent: float | None,
    benchmark_configuration: dict,
    environment_metadata: dict,
    environmental_impact: dict,
    recommendation: dict,
    index_information: dict | None,
    cleanup_information: dict | None
):
    connection = get_benchmark_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO benchmark_results (
                    query,
                    table_name,
                    column_name,
                    baseline_time_ms,
                    optimized_time_ms,
                    improvement_percent,
                    baseline_plan,
                    optimized_plan,
                    benchmark_configuration,
                    environment_metadata,
                    environmental_impact,
                    recommendation,
                    index_information,
                    cleanup_information
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb,
                    %s::jsonb, %s::jsonb, %s::jsonb,
                    %s::jsonb, %s::jsonb
                )
                RETURNING id, created_at
                """,
                (
                    query,
                    table,
                    column,
                    baseline["median_execution_time_ms"],
                    optimized["median_execution_time_ms"],
                    improvement_percent,
                    json.dumps(baseline["plan"]),
                    json.dumps(optimized["plan"]),
                    json.dumps(benchmark_configuration),
                    json.dumps(environment_metadata),
                    json.dumps(environmental_impact),
                    json.dumps(recommendation),
                    json.dumps(index_information),
                    json.dumps(cleanup_information)
                )
            )

            saved_result = cursor.fetchone()
            connection.commit()

            return {
                "id": saved_result[0],
                "created_at": saved_result[1].isoformat()
            }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()




def get_benchmark_results(
    limit: int = 20,
    offset: int = 0,
    table: str | None = None,
    column: str | None = None
):
    """Retrieve paginated benchmark history with optional filters."""

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    if offset < 0:
        raise ValueError("Offset must be greater than or equal to 0.")

    if table is not None and not table.strip():
        raise ValueError("Table filter cannot be empty.")

    if column is not None and not column.strip():
        raise ValueError("Column filter cannot be empty.")

    connection = get_benchmark_connection()

    try:
        with connection.cursor() as cursor:

            conditions = []
            parameters = []

            if table is not None:
                conditions.append("table_name = %s")
                parameters.append(table.strip())

            if column is not None:
                conditions.append("column_name = %s")
                parameters.append(column.strip())

            where_clause = ""

            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT
                    id,
                    query,
                    table_name,
                    column_name,
                    baseline_time_ms,
                    optimized_time_ms,
                    improvement_percent,
                    environmental_impact,
                    created_at
                FROM benchmark_results
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """

            parameters.extend([limit, offset])

            cursor.execute(query, parameters)

            rows = cursor.fetchall()

            results = []

            for row in rows:
                results.append({
                    "id": row[0],
                    "query": row[1],
                    "table": row[2],
                    "column": row[3],
                    "baseline_time_ms": row[4],
                    "optimized_time_ms": row[5],
                    "improvement_percent": row[6],
                    "environmental_impact": row[7],
                    "created_at": row[8].isoformat()
                })

            return results

    finally:
        connection.close()



def get_benchmark_result_by_id(benchmark_id: int):
    """Retrieve a complete benchmark result by its ID."""

    if benchmark_id < 1:
        raise ValueError("Benchmark ID must be greater than or equal to 1.")

    connection = get_benchmark_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    query,
                    table_name,
                    column_name,
                    baseline_time_ms,
                    optimized_time_ms,
                    improvement_percent,
                    baseline_plan,
                    optimized_plan,
                    benchmark_configuration,
                    environment_metadata,
                    environmental_impact,
                    recommendation,
                    index_information,
                    cleanup_information,
                    created_at
                FROM benchmark_results
                WHERE id = %s
                """,
                (benchmark_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "query": row[1],
                "table": row[2],
                "column": row[3],
                "baseline_time_ms": row[4],
                "optimized_time_ms": row[5],
                "improvement_percent": row[6],
                "baseline_plan": row[7],
                "optimized_plan": row[8],
                "benchmark_configuration": row[9],
                "environment_metadata": row[10],
                "environmental_impact": row[11],
                "recommendation": row[12],
                "index_information": row[13],
                "cleanup_information": row[14],
                "created_at": row[15].isoformat()
            }

    finally:
        connection.close()



def get_benchmark_summary(
    table: str | None = None,
    column: str | None = None
):
    """Retrieve aggregate benchmark statistics with optional filters."""

    if table is not None and not table.strip():
        raise ValueError("Table filter cannot be empty.")

    if column is not None and not column.strip():
        raise ValueError("Column filter cannot be empty.")

    connection = get_benchmark_connection()

    try:
        with connection.cursor() as cursor:

            conditions = []
            parameters = []

            if table is not None:
                conditions.append("table_name = %s")
                parameters.append(table.strip())

            if column is not None:
                conditions.append("column_name = %s")
                parameters.append(column.strip())

            where_clause = ""

            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT
                    COUNT(*) AS total_benchmarks,

                    COALESCE(AVG(baseline_time_ms), 0)
                        AS average_baseline_time_ms,

                    COALESCE(AVG(optimized_time_ms), 0)
                        AS average_optimized_time_ms,

                    COALESCE(AVG(improvement_percent), 0)
                        AS average_improvement_percent,

                    COALESCE(MAX(improvement_percent), 0)
                        AS maximum_improvement_percent,

                    COALESCE(
                        SUM(
                            (
                                environmental_impact
                                ->'baseline'
                                ->>'energy_kwh'
                            )::DOUBLE PRECISION
                            -
                            (
                                environmental_impact
                                ->'optimized'
                                ->>'energy_kwh'
                            )::DOUBLE PRECISION
                        ),
                        0
                    ) AS total_energy_saved_kwh,

                    COALESCE(
                        SUM(
                            (
                                environmental_impact
                                ->'baseline'
                                ->>'carbon_grams_co2e'
                            )::DOUBLE PRECISION
                            -
                            (
                                environmental_impact
                                ->'optimized'
                                ->>'carbon_grams_co2e'
                            )::DOUBLE PRECISION
                        ),
                        0
                    ) AS total_carbon_saved_grams

                FROM benchmark_results
                {where_clause}
            """

            cursor.execute(query, parameters)

            row = cursor.fetchone()

            return {
                "total_benchmarks": row[0],
                "average_baseline_time_ms": float(row[1]),
                "average_optimized_time_ms": float(row[2]),
                "average_improvement_percent": float(row[3]),
                "maximum_improvement_percent": float(row[4]),
                "total_energy_saved_kwh": float(row[5]),
                "total_carbon_saved_grams": float(row[6])
            }

    finally:
        connection.close()