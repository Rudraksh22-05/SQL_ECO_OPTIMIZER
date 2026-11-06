import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Activity, Cpu, HardDrive, MemoryStick, RefreshCw, AlertCircle, Database } from "lucide-react";

const API_URL = "http://localhost:8000/api";

function formatNumber(value, digits = 1) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "N/A";
}

function formatBytes(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  if (number < 1024 * 1024) return `${formatNumber(number / 1024, 1)} KB`;
  return `${formatNumber(number / (1024 * 1024), 2)} MB`;
}

function MetricCard({ title, value, subtitle, icon }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-3 flex items-center gap-2 text-slate-400">
        {icon}
        <span className="text-sm">{title}</span>
      </div>
      <p className="text-2xl font-bold text-cyan-400">{value}</p>
      {subtitle && <p className="mt-2 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

export default function SystemMonitor() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await axios.get(`${API_URL}/system/health`);
      setHealth(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to retrieve OS metrics. Check that the backend is running and psutil is installed."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    axios.get(`${API_URL}/system/health`)
      .then((response) => {
        if (!cancelled) setHealth(response.data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "Unable to retrieve OS metrics. Check that the backend is running and psutil is installed."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const memory = health?.memory;
  const swap = health?.swap;
  const postgres = health?.local_postgresql_processes;
  const disk = health?.disk_io_counters_total_since_boot;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">OS Resource Profiler</h2>
          <p className="mt-1 text-sm text-slate-400">
            Current host-level resource conditions. These metrics provide context and are not attributed to a single SQL query.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm transition hover:border-cyan-400 disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          {loading ? "Refreshing..." : "Refresh Metrics"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {!health && loading && <p className="text-slate-400">Collecting system metrics...</p>}

      {health && (
        <>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">Operating System</p>
            <p className="mt-2 break-words font-medium">{health.operating_system}</p>
            <p className="mt-1 text-sm text-slate-500">
              {health.logical_cpu_count ?? "N/A"} logical CPUs · Sampled at {new Date(health.timestamp_utc).toLocaleString()}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="CPU Utilization"
              value={`${formatNumber(health.cpu_utilization_percent)}%`}
              subtitle="System-wide utilization during a short sampling interval"
              icon={<Cpu size={18} />}
            />
            <MetricCard
              title="Memory Used"
              value={`${formatNumber(memory?.used_percent)}%`}
              subtitle={`${formatNumber(memory?.available_mb)} MB available of ${formatNumber(memory?.total_mb)} MB`}
              icon={<MemoryStick size={18} />}
            />
            <MetricCard
              title="Swap Used"
              value={`${formatNumber(swap?.used_percent)}%`}
              subtitle={`${formatNumber(swap?.used_mb)} MB currently used${swap?.io_counters_reliable ? "" : " · swap-in/out counters unsupported on Windows"}`}
              icon={<Activity size={18} />}
            />
            <MetricCard
              title="Local PostgreSQL"
              value={postgres?.available ? `${postgres.process_count} process(es)` : "Not detected"}
              subtitle={
                !postgres?.available
                  ? "The database may be remote or process access may be restricted"
                  : postgres.rss_mb_total == null
                    ? "Memory not readable (run the backend as administrator to see service process memory)"
                    : `${formatNumber(postgres.rss_mb_total)} MB combined resident memory`
              }
              icon={<Database size={18} />}
            />
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-3 flex items-center gap-2">
              <HardDrive className="text-cyan-400" size={18} />
              <h3 className="font-semibold">Disk I/O Counters</h3>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-sm text-slate-400">Read since boot</p>
                <p className="mt-1 text-lg font-semibold">{formatBytes(disk?.read_bytes)}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Written since boot</p>
                <p className="mt-1 text-lg font-semibold">{formatBytes(disk?.write_bytes)}</p>
              </div>
            </div>
            <p className="mt-4 text-xs text-slate-500">
              These are cumulative system-wide counters, not rates and not PostgreSQL-only traffic. Benchmark-phase deltas are shown in saved benchmark details.
            </p>
          </div>

          <div className="rounded-xl border border-amber-800/70 bg-amber-950/20 p-4 text-sm text-amber-200">
            <strong>Interpretation:</strong> A single snapshot cannot establish that the OS caused a slow query. Use the separate baseline and optimized phase summaries, repeat measurements, and compare under similar system conditions.
          </div>
        </>
      )}
    </section>
  );
}
