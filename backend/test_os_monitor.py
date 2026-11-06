import time
from unittest.mock import patch

from app.services.os_monitor import OSResourceMonitor, _summary_from_samples


def _sample(t, cpu, memory, available, swap, disk_read, disk_write, pg_count=1, pg_rss=10, pg_cpu=2.0):
    return {
        "monotonic": t,
        "cpu_percent": cpu,
        "memory_percent": memory,
        "memory_available_bytes": available,
        "memory_total_bytes": 8 * 1024 * 1024 * 1024,
        "swap_percent": swap,
        "swap_used_bytes": 100,
        "swap_in_bytes_total": t * 100,
        "swap_out_bytes_total": t * 200,
        "disk": {
            "read_bytes": disk_read,
            "write_bytes": disk_write,
            "read_count": t * 10,
            "write_count": t * 20,
        },
        "postgres_process_count": pg_count,
        "postgres_rss_bytes": pg_rss * 1024 * 1024,
        "postgres_cpu_seconds_total": pg_cpu,
        "postgres_cpu_seconds_by_pid": {123: pg_cpu},
    }


def test_summary_calculates_system_metrics_and_counter_deltas():
    samples = [
        _sample(10, None, 40, 4 * 1024**3, 0, 1000, 2000, pg_cpu=2.0),
        _sample(10.5, 50, 45, 3 * 1024**3, 1, 1600, 2300, pg_cpu=2.2),
        _sample(11, 70, 50, 2 * 1024**3, 2, 2100, 2600, pg_cpu=2.5),
        _sample(11.1, None, 50, 2 * 1024**3, 2, 2200, 2700, pg_cpu=2.6),
    ]

    # Pin the platform so swap counter assertions behave the same on Windows.
    with patch("app.services.os_monitor.platform.system", return_value="Linux"):
        result = _summary_from_samples(samples, 0.5)

    assert result["available"] is True
    assert result["sample_count"] == 4
    assert result["cpu_sample_count"] == 2
    assert result["cpu_utilization_avg_percent"] == 60
    assert result["cpu_utilization_max_percent"] == 70
    assert result["memory_available_min_mb"] == 2048
    assert result["read_bytes_delta"] == 1200
    assert result["write_bytes_delta"] == 700
    assert result["swap_out_bytes_delta"] == 220
    assert result["postgres_local_process_metrics_available"] is True
    assert result["sampling_quality"] == "limited_cpu_samples"


def test_summary_marks_swap_counters_unsupported_on_windows():
    samples = [
        _sample(10, None, 40, 4 * 1024**3, 0, 1000, 2000),
        _sample(11, 50, 45, 3 * 1024**3, 1, 1600, 2300),
    ]

    with patch("app.services.os_monitor.platform.system", return_value="Windows"):
        result = _summary_from_samples(samples, 0.5)

    assert result["swap_io_counters_reliable"] is False
    assert result["swap_in_bytes_delta"] is None
    assert result["swap_out_bytes_delta"] is None


def test_summary_handles_unreadable_postgres_memory():
    samples = [
        dict(_sample(10, None, 40, 100, 0, 1, 1), postgres_rss_bytes=None),
        dict(_sample(11, 50, 40, 100, 0, 2, 2), postgres_rss_bytes=None),
    ]

    result = _summary_from_samples(samples, 0.5)

    assert result["postgres_local_process_metrics_available"] is True
    assert result["postgres_local_rss_avg_mb"] is None


def test_monitor_collects_real_samples():
    monitor = OSResourceMonitor(sample_interval_seconds=0.1)
    monitor.start()
    # Wait for the priming sample plus one CPU sample; slow hosts (e.g. Windows
    # with many processes) can take noticeably longer than the interval.
    deadline = time.monotonic() + 5
    while len(monitor._samples) < 2 and time.monotonic() < deadline:
        time.sleep(0.05)
    result = monitor.stop()

    assert result["available"] is True
    assert result["cpu_sample_count"] >= 1


def test_summary_handles_insufficient_samples():
    result = _summary_from_samples([_sample(1, None, 40, 100, 0, 1, 1)], 0.5)

    assert result["available"] is False
    assert result["sample_count"] == 1


def test_monitor_interval_is_validated():
    try:
        OSResourceMonitor(sample_interval_seconds=0.01)
    except ValueError as exc:
        assert "between 0.1 and 10" in str(exc)
    else:
        raise AssertionError("Invalid interval should raise ValueError")


def test_stop_before_start_is_safe():
    result = OSResourceMonitor().stop()
    assert result["available"] is False
    assert result["sample_count"] == 0


def test_collect_system_health_shape():
    from app.services.os_monitor import collect_system_health

    result = collect_system_health()

    assert "timestamp_utc" in result
    assert "cpu_utilization_percent" in result
    assert "memory" in result and "available_mb" in result["memory"]
    assert "swap" in result
    assert "local_postgresql_processes" in result