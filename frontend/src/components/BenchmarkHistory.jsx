import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useState } from "react";
import axios from "axios";
import {
  History,
  RefreshCw,
  AlertCircle,
  Search,
  X,
} from "lucide-react";

const API_URL = "http://localhost:8000/api";

function requestHistory(selectedTable, selectedColumn) {
  const table = selectedTable.trim() || undefined;
  const column = selectedColumn.trim() || undefined;

  return Promise.all([
    axios.get(`${API_URL}/benchmarks`, {
      params: { limit: 20, offset: 0, table, column },
    }),
    axios.get(`${API_URL}/benchmarks/summary`, {
      params: { table, column },
    }),
  ]);
}

function historyErrorMessage(err) {
  return (
    err.response?.data?.detail ||
    "Unable to retrieve benchmark history."
  );
}

function BenchmarkHistory() {
  const [benchmarks, setBenchmarks] = useState([]);
  const [summary, setSummary] = useState(null);

  const [tableFilter, setTableFilter] = useState("");
  const [columnFilter, setColumnFilter] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedBenchmark, setSelectedBenchmark] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const fetchHistory = async (selectedTable = tableFilter, selectedColumn = columnFilter) => {
    setLoading(true);
    setError("");

    try {
      const [historyResponse, summaryResponse] =
        await requestHistory(selectedTable, selectedColumn);

      setBenchmarks(historyResponse.data.results || []);
      setSummary(summaryResponse.data.summary || null);
    } catch (err) {
      setError(historyErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Initial load; state already starts as loading, so only update it on completion.
  useEffect(() => {
    let cancelled = false;

    requestHistory("", "")
      .then(([historyResponse, summaryResponse]) => {
        if (cancelled) return;
        setBenchmarks(historyResponse.data.results || []);
        setSummary(summaryResponse.data.summary || null);
      })
      .catch((err) => {
        if (!cancelled) setError(historyErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleClearAndRefresh = () => {
    setTableFilter("");
    setColumnFilter("");
    fetchHistory("", "");
  };

  const chartData = benchmarks.map((benchmark) => {
  const environmentalImpact =
    benchmark.environmental_impact;

  const baselineCarbon =
    Number(
      environmentalImpact?.baseline?.carbon_grams_co2e
    ) || 0;

  const optimizedCarbon =
    Number(
      environmentalImpact?.optimized?.carbon_grams_co2e
    ) || 0;

  return {
    id: `#${benchmark.id}`,
    baseline: Number(benchmark.baseline_time_ms),
    optimized: Number(benchmark.optimized_time_ms)      ,

    baselineCarbon,
    optimizedCarbon,
    carbonSaved: baselineCarbon - optimizedCarbon,
  };
});

  const fetchBenchmarkDetails = async (benchmarkId) => {
    setDetailLoading(true);
    setDetailError("");

    try {
      const response = await axios.get(
        `${API_URL}/benchmarks/${benchmarkId}`
      );

      setSelectedBenchmark(response.data);
    } catch (err) {
      setDetailError(
        err.response?.data?.detail ||
          "Unable to retrieve benchmark details."
      );
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="text-cyan-400" />
          <h2 className="text-xl font-semibold">
            Benchmark History
          </h2>
        </div>

        <button
          onClick={() => fetchHistory()}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm transition hover:border-cyan-400 disabled:opacity-50"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-4 flex items-center gap-2">
          <Search className="text-cyan-400" size={18} />
          <h3 className="font-semibold">Filter Benchmarks</h3>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm text-slate-400">
              Table Name
            </label>

            <input
              type="text"
              value={tableFilter}
              onChange={(event) =>
                setTableFilter(event.target.value)
              }
              placeholder="e.g. employees"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm outline-none focus:border-cyan-400"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-slate-400">
              Column Name
            </label>

            <input
              type="text"
              value={columnFilter}
              onChange={(event) =>
                setColumnFilter(event.target.value)
              }
              placeholder="e.g. dept_id"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-sm outline-none focus:border-cyan-400"
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            onClick={() => fetchHistory()}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-cyan-500 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
          >
            <Search size={16} />
            Apply Filters
          </button>

          <button
            onClick={handleClearAndRefresh}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-5 py-2 text-sm hover:border-cyan-400 disabled:opacity-50"
          >
            <X size={16} />
            Clear Filters
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {detailError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          <AlertCircle size={18} />
          {detailError}
        </div>
      )}

      {detailLoading && (
        <p className="text-sm text-slate-400">
          Loading benchmark details...
        </p>
      )}

      {/* Loading */}
      {loading ? (
        <p className="text-slate-400">
          Loading benchmark history...
        </p>
      ) : (
        <>
          {/* Summary */}
          {summary && (
            <div className="grid gap-4 md:grid-cols-3">
              <SummaryCard
                title="Total Benchmarks"
                value={summary.total_benchmarks}
              />

              <SummaryCard
                title="Average Improvement"
                value={`${Number(
                  summary.average_improvement_percent
                ).toFixed(2)}%`}
              />

              <SummaryCard
                title="Carbon Saved"
                value={`${Number(
                  summary.total_carbon_saved_grams
                ).toExponential(4)} g`}
              />
            </div>
          )}

          {/* Performance Comparison Chart */}
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h3 className="mb-4 text-lg font-semibold">
                Execution Time Comparison
            </h3>

            <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

                    <XAxis dataKey="id" stroke="#94a3b8" />

                    <YAxis
                    stroke="#94a3b8"
                    label={{
                        value: "Time (ms)",
                        angle: -90,
                        position: "insideLeft",
                    }}
                    />

                    <Tooltip
                    contentStyle={{
                        backgroundColor: "#0f172a",
                        border: "1px solid #334155",
                    }}
                    />

                    <Legend />

                    <Bar
                    dataKey="baseline"
                    name="Baseline"
                    fill="#f59e0b"
                    />

                    <Bar
                    dataKey="optimized"
                    name="Optimized"
                    fill="#22d3ee"
                    />
                </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
        
        {/* Carbon Emissions Comparison Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h3 className="mb-4 text-lg font-semibold">
                Carbon Emissions Comparison
            </h3>

            <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                    <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#334155"
                    />

                    <XAxis dataKey="id" stroke="#94a3b8" />

                    <YAxis
                    stroke="#94a3b8"
                    label={{
                        value: "Carbon Emissions (g CO₂e)",
                        angle: -90,
                        position: "insideLeft",
                    }}
                />

                <Tooltip
                    formatter={(value) => [
                        `${Number(value).toExponential(4)} g`,
                        "Carbon",
                    ]}
                    contentStyle={{
                        backgroundColor: "#0f172a",
                        border: "1px solid #334155",
                    }}
                />

                <Legend />

                    <Bar
                        dataKey="baselineCarbon"
                        name="Baseline Carbon"
                        fill="#f59e0b"
                    />

                    <Bar
                        dataKey="optimizedCarbon"
                        name="Optimized Carbon"
                        fill="#34d399"
                    />
                </BarChart>
            </ResponsiveContainer>
            </div>
        </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-700 text-slate-400">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Table</th>
                  <th className="px-4 py-3">Column</th>
                  <th className="px-4 py-3">Baseline</th>
                  <th className="px-4 py-3">Optimized</th>
                  <th className="px-4 py-3">Improvement</th>
                  <th className="px-4 py-3">Created At</th>
                </tr>
              </thead>

              <tbody>
                {benchmarks.map((benchmark) => (
                  <tr
                    key={benchmark.id}
                    onClick={() => {
                      if (!detailLoading) fetchBenchmarkDetails(benchmark.id);
                    }}
                    className="cursor-pointer border-b border-slate-800 text-slate-300 transition hover:bg-slate-800"
                    title="Click to view benchmark details"
                  >
                    <td className="px-4 py-3">
                      {benchmark.id}
                    </td>

                    <td className="px-4 py-3">
                      {benchmark.table}
                    </td>

                    <td className="px-4 py-3">
                      {benchmark.column}
                    </td>

                    <td className="px-4 py-3">
                      {Number(
                        benchmark.baseline_time_ms
                      ).toFixed(3)} ms
                    </td>

                    <td className="px-4 py-3">
                      {Number(
                        benchmark.optimized_time_ms
                      ).toFixed(3)} ms
                    </td>

                    <td className="px-4 py-3 font-semibold text-emerald-400">
                      {Number(
                        benchmark.improvement_percent
                      ).toFixed(2)}%
                    </td>

                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(
                        benchmark.created_at
                      ).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {selectedBenchmark && (
              <BenchmarkDetailsModal
                benchmark={selectedBenchmark}
                onClose={() => setSelectedBenchmark(null)}
              />
            )}

            {!benchmarks.length && (
              <p className="p-6 text-slate-400">
                No benchmark records found.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function SummaryCard({ title, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-sm text-slate-400">{title}</p>

      <p className="mt-2 text-2xl font-bold text-cyan-400">
        {value}
      </p>
    </div>
  );
}

function BenchmarkDetailsModal({ benchmark, onClose }) {
  const impact = benchmark.environmental_impact;

  const baselineCarbon =
    Number(impact?.baseline?.carbon_grams_co2e) || 0;

  const optimizedCarbon =
    Number(impact?.optimized?.carbon_grams_co2e) || 0;

  const carbonSaved = baselineCarbon - optimizedCarbon;
  const osMonitoring = benchmark.environment_metadata?.os_monitoring;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 p-6">

        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold">
            Benchmark #{benchmark.id}
          </h2>

          <button
            onClick={onClose}
            className="rounded-lg border border-slate-700 px-3 py-1 text-slate-300 hover:border-cyan-400"
          >
            ✕
          </button>
        </div>

        {/* Query */}
        <div className="mb-6">
          <h3 className="mb-2 font-semibold text-cyan-400">
            SQL Query
          </h3>

          <pre className="overflow-x-auto rounded-lg bg-slate-950 p-4 text-sm text-slate-300">
            {benchmark.query}
          </pre>
        </div>

        {/* Metadata */}
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <DetailItem
            label="Table"
            value={benchmark.table}
          />

          <DetailItem
            label="Column"
            value={benchmark.column}
          />

          <DetailItem
            label="Created At"
            value={new Date(
              benchmark.created_at
            ).toLocaleString()}
          />

          <DetailItem
            label="Improvement"
            value={`${Number(
              benchmark.improvement_percent
            ).toFixed(2)}%`}
          />
        </div>
            
        {/* Performance Impact Summary */}
        <PerformanceImpactSummary
          benchmark={benchmark}
        />

        {/* Performance */}
        <h3 className="mb-3 text-lg font-semibold">
          Performance Comparison
        </h3>

        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <DetailMetric
            title="Baseline Time"
            value={`${Number(
              benchmark.baseline_time_ms
            ).toFixed(3)} ms`}
          />

          <DetailMetric
            title="Optimized Time"
            value={`${Number(
              benchmark.optimized_time_ms
            ).toFixed(3)} ms`}
          />
        </div>

        {/* OS Resource Context */}
        <h3 className="mb-2 text-lg font-semibold">OS Resource Context</h3>
        <p className="mb-4 text-sm text-slate-400">
          Host-level resource observations collected across each complete benchmark phase. These metrics provide context and are not measurements attributable to a single SQL statement.
        </p>
        {osMonitoring ? (
          <div className="mb-6 grid gap-4 md:grid-cols-2">
            <OSPhaseCard title="Baseline phase" metrics={osMonitoring.baseline} />
            <OSPhaseCard title="Indexed phase" metrics={osMonitoring.optimized} />
          </div>
        ) : (
          <p className="mb-6 rounded-lg border border-slate-700 bg-slate-950 p-4 text-sm text-slate-400">
            No OS monitoring data is stored for this benchmark. Run a new benchmark after installing the OS profiler to collect it.
          </p>
        )}

        {/* Carbon */}
        <h3 className="mb-3 text-lg font-semibold">
          Environmental Impact
        </h3>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <DetailMetric
            title="Baseline Carbon"
            value={`${baselineCarbon.toExponential(4)} g`}
          />

          <DetailMetric
            title="Optimized Carbon"
            value={`${optimizedCarbon.toExponential(4)} g`}
          />

          <DetailMetric
            title="Carbon Saved"
            value={`${carbonSaved.toExponential(4)} g`}
          />
        </div>

        {/* Automatic Plan Change Summary */}
        <PlanChangeSummary
          baselinePlan={benchmark.baseline_plan}
          optimizedPlan={benchmark.optimized_plan}
        />

        {/* Index Impact Analysis */}
        <IndexImpactAnalysis
          baselinePlan={benchmark.baseline_plan}
          optimizedPlan={benchmark.optimized_plan}
        />

        {/* Execution Plans */}
        <h3 className="mb-3 text-lg font-semibold">
          Execution Plan Comparison
        </h3>

        <div className="grid gap-4 md:grid-cols-2">
          <PlanCard
            title="Baseline Plan"
            plan={benchmark.baseline_plan}
          />

          <PlanCard
            title="Optimized Plan"
            plan={benchmark.optimized_plan}
          />
        </div>


        {/* Query Optimization Explanation */}
        <OptimizationExplanation
          recommendation={benchmark.recommendation}
        />

        <button
          onClick={onClose}
          className="mt-6 rounded-lg bg-cyan-500 px-5 py-2 font-semibold text-slate-950 hover:bg-cyan-400"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function OSPhaseCard({ title, metrics }) {
  const available = metrics?.available;
  const display = (value, suffix = "") =>
    value === null || value === undefined || !Number.isFinite(Number(value))
      ? "N/A"
      : `${Number(value).toFixed(2)}${suffix}`;
  const bytesToMb = (value) =>
    value === null || value === undefined || !Number.isFinite(Number(value))
      ? "N/A"
      : `${(Number(value) / (1024 * 1024)).toFixed(2)} MB`;
  const avgRss = metrics?.postgres_local_rss_avg_mb;
  const maxRss = metrics?.postgres_local_rss_max_mb;
  const postgresRss = avgRss == null || maxRss == null
    ? "N/A"
    : `${display(avgRss)} / ${display(maxRss)} MB`;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950 p-4">
      <h4 className="mb-3 font-semibold text-cyan-300">{title}</h4>
      {!available ? (
        <p className="text-sm text-slate-400">Insufficient monitoring samples for a phase summary.</p>
      ) : (
        <div className="space-y-2 text-sm">
          <OSMetricRow label="Average CPU" value={display(metrics.cpu_utilization_avg_percent, "%")} />
          <OSMetricRow label="Peak CPU" value={display(metrics.cpu_utilization_max_percent, "%")} />
          <OSMetricRow label="Average memory used" value={display(metrics.memory_used_avg_percent, "%")} />
          <OSMetricRow label="Minimum available RAM" value={display(metrics.memory_available_min_mb, " MB")} />
          <OSMetricRow label="Disk read delta" value={bytesToMb(metrics.read_bytes_delta)} />
          <OSMetricRow label="Disk write delta" value={bytesToMb(metrics.write_bytes_delta)} />
          <OSMetricRow label="Swap-out delta" value={metrics.swap_io_counters_reliable ? bytesToMb(metrics.swap_out_bytes_delta) : "Unsupported on Windows"} />
          <OSMetricRow label="Local PostgreSQL RSS (avg / max)" value={postgresRss} />
          <p className="pt-2 text-xs text-slate-500">
            {metrics.cpu_sample_count ?? 0} CPU samples · {metrics.sampling_quality ?? "unknown coverage"}
          </p>
        </div>
      )}
    </div>
  );
}

function OSMetricRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-slate-400">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}

function PerformanceImpactSummary({ benchmark }) {
  const baselineTime = Number(benchmark.baseline_time_ms) || 0;
  const optimizedTime = Number(benchmark.optimized_time_ms) || 0;

  const timeSaved = baselineTime - optimizedTime;

  const timeReduction =
    baselineTime > 0
      ? (timeSaved / baselineTime) * 100
      : 0;

  const impact = benchmark.environmental_impact;

  const baselineCarbon =
    Number(impact?.baseline?.carbon_grams_co2e) || 0;

  const optimizedCarbon =
    Number(impact?.optimized?.carbon_grams_co2e) || 0;

  const carbonSaved = baselineCarbon - optimizedCarbon;

  const carbonReduction =
    baselineCarbon > 0
      ? (carbonSaved / baselineCarbon) * 100
      : 0;

  return (
    <div className="mb-6 rounded-xl border border-cyan-800 bg-cyan-950/30 p-5">
      <h3 className="mb-4 text-lg font-semibold text-cyan-300">
        Performance Impact Summary
      </h3>

      <div className="grid gap-4 md:grid-cols-2">
        <ImpactMetric
          label="Execution Time Saved"
          value={`${timeSaved.toFixed(3)} ms`}
          subtitle={`${timeReduction.toFixed(2)}% reduction`}
        />

        <ImpactMetric
          label="Carbon Saved"
          value={`${carbonSaved.toExponential(4)} g`}
          subtitle={`${carbonReduction.toFixed(2)}% reduction`}
        />
      </div>
    </div>
  );
}

function ImpactMetric({ label, value, subtitle }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <p className="text-xs text-slate-400">
        {label}
      </p>

      <p className="mt-2 text-xl font-bold text-cyan-400">
        {value}
      </p>

      <p className="mt-1 text-sm text-emerald-400">
        {subtitle}
      </p>
    </div>
  );
}

function OptimizationExplanation({ recommendation }) {
  const data = recommendation || {};

  const decision =
    data.decision || "NO_DECISION";

  const meetsThreshold =
    data.meets_improvement_threshold;

  const minimumImprovement =
    data.minimum_improvement_percent;

  const explanation =
    meetsThreshold === true
      ? "The optimized query achieved an improvement above the configured performance threshold."
      : meetsThreshold === false
        ? "The measured improvement did not meet the configured performance threshold."
        : "Performance threshold information is unavailable.";

  const optimization =
    decision === "PERFORMANCE_IMPROVEMENT_CONFIRMED"
      ? "The optimization was retained because the measured performance improvement was confirmed."
      : "No specific optimization action was recorded.";

  return (
    <div className="mt-6 rounded-xl border border-emerald-800 bg-emerald-950/30 p-5">
      <h3 className="mb-4 text-lg font-semibold text-emerald-300">
        Query Optimization Explanation
      </h3>

      <div className="space-y-4">
        <ExplanationItem
          label="Decision"
          value={decision}
        />

        <ExplanationItem
          label="Detected Issue"
          value={explanation}
        />

        <ExplanationItem
          label="Optimization Result"
          value={optimization}
        />

        <ExplanationItem
          label="Minimum Improvement Threshold"
          value={
            minimumImprovement !== undefined
              ? `${minimumImprovement}%`
              : "Not available"
          }
        />

        <ExplanationItem
          label="Threshold Satisfied"
          value={
            meetsThreshold === true
              ? "Yes"
              : meetsThreshold === false
                ? "No"
                : "Unknown"
          }
        />
      </div>

      <details className="mt-5">
        <summary className="cursor-pointer text-sm text-emerald-300">
          View Full Recommendation Data
        </summary>

        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-400">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}

function ExplanationItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-slate-400">
        {label}
      </p>

      <p className="mt-1 break-words text-sm text-slate-200">
        {typeof value === "object"
          ? JSON.stringify(value)
          : String(value ?? "Not available")}
      </p>
    </div>
  );
}

function PlanChangeSummary({
  baselinePlan,
  optimizedPlan,
}) {
  const baseline = extractPlanDetails(baselinePlan);
  const optimized = extractPlanDetails(optimizedPlan);

  const nodeTypeChanged =
    baseline.nodeType !== optimized.nodeType;

  const indexIntroduced =
    !baseline.indexName && optimized.indexName;

  const indexRemoved =
    baseline.indexName && !optimized.indexName;

  let summary = "Execution plan remains unchanged.";

  if (nodeTypeChanged) {
    summary = `Execution strategy changed from ${baseline.nodeType} to ${optimized.nodeType}.`;
  }

  if (indexIntroduced) {
    summary += " An index is used in the optimized plan.";
  }

  if (indexRemoved) {
    summary += " The optimized plan does not report an index.";
  }

  return (
    <div className="mb-6 rounded-xl border border-cyan-800 bg-cyan-950/30 p-5">
      <h3 className="mb-4 text-lg font-semibold text-cyan-300">
        Execution Plan Change
      </h3>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs text-slate-400">
            Baseline Strategy
          </p>

          <p className="mt-1 font-semibold text-slate-200">
            {baseline.nodeType}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Optimized Strategy
          </p>

          <p className="mt-1 font-semibold text-emerald-400">
            {optimized.nodeType}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-sm text-slate-300">
          {summary}
        </p>
      </div>

      {optimized.indexName && (
        <div className="mt-4">
          <p className="text-xs text-slate-400">
            Index Used
          </p>

          <p className="mt-1 break-words text-sm text-emerald-300">
            {optimized.indexName}
          </p>
        </div>
      )}
    </div>
  );
}

function IndexImpactAnalysis({
  baselinePlan,
  optimizedPlan,
}) {
  const baseline = extractPlanDetails(baselinePlan);
  const optimized = extractPlanDetails(optimizedPlan);

  const baselineUsesIndex = Boolean(baseline.indexName);
  const optimizedUsesIndex = Boolean(optimized.indexName);

  const scanChanged =
    baseline.nodeType !== optimized.nodeType;

  let impactMessage;

  if (!baselineUsesIndex && optimizedUsesIndex) {
    impactMessage =
      "The optimized plan introduced index-based access.";
  } else if (baselineUsesIndex && !optimizedUsesIndex) {
    impactMessage =
      "The optimized plan no longer reports index usage.";
  } else if (scanChanged) {
    impactMessage =
      "The execution strategy changed, but no root-level index usage was detected.";
  } else {
    impactMessage =
      "No index usage change was detected at the root plan level.";
  }

  return (
    <div className="mb-6 rounded-xl border border-emerald-800 bg-emerald-950/30 p-5">
      <h3 className="mb-4 text-lg font-semibold text-emerald-300">
        Index Impact Analysis
      </h3>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs text-slate-400">
            Baseline Index
          </p>

          <p className="mt-1 text-sm text-slate-200">
            {baseline.indexName || "No index reported"}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Optimized Index
          </p>

          <p className="mt-1 break-words text-sm text-emerald-300">
            {optimized.indexName || "No index reported"}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-sm text-slate-300">
          {impactMessage}
        </p>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs text-slate-400">
            Baseline Scan
          </p>

          <p className="mt-1 text-sm text-slate-200">
            {baseline.nodeType}
          </p>
        </div>

        <div>
          <p className="text-xs text-slate-400">
            Optimized Scan
          </p>

          <p className="mt-1 text-sm text-emerald-300">
            {optimized.nodeType}
          </p>
        </div>
      </div>
    </div>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 font-semibold text-slate-200">
        {value}
      </p>
    </div>
  );
}

function DetailMetric({ title, value }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="mt-2 text-xl font-bold text-cyan-400">
        {value}
      </p>
    </div>
  );
}

function PlanCard({ title, plan }) {
  const planDetails = extractPlanDetails(plan);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <h4 className="mb-4 font-semibold text-slate-200">
        {title}
      </h4>

      {/* Main plan information */}
      <div className="space-y-3 text-sm">
        <PlanDetail
          label="Node Type"
          value={planDetails.nodeType}
        />

        <PlanDetail
          label="Relation"
          value={planDetails.relationName}
        />

        <PlanDetail
          label="Plan Rows"
          value={planDetails.planRows}
        />

        <PlanDetail
          label="Actual Rows"
          value={planDetails.actualRows}
        />

        <PlanDetail
          label="Total Cost"
          value={planDetails.totalCost}
        />

        {planDetails.indexName && (
          <PlanDetail
            label="Index Name"
            value={planDetails.indexName}
          />
        )}

        {planDetails.filter && (
          <PlanDetail
            label="Filter"
            value={planDetails.filter}
          />
        )}

        {planDetails.indexCond && (
          <PlanDetail
            label="Index Condition"
            value={planDetails.indexCond}
          />
        )}
      </div>

      {/* Full plan */}
      <details className="mt-5">
        <summary className="cursor-pointer text-sm text-cyan-400">
          View Full Execution Plan
        </summary>

        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-400">
          {JSON.stringify(plan, null, 2)}
        </pre>
      </details>
    </div>
  );
}

function PlanDetail({ label, value }) {
  return (
    <div>
      <p className="text-xs text-slate-500">
        {label}
      </p>

      <p className="mt-1 break-words text-slate-300">
        {String(value ?? "N/A")}
      </p>
    </div>
  );
}

function extractPlanDetails(plan) {
  const rootPlan =
    plan?.Plan ||
    plan?.plan?.Plan ||
    plan?.plan ||
    {};

  const findIndexNode = (node) => {
    if (!node) return null;

    if (
      node["Index Name"] ||
      node["Node Type"] === "Index Scan" ||
      node["Node Type"] === "Index Only Scan" ||
      node["Node Type"] === "Bitmap Index Scan"
    ) {
      return node;
    }

    if (Array.isArray(node.Plans)) {
      for (const child of node.Plans) {
        const result = findIndexNode(child);

        if (result) return result;
      }
    }

    return null;
  };

  const indexNode = findIndexNode(rootPlan);

  return {
    nodeType: rootPlan["Node Type"] || "Unavailable",
    relationName: rootPlan["Relation Name"] || "N/A",
    planRows: rootPlan["Plan Rows"] ?? "N/A",
    actualRows: rootPlan["Actual Rows"] ?? "N/A",
    totalCost: rootPlan["Total Cost"] ?? "N/A",

    indexName: indexNode?.["Index Name"] || "",
    filter: rootPlan["Filter"] || "",
    indexCond:
      indexNode?.["Index Cond"] ||
      rootPlan["Index Cond"] ||
      "",
  };
}

export default BenchmarkHistory;