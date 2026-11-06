from unittest.mock import MagicMock
from unittest.mock import patch
import pytest
from app.services.benchmarker import benchmark_query
from app.services.benchmarker import (
    calculate_improvement,
    run_multiple_measurements,
)

MOCK_BASELINE = {
    "runs": 5,
    "warmup_runs": 2,
    "execution_times_ms": [10.0, 9.0, 11.0, 10.0, 9.5],
    "planning_times_ms": [1.0, 1.0, 1.0, 1.0, 1.0],
    "median_execution_time_ms": 10.0,
    "median_planning_time_ms": 1.0,
    "plan": {
        "Node Type": "Seq Scan"
    }
}

MOCK_OPTIMIZED = {
    "runs": 5,
    "warmup_runs": 2,
    "execution_times_ms": [5.0, 4.5, 5.5, 5.0, 4.8],
    "planning_times_ms": [1.0, 1.0, 1.0, 1.0, 1.0],
    "median_execution_time_ms": 5.0,
    "median_planning_time_ms": 1.0,
    "plan": {
        "Node Type": "Bitmap Heap Scan"
    }
}

MOCK_ENVIRONMENT = {
    "database": "sql_eco_benchmark",
    "measurement_method": "EXPLAIN ANALYZE"
}

MOCK_IMPACT = {
    "energy_wh": 0.001,
    "energy_kwh": 0.000001,
    "carbon_grams_co2e": 0.0005
}


def test_calculate_improvement():
    improvement = calculate_improvement(
        baseline_time=10.0,
        optimized_time=5.0
    )

    assert improvement == 50.0


def test_calculate_improvement_no_change():
    improvement = calculate_improvement(
        baseline_time=10.0,
        optimized_time=10.0
    )

    assert improvement == 0.0


def test_calculate_improvement_degradation():
    improvement = calculate_improvement(
        baseline_time=5.0,
        optimized_time=10.0
    )

    assert improvement == -100.0


def test_calculate_improvement_zero_baseline():
    with pytest.raises(ValueError):
        calculate_improvement(
            baseline_time=0.0,
            optimized_time=5.0
        )


def test_run_multiple_measurements():
    connection = MagicMock()

    execution_results = [
        {
            "execution_time_ms": 10.0,
            "planning_time_ms": 1.0,
            "plan": {"Node Type": "Seq Scan"},
        },
        {
            "execution_time_ms": 8.0,
            "planning_time_ms": 1.0,
            "plan": {"Node Type": "Seq Scan"},
        },
        {
            "execution_time_ms": 6.0,
            "planning_time_ms": 1.0,
            "plan": {"Node Type": "Seq Scan"},
        },
    ]

    # We'll mock the benchmark execution function next.

def test_run_multiple_measurements():
    connection = MagicMock()

    mock_results = [
        {
            "execution_time_ms": 10.0,
            "planning_time_ms": 1.0,
            "plan": {"Node Type": "Seq Scan"},
        },
        {
            "execution_time_ms": 8.0,
            "planning_time_ms": 1.0,
            "plan": {"Node Type": "Seq Scan"},
        },
        {
            "execution_time_ms": 6.0,
            "planning_time_ms": 1.0,
            "plan": {"Node Type": "Seq Scan"},
        },
    ]

    with patch(
        "app.services.benchmarker.execute_benchmark_query",
        side_effect=mock_results
    ):
        result = run_multiple_measurements(
            connection=connection,
            query="SELECT * FROM employees",
            runs=3,
            warmup_runs=0
        )

    assert result["median_execution_time_ms"] == 8.0
    assert result["median_planning_time_ms"] == 1.0
    assert result["execution_times_ms"] == [10.0, 8.0, 6.0]
    assert result["plan"]["Node Type"] == "Seq Scan"
    

def test_benchmark_query_insufficient_improvement():
    mock_connection = MagicMock()

    mock_index_result = {
        "index_name": "eco_test_idx_employees_dept_id_low",
        "table": "employees",
        "column": "dept_id",
        "created": True
    }

    mock_saved_result = {
        "id": 102,
        "created_at": "2026-09-20T12:00:00"
    }

    mock_insights = {
        "summary": "Performance improvement: 2.00%",
        "improvement_percent": 2.0,
        "threshold_met": False,
        "insights": [],
        "cleanup_success": True
    }

    baseline = {
        **MOCK_BASELINE,
        "median_execution_time_ms": 10.0
    }

    optimized = {
        **MOCK_OPTIMIZED,
        "median_execution_time_ms": 9.8
    }

    with patch(
        "app.services.benchmarker.validate_query",
        return_value="SELECT * FROM employees WHERE dept_id = 5"
    ), patch(
        "app.services.benchmarker.get_benchmark_connection",
        return_value=mock_connection
    ), patch(
        "app.services.benchmarker.collect_benchmark_metadata",
        return_value=MOCK_ENVIRONMENT
    ), patch(
        "app.services.benchmarker.run_multiple_measurements",
        side_effect=[baseline, optimized]
    ), patch(
        "app.services.benchmarker.SafeIndexManager",
        autospec=True
    ) as mock_manager_class, patch(
        "app.services.benchmarker.estimate_environmental_impact",
        return_value=MOCK_IMPACT
    ), patch(
        "app.services.benchmarker.save_benchmark_result",
        return_value=mock_saved_result
    ), patch(
        "app.services.benchmarker.generate_benchmark_insights",
        return_value=mock_insights
    ):

        manager = mock_manager_class.return_value
        manager.create_test_index.return_value = mock_index_result
        manager.cleanup.return_value = [
            {
                "index_name": mock_index_result["index_name"],
                "dropped": True,
                "success": True
            }
        ]

        result = benchmark_query(
            query="SELECT * FROM employees WHERE dept_id = 5",
            table="employees",
            column="dept_id"
        )

        assert result["improvement_percent"] == pytest.approx(2.0)
        assert result["recommendation"]["meets_improvement_threshold"] is False
        assert (
            result["recommendation"]["decision"]
            == "INSUFFICIENT_PERFORMANCE_IMPROVEMENT"
        )
        assert result["cleanup"]["success"] is True