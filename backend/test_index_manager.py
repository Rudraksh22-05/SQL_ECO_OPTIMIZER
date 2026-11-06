import re
from unittest.mock import MagicMock, patch
from app.services.benchmarker import benchmark_query
import pytest

from app.services.index_manager import SafeIndexManager


import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_connection():
    connection = MagicMock()

    cursor = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    return connection

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

def test_validate_identifier_valid():
    SafeIndexManager.validate_identifier(
        "employees",
        "table name"
    )


@pytest.mark.parametrize(
    "identifier",
    [
        "",
        "employee table",
        "employees;",
        "employees--",
        "123employees",
    ]
)
def test_validate_identifier_invalid(identifier):
    with pytest.raises(ValueError):
        SafeIndexManager.validate_identifier(
            identifier,
            "table name"
        )


def test_validate_identifier_non_string():
    with pytest.raises(ValueError):
        SafeIndexManager.validate_identifier(
            123,
            "table name"
        )


def test_generate_test_index_name():
    manager = SafeIndexManager()

    index_name = manager.generate_test_index_name(
        "employees",
        "dept_id"
    )

    assert index_name.startswith("eco_test_idx_")
    assert "employees_dept_id_" in index_name
    assert len(index_name) <= 63
    assert re.fullmatch(
        r"[a-zA-Z_][a-zA-Z0-9_]*",
        index_name
    )


def test_validate_table_and_column_success():
    manager = SafeIndexManager()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    manager.validate_table_and_column(
        mock_connection,
        "employees",
        "dept_id"
    )

    mock_cursor.execute.assert_called_once()
    mock_cursor.fetchone.assert_called_once()


def test_validate_table_and_column_missing():
    manager = SafeIndexManager()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    with pytest.raises(ValueError, match="does not exist"):
        manager.validate_table_and_column(
            mock_connection,
            "employees",
            "missing_column"
        )


def test_create_test_index():
    manager = SafeIndexManager()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    with patch(
        "app.services.index_manager.get_benchmark_connection",
        return_value=mock_connection
    ):
        result = manager.create_test_index(
            "employees",
            "dept_id"
        )

    assert result["created"] is True
    assert result["table"] == "employees"
    assert result["column"] == "dept_id"
    assert result["index_name"] in manager.created_indexes

    mock_connection.commit.assert_called_once()
    mock_connection.close.assert_called_once()
    
def test_create_test_index_rollback():
    manager = SafeIndexManager()

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor.execute.side_effect = Exception(
        "Index creation failed"
    )

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    with patch(
        "app.services.index_manager.get_benchmark_connection",
        return_value=mock_connection
    ):
        with pytest.raises(Exception, match="Index creation failed"):
            manager.create_test_index(
                "employees",
                "dept_id"
            )

    mock_connection.rollback.assert_called_once()
    mock_connection.close.assert_called_once()
    assert len(manager.created_indexes) == 0

def test_drop_unmanaged_index_rejected():
    manager = SafeIndexManager()

    with pytest.raises(
        ValueError,
        match="Refusing to drop"
    ):
        manager.drop_test_index(
            "eco_test_idx_not_created_by_manager"
        )
        
def test_drop_test_index_success():
    manager = SafeIndexManager()
    index_name = "eco_test_idx_employees_dept_id_abc123"

    manager.created_indexes.add(index_name)

    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    with patch(
        "app.services.index_manager.get_benchmark_connection",
        return_value=mock_connection
    ):
        result = manager.drop_test_index(index_name)

    assert result["index_name"] == index_name
    assert result["dropped"] is True
    assert index_name not in manager.created_indexes

    mock_connection.commit.assert_called_once()
    mock_connection.close.assert_called_once()
    
    
def test_drop_test_index_rollback():
    manager = SafeIndexManager()
    index_name = "eco_test_idx_employees_dept_id_abc123"

    manager.created_indexes.add(index_name)

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception(
        "Index drop failed"
    )

    mock_connection = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    with patch(
        "app.services.index_manager.get_benchmark_connection",
        return_value=mock_connection
    ):
        with pytest.raises(Exception, match="Index drop failed"):
            manager.drop_test_index(index_name)

    mock_connection.rollback.assert_called_once()
    mock_connection.close.assert_called_once()

    # Failed cleanup should preserve tracking information.
    assert index_name in manager.created_indexes
    
def test_cleanup_multiple_indexes():
    manager = SafeIndexManager()

    index_names = {
        "eco_test_idx_employees_dept_id_abc123",
        "eco_test_idx_employees_salary_def456",
    }

    manager.created_indexes.update(index_names)

    with patch.object(
        manager,
        "drop_test_index",
        side_effect=lambda name: (
            manager.created_indexes.remove(name),
            {
                "index_name": name,
                "dropped": True
            }
        )[1]
    ):
        results = manager.cleanup()

    assert len(results) == 2
    assert all(item["success"] is True for item in results)
    assert manager.created_indexes == set()
    
    
def test_cleanup_continues_after_failure():
    manager = SafeIndexManager()

    first_index = "eco_test_idx_employees_dept_id_abc123"
    second_index = "eco_test_idx_employees_salary_def456"

    manager.created_indexes.update({
        first_index,
        second_index
    })

    def drop_with_failure(index_name):
        if index_name == first_index:
            raise Exception("Simulated drop failure")

        manager.created_indexes.remove(index_name)

        return {
            "index_name": index_name,
            "dropped": True
        }

    with patch.object(
        manager,
        "drop_test_index",
        side_effect=drop_with_failure
    ):
        results = manager.cleanup()

    assert len(results) == 2

    failed_results = [
        item for item in results
        if item["success"] is False
    ]

    successful_results = [
        item for item in results
        if item["success"] is True
    ]

    assert len(failed_results) == 1
    assert len(successful_results) == 1
    assert first_index in manager.created_indexes
    assert second_index not in manager.created_indexes
    
    
def test_benchmark_query_success():
    mock_connection = MagicMock()

    mock_index_result = {
        "index_name": "eco_test_idx_employees_dept_id_abc123",
        "table": "employees",
        "column": "dept_id",
        "created": True
    }

    mock_saved_result = {
        "id": 100,
        "created_at": "2026-09-20T12:00:00"
    }

    mock_insights = {
        "summary": "Performance improvement: 50.00%",
        "improvement_percent": 50.0,
        "threshold_met": True,
        "insights": [
            "Execution time decreased."
        ],
        "cleanup_success": True
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
        side_effect=[MOCK_BASELINE, MOCK_OPTIMIZED]
    ),  patch(
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

        mock_manager = mock_manager_class.return_value
        mock_manager.create_test_index.return_value = mock_index_result
        mock_manager.cleanup.return_value = [
            {
                "index_name": mock_index_result["index_name"],
                "dropped": True,
                "success": True
            }
        ]

        result = benchmark_query(
            query="SELECT * FROM employees WHERE dept_id = 5",
            table="employees",
            column="dept_id",
            runs=5
        )

    assert result["query"] == (
        "SELECT * FROM employees WHERE dept_id = 5"
    )

    assert result["storage"]["saved"] is True
    assert result["storage"]["benchmark_id"] == 100

    assert result["baseline"]["median_execution_time_ms"] == 10.0
    assert result["optimized"]["median_execution_time_ms"] == 5.0

    assert result["improvement_percent"] == 50.0

    assert result["recommendation"]["meets_improvement_threshold"] is True
    assert result["recommendation"]["decision"] == (
        "PERFORMANCE_IMPROVEMENT_CONFIRMED"
    )

    assert result["cleanup"]["success"] is True
    assert result["insights"] == mock_insights

    mock_manager.create_test_index.assert_called_once_with(
        "employees",
        "dept_id"
    )

    mock_manager.cleanup.assert_called_once()
    mock_connection.close.assert_called_once()

def test_benchmark_query_execution_failure():
    mock_connection = MagicMock()

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
        side_effect=RuntimeError("Benchmark execution failed")
    ), patch(
        "app.services.benchmarker.SafeIndexManager",
        autospec=True
    ) as mock_manager_class:

        manager = mock_manager_class.return_value

        with pytest.raises(RuntimeError, match="Benchmark execution failed"):
            benchmark_query(
                query="SELECT * FROM employees WHERE dept_id = 5",
                table="employees",
                column="dept_id"
            )

        mock_connection.rollback.assert_called()
        mock_connection.close.assert_called_once()
        manager.create_test_index.assert_not_called()
        manager.cleanup.assert_not_called()
        
        
def test_benchmark_query_index_creation_failure():
    mock_connection = MagicMock()

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
        return_value=MOCK_BASELINE
    ), patch(
        "app.services.benchmarker.SafeIndexManager",
        autospec=True
    ) as mock_manager_class:

        manager = mock_manager_class.return_value

        manager.create_test_index.side_effect = RuntimeError(
            "Index creation failed"
        )

        with pytest.raises(RuntimeError, match="Index creation failed"):
            benchmark_query(
                query="SELECT * FROM employees WHERE dept_id = 5",
                table="employees",
                column="dept_id"
            )

        mock_connection.rollback.assert_called()
        mock_connection.close.assert_called_once()
        manager.create_test_index.assert_called_once_with(
            "employees",
            "dept_id"
        )
        manager.cleanup.assert_not_called()


def test_benchmark_query_cleanup_failure():
    mock_connection = MagicMock()

    mock_index_result = {
        "index_name": "eco_test_idx_employees_dept_id_abc123",
        "table": "employees",
        "column": "dept_id",
        "created": True
    }

    mock_saved_result = {
        "id": 101,
        "created_at": "2026-09-20T12:00:00"
    }

    mock_insights = {
        "summary": "Performance improvement: 50.00%",
        "improvement_percent": 50.0,
        "threshold_met": True,
        "insights": [],
        "cleanup_success": False
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
        side_effect=[MOCK_BASELINE, MOCK_OPTIMIZED]
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
                "success": False,
                "error": "Cleanup failed"
            }
        ]

        result = benchmark_query(
            query="SELECT * FROM employees WHERE dept_id = 5",
            table="employees",
            column="dept_id"
        )

        assert result["cleanup"]["success"] is False
        assert result["cleanup"]["results"][0]["success"] is False

        manager.create_test_index.assert_called_once_with(
            "employees",
            "dept_id"
        )
        manager.cleanup.assert_called_once()
        mock_connection.close.assert_called_once()


def test_get_existing_indexes(mock_connection):
    manager = SafeIndexManager()

    cursor = (
        mock_connection
        .cursor.return_value
        .__enter__
        .return_value
    )

    cursor.fetchall.return_value = [
        (
            "idx_employees_salary",
            "employees",
            "CREATE INDEX idx_employees_salary "
            "ON public.employees USING btree (salary)"
        )
    ]

    with patch(
        "app.services.index_manager.get_benchmark_connection",
        return_value=mock_connection
    ):
        result = manager.get_existing_indexes("employees")

    assert len(result) == 1
    assert result[0]["index_name"] == "idx_employees_salary"
    assert result[0]["table"] == "employees"