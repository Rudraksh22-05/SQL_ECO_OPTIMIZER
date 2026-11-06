from fastapi import APIRouter, HTTPException

from app.schemas import QueryRequest
from app.services.executor import execute_query
from app.services.analyzer import analyze_plan
from app.services.optimizer import generate_suggestions
from app.services.benchmarker import benchmark_query
from app.database import get_connection
from app.services.index_manager import get_existing_index_columns

router = APIRouter()


@router.post("/analyze")
def analyze_query(request: QueryRequest):
    try:
        # 1. Execute and analyze the original query
        result = execute_query(request.query)

        analysis = analyze_plan(result["plan"])

        # Retrieve existing indexes from the analysis database
        connection = get_connection()

        try:
            existing_indexes = get_existing_index_columns(connection)
        finally:
            connection.close()

        suggestions = generate_suggestions(
            result["plan"],
            result["query"],
            existing_indexes=existing_indexes
        )

        benchmark_result = None

        # 2. Automatically benchmark index recommendations
        for suggestion in suggestions:

            if suggestion["type"] != "INDEX_RECOMMENDATION":
                continue

            table = suggestion.get("table")
            column = suggestion.get("column")

            if not table or not column:
                continue

            benchmark_result = benchmark_query(
                query=result["query"],
                table=table,
                column=column,
                runs=5
            )

            break

        # 3. Return complete analysis
        return {
            **result,
            "analysis": analysis,
            "suggestions": suggestions,
            "benchmark": benchmark_result
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print(f"Analysis error: {error}")

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )