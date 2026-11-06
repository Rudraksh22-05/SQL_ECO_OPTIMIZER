from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)



VALID_REQUEST = {
    "query": "SELECT * FROM employees WHERE dept_id = 5",
    "table": "employees",
    "column": "dept_id",
    "runs": 5
}

MOCK_BENCHMARK_RESULT = {
    "id": 10,
    "query": "SELECT * FROM employees WHERE dept_id = 5",
    "table": "employees",
    "column": "dept_id",
    "baseline_time_ms": 5.0,
    "optimized_time_ms": 2.0,
    "improvement_percent": 60.0,
    "baseline_plan": {
        "Node Type": "Seq Scan"
    },
    "optimized_plan": {
        "Node Type": "Bitmap Heap Scan"
    },
    "benchmark_configuration": {
        "runs": 5,
        "warmup_runs": 2
    },
    "environment_metadata": {},
    "environmental_impact": {},
    "recommendation": {
        "decision": "PERFORMANCE_IMPROVEMENT_CONFIRMED"
    },
    "index_information": {},
    "cleanup_information": {
        "success": True
    },
    "created_at": datetime.now()
}

def test_benchmark_success():
    with patch(
        "app.routes.benchmark.benchmark_query",
        return_value=MOCK_BENCHMARK_RESULT
    ):
        response = client.post(
            "/api/benchmark",
            json=VALID_REQUEST
        )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 10
    assert data["table"] == "employees"
    assert data["column"] == "dept_id"
    assert data["improvement_percent"] == 60.0
    
def test_history_success():
    mock_history = [
        {
            "id": 10,
            "query": "SELECT * FROM employees WHERE dept_id = 5",
            "table": "employees",
            "column": "dept_id",
            "baseline_time_ms": 5.0,
            "optimized_time_ms": 2.0,
            "improvement_percent": 60.0,
            "environmental_impact": {
                "baseline": {
                    "carbon_grams_co2e": 0.001
                },
                "optimized": {
                    "carbon_grams_co2e": 0.0004
                }
            },
            "created_at": datetime.now()
        }
    ]

    with patch(
        "app.routes.benchmark.get_benchmark_results",
        return_value=mock_history
    ):
        response = client.get("/api/benchmarks")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["pagination"]["returned"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == 10


def test_summary_success():
    mock_summary = {
        "total_benchmarks": 5,
        "average_baseline_time_ms": 5.0,
        "average_optimized_time_ms": 2.5,
        "average_improvement_percent": 50.0,
        "maximum_improvement_percent": 70.0,
        "total_energy_saved_kwh": 0.00001,
        "total_carbon_saved_grams": 0.005
    }

    with patch(
        "app.routes.benchmark.get_benchmark_summary",
        return_value=mock_summary
    ):
        response = client.get("/api/benchmarks/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_benchmarks"] == 5
    assert data["summary"]["average_improvement_percent"] == 50.0

def test_detail_success():
    with patch(
        "app.routes.benchmark.get_benchmark_result_by_id",
        return_value=MOCK_BENCHMARK_RESULT
    ):
        response = client.get("/api/benchmarks/10")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 10
    assert data["query"].startswith("SELECT")
    assert data["cleanup_information"]["success"] is True

def test_benchmark_missing_query():
    request = VALID_REQUEST.copy()
    del request["query"]

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_empty_query():
    request = VALID_REQUEST.copy()
    request["query"] = ""

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_invalid_runs_zero():
    request = VALID_REQUEST.copy()
    request["runs"] = 0

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_invalid_runs_negative():
    request = VALID_REQUEST.copy()
    request["runs"] = -1

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_invalid_runs_too_high():
    request = VALID_REQUEST.copy()
    request["runs"] = 21

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_missing_table():
    request = VALID_REQUEST.copy()
    del request["table"]

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_missing_column():
    request = VALID_REQUEST.copy()
    del request["column"]

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 422


def test_benchmark_non_select_query():
    request = VALID_REQUEST.copy()
    request["query"] = "DELETE FROM employees"

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 400


def test_benchmark_multiple_statements():
    request = VALID_REQUEST.copy()
    request["query"] = (
        "SELECT * FROM employees; "
        "DROP TABLE employees"
    )

    response = client.post(
        "/api/benchmark",
        json=request
    )

    assert response.status_code == 400

def test_benchmark_detail_invalid_id():
    response = client.get(
        "/api/benchmarks/invalid"
    )

    assert response.status_code == 422


def test_benchmark_detail_negative_id():
    response = client.get(
        "/api/benchmarks/-1"
    )

    assert response.status_code in [400, 404, 422]


def test_benchmark_detail_not_found():
    with patch(
        "app.routes.benchmark.get_benchmark_result_by_id",
        return_value=None
    ):
        response = client.get(
            "/api/benchmarks/999999999"
        )

    assert response.status_code == 404

def test_history_invalid_limit():
    response = client.get(
        "/api/benchmarks?limit=0"
    )

    assert response.status_code == 422


def test_history_limit_above_maximum():
    response = client.get(
        "/api/benchmarks?limit=101"
    )

    assert response.status_code == 422


def test_history_negative_offset():
    response = client.get(
        "/api/benchmarks?offset=-1"
    )

    assert response.status_code == 422
    
def test_benchmark_internal_error():
    with patch(
        "app.routes.benchmark.benchmark_query",
        side_effect=Exception("Database connection failed")
    ):
        response = client.post(
            "/api/benchmark",
            json=VALID_REQUEST
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Benchmark execution failed."


def test_history_internal_error():
    with patch(
        "app.routes.benchmark.get_benchmark_results",
        side_effect=Exception("Database unavailable")
    ):
        response = client.get(
            "/api/benchmarks"
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Could not retrieve benchmark history."
    )


def test_summary_internal_error():
    with patch(
        "app.routes.benchmark.get_benchmark_summary",
        side_effect=Exception("Database unavailable")
    ):
        response = client.get(
            "/api/benchmarks/summary"
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Could not retrieve benchmark summary."
    )


def test_detail_internal_error():
    with patch(
        "app.routes.benchmark.get_benchmark_result_by_id",
        side_effect=Exception("Database unavailable")
    ):
        response = client.get(
            "/api/benchmarks/2"
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Could not retrieve benchmark result."
    )