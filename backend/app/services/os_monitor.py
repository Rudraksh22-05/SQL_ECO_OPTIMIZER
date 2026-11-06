"""Cross-platform operating-system resource monitoring for SQL benchmarks.

System-wide disk counters and CPU/memory measurements describe the host machine,
not a single SQL statement. PostgreSQL process metrics are available only when the
PostgreSQL server runs on this same machine and is visible to the current user.
"""

from __future__ import annotations

from datetime import datetime, timezone
import platform
import statistics
import threading
import time
from typing import Any

import psutil

_MIB = 1024 * 1024


def _postgres_process_stats() -> dict[str, Any]:
    """Return aggregate stats for locally visible PostgreSQL server processes."""
    process_count = 0
    rss_bytes = 0
    rss_visible = False
    cpu_seconds = 0.0
    cpu_by_pid: dict[int, float] = {}

    try:
        # Read only names while scanning every process; memory/CPU reads are slow on
        # Windows (access-denied fallbacks), so do them only for PostgreSQL processes.
        for process in psutil.process_iter(attrs=["name"]):
            try:
                name = (process.info.get("name") or "").lower()
                # Includes postgres.exe on Windows and postgres/postmaster on Linux.
                if "postgres" not in name and "postmaster" not in name:
                    continue

                process_count += 1
                with process.oneshot():
                    # On Windows the PostgreSQL service usually runs as NETWORK SERVICE,
                    # so a normal user may get AccessDenied for memory/CPU.
                    try:
                        rss_bytes += int(process.memory_info().rss)
                        rss_visible = True
                    except psutil.AccessDenied:
                        pass

                    try:
                        times = process.cpu_times()
                        process_cpu = float(times.user + times.system)
                        cpu_seconds += process_cpu
                        cpu_by_pid[int(process.pid)] = process_cpu
                    except psutil.AccessDenied:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                continue
    except (psutil.Error, OSError):
        pass

    return {
        "process_count": process_count,
        "rss_bytes": rss_bytes if rss_visible else None,
        "cpu_seconds_total": cpu_seconds,
        "cpu_seconds_by_pid": cpu_by_pid,
    }


def _disk_counters() -> dict[str, int] | None:
    try:
        counters = psutil.disk_io_counters()
        if counters is None:
            return None
        return {
            "read_bytes": int(counters.read_bytes),
            "write_bytes": int(counters.write_bytes),
            "read_count": int(counters.read_count),
            "write_count": int(counters.write_count),
        }
    except (psutil.Error, OSError, RuntimeError):
        # Windows can raise RuntimeError when no physical disk counters are exposed.
        return None


def _capture_sample(cpu_percent: float | None) -> dict[str, Any]:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    postgres = _postgres_process_stats()

    return {
        "monotonic": time.monotonic(),
        "cpu_percent": float(cpu_percent) if cpu_percent is not None else None,
        "memory_percent": float(memory.percent),
        "memory_available_bytes": int(memory.available),
        "memory_total_bytes": int(memory.total),
        "swap_percent": float(swap.percent),
        "swap_used_bytes": int(swap.used),
        "swap_in_bytes_total": int(swap.sin),
        "swap_out_bytes_total": int(swap.sout),
        "disk": _disk_counters(),
        "postgres_process_count": postgres["process_count"],
        "postgres_rss_bytes": postgres["rss_bytes"],
        "postgres_cpu_seconds_total": postgres["cpu_seconds_total"],
        "postgres_cpu_seconds_by_pid": postgres["cpu_seconds_by_pid"],
    }


def _counter_delta(first: dict[str, Any], last: dict[str, Any], key: str) -> int | None:
    first_value = first.get(key)
    last_value = last.get(key)
    if first_value is None or last_value is None:
        return None
    return max(0, int(last_value) - int(first_value))


def _summary_from_samples(
    samples: list[dict[str, Any]],
    sample_interval_seconds: float,
) -> dict[str, Any]:
    if len(samples) < 2:
        return {
            "available": False,
            "sample_count": len(samples),
            "sample_interval_seconds": sample_interval_seconds,
            "note": "Not enough samples were collected to calculate benchmark-window deltas.",
        }

    first, last = samples[0], samples[-1]
    cpu_values = [s["cpu_percent"] for s in samples if s.get("cpu_percent") is not None]
    memory_values = [s["memory_percent"] for s in samples if s.get("memory_percent") is not None]
    available_values = [s["memory_available_bytes"] for s in samples if s.get("memory_available_bytes") is not None]
    swap_values = [s["swap_percent"] for s in samples if s.get("swap_percent") is not None]
    postgres_rss_values = [s["postgres_rss_bytes"] for s in samples if s.get("postgres_rss_bytes") is not None]
    postgres_count_values = [s["postgres_process_count"] for s in samples]

    disk_start = first.get("disk") or {}
    disk_end = last.get("disk") or {}
    disk_delta = {
        f"{metric}_delta": _counter_delta(disk_start, disk_end, metric)
        for metric in ("read_bytes", "write_bytes", "read_count", "write_count")
    } if disk_start and disk_end else {
        "read_bytes_delta": None,
        "write_bytes_delta": None,
        "read_count_delta": None,
        "write_count_delta": None,
    }

    # Count CPU time only for PostgreSQL PIDs visible in both the first and last snapshots.
    # Child processes that start/stop during the window can therefore be under-counted.
    start_pids = first.get("postgres_cpu_seconds_by_pid") or {}
    end_pids = last.get("postgres_cpu_seconds_by_pid") or {}
    common_pids = set(start_pids) & set(end_pids)
    postgres_cpu_delta = sum(
        max(0.0, float(end_pids[pid]) - float(start_pids[pid]))
        for pid in common_pids
    ) if common_pids else None

    cpu_count = len(cpu_values)
    if cpu_count < 2:
        sampling_quality = "insufficient_cpu_samples"
    elif cpu_count < 4:
        sampling_quality = "limited_cpu_samples"
    else:
        sampling_quality = "multiple_cpu_samples"

    return {
        "available": True,
        "sample_count": len(samples),
        "cpu_sample_count": cpu_count,
        "sample_interval_seconds": sample_interval_seconds,
        "observed_duration_seconds": round(max(0.0, last["monotonic"] - first["monotonic"]), 3),
        "sampling_quality": sampling_quality,
        "cpu_utilization_avg_percent": round(statistics.mean(cpu_values), 2) if cpu_values else None,
        "cpu_utilization_max_percent": round(max(cpu_values), 2) if cpu_values else None,
        "memory_used_avg_percent": round(statistics.mean(memory_values), 2) if memory_values else None,
        "memory_used_max_percent": round(max(memory_values), 2) if memory_values else None,
        "memory_available_min_mb": round(min(available_values) / _MIB, 2) if available_values else None,
        "swap_used_avg_percent": round(statistics.mean(swap_values), 2) if swap_values else None,
        "swap_used_max_percent": round(max(swap_values), 2) if swap_values else None,
        "swap_in_bytes_delta": (
            _counter_delta(first, last, "swap_in_bytes_total")
            if platform.system() != "Windows" else None
        ),
        "swap_out_bytes_delta": (
            _counter_delta(first, last, "swap_out_bytes_total")
            if platform.system() != "Windows" else None
        ),
        "swap_io_counters_reliable": platform.system() != "Windows",
        **disk_delta,
        "disk_metrics_scope": "system-wide; not specific to PostgreSQL",
        "postgres_local_process_metrics_available": max(postgres_count_values, default=0) > 0,
        "postgres_local_process_count_max": max(postgres_count_values, default=0),
        "postgres_local_rss_avg_mb": round(statistics.mean(postgres_rss_values) / _MIB, 2) if postgres_rss_values else None,
        "postgres_local_rss_max_mb": round(max(postgres_rss_values) / _MIB, 2) if postgres_rss_values else None,
        "postgres_local_cpu_seconds_delta": round(postgres_cpu_delta, 4) if postgres_cpu_delta is not None else None,
        "postgres_process_metrics_note": (
            "Local PostgreSQL process metrics are approximate; they are unavailable if the database runs remotely "
            "or process access is restricted. CPU-time delta includes only PostgreSQL PIDs present in both edge snapshots."
        ),
        "interpretation_note": (
            "These values describe system conditions during the whole benchmark phase, not resources attributable "
            "to an individual SQL statement. Very short phases may have limited sampling coverage."
        ),
    }


class OSResourceMonitor:
    """Sample host-level metrics during one baseline or optimized benchmark phase."""

    def __init__(self, sample_interval_seconds: float = 0.5) -> None:
        if not 0.1 <= sample_interval_seconds <= 10:
            raise ValueError("sample_interval_seconds must be between 0.1 and 10.")
        self.sample_interval_seconds = float(sample_interval_seconds)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._samples: list[dict[str, Any]] = []

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("OS resource monitor is already running.")
        self._samples = []
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="sql-eco-os-monitor", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        # psutil's first non-blocking CPU reading is not meaningful; prime it in this thread.
        # psutil>=5.9.6 tracks this per thread, so concurrent monitors do not interfere.
        try:
            psutil.cpu_percent(interval=None)
            self._samples.append(_capture_sample(cpu_percent=None))
        except (psutil.Error, OSError, RuntimeError):
            pass
        while not self._stop_event.wait(self.sample_interval_seconds):
            try:
                cpu_percent = psutil.cpu_percent(interval=None)
                self._samples.append(_capture_sample(cpu_percent=cpu_percent))
            except (psutil.Error, OSError, RuntimeError):
                # Keep the monitor alive if an optional OS metric briefly fails.
                continue

    def stop(self) -> dict[str, Any]:
        if self._thread is None:
            return {
                "available": False,
                "sample_count": 0,
                "sample_interval_seconds": self.sample_interval_seconds,
                "note": "Monitor was not started.",
            }

        self._stop_event.set()
        self._thread.join(timeout=max(5.0, self.sample_interval_seconds * 4))
        if self._thread.is_alive():
            return {
                "available": False,
                "sample_count": len(self._samples),
                "sample_interval_seconds": self.sample_interval_seconds,
                "note": "Monitor sampling thread did not stop cleanly.",
            }

        # Final edge snapshot captures cumulative disk/swap counters for delta calculations.
        try:
            self._samples.append(_capture_sample(cpu_percent=None))
        except (psutil.Error, OSError, RuntimeError):
            pass
        return _summary_from_samples(self._samples, self.sample_interval_seconds)


def collect_system_health() -> dict[str, Any]:
    """Return a point-in-time system snapshot for the diagnostics endpoint."""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    postgres = _postgres_process_stats()
    disk = _disk_counters()

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "operating_system": platform.platform(),
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "cpu_utilization_percent": round(float(cpu_percent), 2),
        "memory": {
            "total_mb": round(memory.total / _MIB, 2),
            "available_mb": round(memory.available / _MIB, 2),
            "used_percent": round(float(memory.percent), 2),
        },
        "swap": {
            "total_mb": round(swap.total / _MIB, 2),
            "used_mb": round(swap.used / _MIB, 2),
            "used_percent": round(float(swap.percent), 2),
            "io_counters_reliable": platform.system() != "Windows",
        },
        "disk_io_counters_total_since_boot": disk,
        "disk_metrics_scope": "system-wide; counters are cumulative since boot",
        "local_postgresql_processes": {
            "available": postgres["process_count"] > 0,
            "process_count": postgres["process_count"],
            "rss_mb_total": (
                round(postgres["rss_bytes"] / _MIB, 2)
                if postgres["rss_bytes"] is not None else None
            ),
            "cpu_seconds_total": round(postgres["cpu_seconds_total"], 3),
        },
        "note": "Host metrics are contextual; they are not measurements attributable to one SQL statement.",
    }