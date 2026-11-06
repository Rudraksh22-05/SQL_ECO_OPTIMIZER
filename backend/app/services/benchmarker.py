
import statistics

from psycopg2 import sql

from app.database import get_benchmark_connection
from app.services.executor import validate_query
from app.services.index_manager import SafeIndexManager
from app.services.carbon_estimator import (
    estimate_environmental_impact
)
from app.services.benchmark_metadata import (
    collect_benchmark_metadata
)
from app.services.benchmark_repository import (
    save_benchmark_result
)
from app.services.insight_generator import generate_benchmark_insights
from app.services.os_monitor import OSResourceMonitor




DEFAULT_RUNS = 5
DEFAULT_WARMUP_RUNS = 2
MINIMUM_IMPROVEMENT_PERCENT = 5.0
OS_MONITOR_INTERVAL_SECONDS = 0.25


def execute_benchmark_query(connection, query: str):
    """
    Execute a validated query with EXPLAIN ANALYZE
    and return execution metrics.
    """

    with connection.cursor() as cursor:
        explain_query = sql.SQL(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
        ).as_string(connection) + query

        cursor.execute(explain_query)

        plan = cursor.fetchone()[0][0]

        return {
            "execution_time_ms": plan["Execution Time"],
            "planning_time_ms": plan["Planning Time"],
            "plan": plan,
        }


def run_multiple_measurements(
    connection,
    query: str,
    runs: int = DEFAULT_RUNS,
    warmup_runs: int = DEFAULT_WARMUP_RUNS
):
    """
    Execute warm-up runs before collecting measurements.
    """

    if runs < 1:
        raise ValueError("Runs must be at least 1.")

    if warmup_runs < 0:
        raise ValueError("Warm-up runs cannot be negative.")

    # Warm-up executions are not included in measurements.
    for _ in range(warmup_runs):
        execute_benchmark_query(
            connection,
            query
        )

    measurements = []

    for _ in range(runs):
        result = execute_benchmark_query(
            connection,
            query
        )

        measurements.append(result)

    execution_times = [
        result["execution_time_ms"]
        for result in measurements
    ]

    planning_times = [
        result["planning_time_ms"]
        for result in measurements
    ]

    final_plan = measurements[-1]["plan"]

    return {
        "runs": runs,
        "warmup_runs": warmup_runs,
        "execution_times_ms": execution_times,
        "planning_times_ms": planning_times,
        "median_execution_time_ms": statistics.median(
            execution_times
        ),
        "median_planning_time_ms": statistics.median(
            planning_times
        ),
        "plan": final_plan
    }

def calculate_improvement(
    baseline_time,
    optimized_time
):
    if baseline_time <= 0:
        raise ValueError("Baseline execution time must be greater than zero.")

    return (
        (baseline_time - optimized_time)
        / baseline_time
    ) * 100



def benchmark_query(
    query: str,
    table: str,
    column: str,
    runs: int = DEFAULT_RUNS
):
    """
    Compare baseline and optimized query performance
    using a temporary test index in the benchmark database.

    Environment metadata and benchmark configuration are
    maintained separately.
    """

    validated_query = validate_query(query)

    if runs < 1:
        raise ValueError("Runs must be at least 1.")

    connection = get_benchmark_connection()
    manager = SafeIndexManager()

    # Configure the session before executing any SQL.
    connection.set_session(
        readonly=True,
        autocommit=False
    )

    # Collect environment-level metadata; copy it because OS metrics are added later.
    environment_metadata = dict(collect_benchmark_metadata(connection))

    connection.rollback()

    test_index_name = None
    baseline = None
    optimized = None
    index_result = None
    cleanup_results = []
    benchmark_error = None
    baseline_os_metrics = None
    optimized_os_metrics = None

    try:
        # Monitor host resources over the complete baseline phase. Because individual
        # SQL executions may take only milliseconds, these are phase-level context metrics.
        baseline_monitor = OSResourceMonitor(sample_interval_seconds=OS_MONITOR_INTERVAL_SECONDS)
        baseline_monitor.start()
        try:
            baseline = run_multiple_measurements(
                connection,
                validated_query,
                runs,
                DEFAULT_WARMUP_RUNS
            )
        finally:
            baseline_os_metrics = baseline_monitor.stop()

        baseline["os_metrics"] = baseline_os_metrics
        connection.commit()

        # Create temporary test index using the separate
        # benchmark index manager connection.
        index_result = manager.create_test_index(
            table,
            column
        )

        test_index_name = index_result["index_name"]

        # Capture a separate OS monitoring window for the indexed/optimized phase.
        optimized_monitor = OSResourceMonitor(sample_interval_seconds=OS_MONITOR_INTERVAL_SECONDS)
        optimized_monitor.start()
        try:
            optimized = run_multiple_measurements(
                connection,
                validated_query,
                runs,
                DEFAULT_WARMUP_RUNS
            )
        finally:
            optimized_os_metrics = optimized_monitor.stop()

        optimized["os_metrics"] = optimized_os_metrics
        connection.commit()

    except Exception as error:
        benchmark_error = error
        connection.rollback()

    finally:
        connection.rollback()
        connection.close()

        if test_index_name:
            cleanup_results = manager.cleanup()

    if benchmark_error:
        raise benchmark_error

    baseline_time = baseline["median_execution_time_ms"]
    optimized_time = optimized["median_execution_time_ms"]

    improvement = calculate_improvement(
        baseline_time,
        optimized_time
    )

    meets_improvement_threshold = (
        improvement is not None
        and improvement >= MINIMUM_IMPROVEMENT_PERCENT
    )

    baseline_environment = estimate_environmental_impact(
        baseline_time
    )

    optimized_environment = estimate_environmental_impact(
        optimized_time
    )

    energy_saving_percent = calculate_improvement(
        baseline_environment["energy_wh"],
        optimized_environment["energy_wh"]
    )

    carbon_saving_percent = calculate_improvement(
        baseline_environment["carbon_grams_co2e"],
        optimized_environment["carbon_grams_co2e"]
    )

    cleanup_success = all(
        result.get("success", False)
        for result in cleanup_results
    )
    

    environment_metadata["os_monitoring"] = {
        "sample_interval_seconds": OS_MONITOR_INTERVAL_SECONDS,
        "baseline": baseline_os_metrics,
        "optimized": optimized_os_metrics,
        "metrics_scope": "host-level during each complete benchmark phase",
    }

    # Benchmark-specific configuration is kept separate
    # from environment metadata.
    benchmark_configuration = {
        "runs": runs,
        "warmup_runs": DEFAULT_WARMUP_RUNS,
        "minimum_improvement_percent": (
            MINIMUM_IMPROVEMENT_PERCENT
        ),
        "measurement_method": "EXPLAIN ANALYZE",
        "index_strategy": "temporary_test_index"
    }
    
    # Save benchmark result in PostgreSQL.
    saved_result = save_benchmark_result(
        query=validated_query,
        table=table,
        column=column,
        baseline=baseline,
        optimized=optimized,
        improvement_percent=improvement,
        benchmark_configuration=benchmark_configuration,
        environment_metadata=environment_metadata,
        environmental_impact={
            "baseline": baseline_environment,
            "optimized": optimized_environment,
            "energy_saving_percent": energy_saving_percent,
            "carbon_saving_percent": carbon_saving_percent
        },
        recommendation={
            "minimum_improvement_percent": (
                MINIMUM_IMPROVEMENT_PERCENT
            ),
            "meets_improvement_threshold": (
                meets_improvement_threshold
            ),
            "decision": (
                "PERFORMANCE_IMPROVEMENT_CONFIRMED"
                if meets_improvement_threshold
                else "INSUFFICIENT_PERFORMANCE_IMPROVEMENT"
            )
        },
        index_information=index_result,
        cleanup_information={
            "success": cleanup_success,
            "results": cleanup_results
        }
    )
    
    insights = generate_benchmark_insights(
            baseline_plan=baseline["plan"],
            optimized_plan=optimized["plan"],
            baseline_time_ms=baseline_time,
            optimized_time_ms=optimized_time,
            improvement_percent=improvement,
            recommendation={
                "meets_improvement_threshold": meets_improvement_threshold
            },
            environmental_impact={
                "baseline": baseline_environment,
                "optimized": optimized_environment
            },
            cleanup_information={
                "success": cleanup_success,
                "results": cleanup_results
            }
        )

    return {
        "query": validated_query,
        
        "storage": {
            "saved": True,
            "benchmark_id": saved_result["id"],
            "created_at": saved_result["created_at"]
        },

        "benchmark_configuration": benchmark_configuration,

        "environment_metadata": environment_metadata,

        "index": index_result,

        "baseline": baseline,

        "optimized": optimized,

        "improvement_percent": improvement,

        "recommendation": {
            "minimum_improvement_percent": (
                MINIMUM_IMPROVEMENT_PERCENT
            ),
            "meets_improvement_threshold": (
                meets_improvement_threshold
            ),
            "decision": (
                "PERFORMANCE_IMPROVEMENT_CONFIRMED"
                if meets_improvement_threshold
                else "INSUFFICIENT_PERFORMANCE_IMPROVEMENT"
            )
        },

        "environmental_impact": {
            "baseline": baseline_environment,
            "optimized": optimized_environment,
            "energy_saving_percent": energy_saving_percent,
            "carbon_saving_percent": carbon_saving_percent
        },

        "cleanup": {
            "success": cleanup_success,
            "results": cleanup_results
        },
        
        "insights": insights,
    }