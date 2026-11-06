
from fastapi import APIRouter, HTTPException, Query
from app.schemas import (
    BenchmarkHistoryResponse,
    BenchmarkDetailResponse,
    BenchmarkRequest
)
from app.services.benchmarker import benchmark_query
from app.services.benchmark_repository import (
    get_benchmark_results,
    get_benchmark_result_by_id,
    get_benchmark_summary
)

router = APIRouter()


@router.post("/benchmark")
def benchmark(request: BenchmarkRequest):
    try:
        return benchmark_query(
            query=request.query,
            table=request.table,
            column=request.column,
            runs=request.runs
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print(f"Benchmark error: {error}")

        raise HTTPException(
            status_code=500,
            detail="Benchmark execution failed."
        )




@router.get(
    "/benchmarks",
    response_model=BenchmarkHistoryResponse
)
def benchmark_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    table: str | None = Query(default=None, min_length=1),
    column: str | None = Query(default=None, min_length=1)
):
    try:
        results = get_benchmark_results(
            limit=limit,
            offset=offset,
            table=table,
            column=column
        )

        return {
            "count": len(results),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "returned": len(results)
            },
            "filters": {
                "table": table,
                "column": column
            },
            "results": results
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print(f"History retrieval error: {error}")

        raise HTTPException(
            status_code=500,
            detail="Could not retrieve benchmark history."
        )


@router.get("/benchmarks/summary")
def benchmark_summary(
    table: str | None = Query(default=None, min_length=1),
    column: str | None = Query(default=None, min_length=1)
):
    try:
        summary = get_benchmark_summary(
            table=table,
            column=column
        )

        return {
            "filters": {
                "table": table,
                "column": column
            },
            "summary": summary
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print(f"Benchmark summary retrieval error: {error}")

        raise HTTPException(
            status_code=500,
            detail="Could not retrieve benchmark summary."
        )


@router.get(
    "/benchmarks/{benchmark_id}",
    response_model=BenchmarkDetailResponse
)
def benchmark_detail(benchmark_id: int):
    try:
        result = get_benchmark_result_by_id(benchmark_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Benchmark result not found."
            )

        return result

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        print(f"Benchmark detail retrieval error: {error}")

        raise HTTPException(
            status_code=500,
            detail="Could not retrieve benchmark result."
        )


