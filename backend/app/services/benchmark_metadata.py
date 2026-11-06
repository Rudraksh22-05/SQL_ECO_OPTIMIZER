from datetime import datetime, timezone
import platform
import psycopg2
from app.services.carbon_estimator import (
    DEFAULT_POWER_WATTS,
    DEFAULT_CARBON_INTENSITY
)


def collect_benchmark_metadata(connection):
    """
    Collect metadata required for benchmark reproducibility.
    """

    with connection.cursor() as cursor:
        cursor.execute("SELECT version()")
        postgres_version = cursor.fetchone()[0]

        cursor.execute("SELECT current_database()")
        database_name = cursor.fetchone()[0]

    return {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "operating_system": platform.platform(),

        "python_version": platform.python_version(),

        "postgresql_version": postgres_version,

        "database_name": database_name,

        "benchmark_environment": "isolated_benchmark_database",

        "measurement_method": "EXPLAIN ANALYZE",

        "power_assumption_watts": DEFAULT_POWER_WATTS,

        "carbon_intensity_g_per_kwh": DEFAULT_CARBON_INTENSITY
    }