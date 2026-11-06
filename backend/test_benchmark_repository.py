from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.benchmark_repository import (
    get_benchmark_results,
    get_benchmark_result_by_id,
    get_benchmark_summary,
)

MOCK_HISTORY_ROW = (
    1,
    "SELECT * FROM employees WHERE dept_id = 5",
    "employees",
    "dept_id",
    5.0,
    2.0,
    60.0,
    {
        "baseline": {
            "carbon_grams_co2e": 0.001
        },
        "optimized": {
            "carbon_grams_co2e": 0.0004
        }
    },
    datetime.now()
)

MOCK_DETAIL_ROW = (
    10,
    "SELECT * FROM employees WHERE dept_id = 5",
    "employees",
    "dept_id",
    5.0,
    2.0,
    60.0,
    {"Node Type": "Seq Scan"},
    {"Node Type": "Bitmap Heap Scan"},
    {"runs": 5, "warmup_runs": 2},
    {"database": "sql_eco_benchmark"},
    {
        "baseline": {"energy_kwh": 0.001},
        "optimized": {"energy_kwh": 0.0005},
    },
    {"decision": "PERFORMANCE_IMPROVEMENT_CONFIRMED"},
    {"created": True},
    {"success": True},
    datetime(2026, 9, 20, 12, 0, 0),
)

MOCK_SUMMARY_ROW = (
    5,          # total benchmarks
    5.0,        # average baseline time
    2.5,        # average optimized time
    50.0,       # average improvement
    70.0,       # maximum improvement
    0.001,      # baseline energy
    0.0005,     # optimized energy
    0.005,      # baseline carbon
    0.0025      # optimized carbon
)

def test_get_benchmark_results():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [MOCK_HISTORY_ROW]

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        results = get_benchmark_results()

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["table"] == "employees"
    assert results[0]["column"] == "dept_id"
    assert results[0]["improvement_percent"] == 60.0

    mock_cursor.execute.assert_called_once()
    mock_connection.close.assert_called_once()
    
        
def test_get_benchmark_results_with_filters():
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [MOCK_HISTORY_ROW]

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        results = get_benchmark_results(
            limit=10,
            offset=5,
            table="employees",
            column="dept_id"
        )

    assert len(results) == 1

    executed_query, executed_params = mock_cursor.execute.call_args.args

    assert "table_name = %s" in executed_query
    assert "column_name = %s" in executed_query
    assert "employees" in executed_params
    assert "dept_id" in executed_params
    
def test_history_invalid_limit():
    with pytest.raises(ValueError):
        get_benchmark_results(limit=0)


def test_history_invalid_offset():
    with pytest.raises(ValueError):
        get_benchmark_results(offset=-1)


def test_history_empty_table_filter():
    with pytest.raises(ValueError):
        get_benchmark_results(table="   ")
        
def test_get_benchmark_result_by_id():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = MOCK_DETAIL_ROW

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        result = get_benchmark_result_by_id(10)

    assert result is not None
    assert result["id"] == 10
    assert result["table"] == "employees"
    assert result["column"] == "dept_id"
    assert result["baseline_time_ms"] == 5.0
    assert result["optimized_time_ms"] == 2.0
    assert result["improvement_percent"] == 60.0
    assert result["cleanup_information"]["success"] is True

    mock_cursor.execute.assert_called_once()
    mock_connection.close.assert_called_once()


def test_get_benchmark_result_not_found():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        result = get_benchmark_result_by_id(99999)

    assert result is None
    mock_connection.close.assert_called_once()
    
def test_get_benchmark_result_invalid_id():
    with pytest.raises(ValueError):
        get_benchmark_result_by_id(0)


def test_get_benchmark_result_negative_id():
    with pytest.raises(ValueError):
        get_benchmark_result_by_id(-1)
        
def test_get_benchmark_result_database_error():
    mock_connection = MagicMock()
    mock_connection.cursor.side_effect = Exception("Database unavailable")

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        with pytest.raises(Exception, match="Database unavailable"):
            get_benchmark_result_by_id(10)

    mock_connection.close.assert_called_once()
    
    
def test_get_benchmark_summary():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = MOCK_SUMMARY_ROW

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        summary = get_benchmark_summary()

    assert summary["total_benchmarks"] == 5
    assert summary["average_baseline_time_ms"] == 5.0
    assert summary["average_optimized_time_ms"] == 2.5
    assert summary["average_improvement_percent"] == 50.0
    assert summary["maximum_improvement_percent"] == 70.0

    assert summary["total_energy_saved_kwh"] == 0.001
    assert summary["total_carbon_saved_grams"] == 0.0005

    mock_cursor.execute.assert_called_once()
    mock_connection.close.assert_called_once()
    
def test_get_benchmark_summary_with_filters():
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = MOCK_SUMMARY_ROW

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        summary = get_benchmark_summary(
            table="employees",
            column="dept_id"
        )

    assert summary["total_benchmarks"] == 5

    executed_query, executed_params = mock_cursor.execute.call_args.args

    assert "table_name = %s" in executed_query
    assert "column_name = %s" in executed_query
    assert "employees" in executed_params
    assert "dept_id" in executed_params
    
    
def test_summary_empty_table_filter():
    with pytest.raises(ValueError):
        get_benchmark_summary(table="   ")


def test_summary_empty_column_filter():
    with pytest.raises(ValueError):
        get_benchmark_summary(column="   ")
        
def test_summary_database_error():
    mock_connection = MagicMock()
    mock_connection.cursor.side_effect = Exception("Database unavailable")

    with patch(
        "app.services.benchmark_repository.get_benchmark_connection",
        return_value=mock_connection
    ):
        with pytest.raises(Exception, match="Database unavailable"):
            get_benchmark_summary()

    mock_connection.close.assert_called_once()
    
