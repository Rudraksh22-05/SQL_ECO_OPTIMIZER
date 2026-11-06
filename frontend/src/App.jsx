
import { useState } from "react";
import axios from "axios";
import {
  Activity,
  Database,
  Leaf,
  Zap,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import BenchmarkHistory from "./components/BenchmarkHistory";
import SystemMonitor from "./components/SystemMonitor";


const API_URL = "http://localhost:8000/api";

function App() {
  const [query, setQuery] = useState(
    "SELECT * FROM employees WHERE dept_id = 5"
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState("analysis");
  const analyzeQuery = async () => {
    if (!query.trim()) {
      setError("Please enter a SQL query.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/analyze`, {
        query,
      });

      setResult(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to connect to the backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const benchmark = result?.benchmark;
  const improvement = benchmark?.improvement_percent;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <h1 className="text-2xl font-bold text-cyan-400">
              SQL Eco-Optimizer
            </h1>
            <p className="text-sm text-slate-400">
              Database performance and carbon footprint analyzer
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveView("analysis")}
              className={`rounded-lg px-4 py-2 text-sm ${
                activeView === "analysis"
                  ? "bg-cyan-500 text-slate-950"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              Query Analysis
            </button>

            <button
              onClick={() => setActiveView("history")}
              className={`rounded-lg px-4 py-2 text-sm ${
                activeView === "history"
                  ? "bg-cyan-500 text-slate-950"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              Benchmark History
            </button>
            <button
              onClick={() => setActiveView("system")}
              className={`rounded-lg px-4 py-2 text-sm ${
                activeView === "system"
                  ? "bg-cyan-500 text-slate-950"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              OS Resource Profiler
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">

        {activeView === "history" ? (
          <BenchmarkHistory />
        ) : activeView === "system" ? (
          <SystemMonitor />
        ) : (
          <>

          

        {/* Query Editor */}
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-4 flex items-center gap-3">
            <Database className="text-cyan-400" />
            <h2 className="text-xl font-semibold">
              Query Analysis
            </h2>
          </div>

          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={5}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 p-4 font-mono text-sm text-slate-200 outline-none focus:border-cyan-400"
            placeholder="Enter a SELECT query..."
          />

          <button
            onClick={analyzeQuery}
            disabled={loading}
            className="mt-4 rounded-lg bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Analyzing..." : "Analyze Query"}
          </button>

          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">
              <AlertCircle size={18} />
              {error}
            </div>
          )}
        </section>

        {/* Results */}
        {result && (
          <>
            <section className="grid gap-4 md:grid-cols-3">
              <MetricCard
                title="Execution Time"
                value={`${result.execution_time_ms?.toFixed(3)} ms`}
                icon={<Activity />}
              />

              <MetricCard
                title="Optimization"
                value={
                  improvement !== undefined
                    ? `${improvement.toFixed(2)}%`
                    : "Not benchmarked"
                }
                icon={<Zap />}
              />

              <MetricCard
                title="Carbon Savings"
                value={
                  benchmark?.environmental_impact
                    ? `${benchmark.environmental_impact.carbon_saving_percent.toFixed(2)}%`
                    : "Not available"
                }
                icon={<Leaf />}
              />
            </section>

            {/* Suggestions */}
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
              <h2 className="mb-4 text-xl font-semibold">
                Optimization Suggestions
              </h2>

              <div className="space-y-3">
                {result.suggestions?.length ? (
                  result.suggestions.map((suggestion, index) => (
                    <div
                      key={index}
                      className="rounded-lg border border-slate-700 bg-slate-950 p-4"
                    >
                      <div className="flex items-center gap-2">
                        {suggestion.type ===
                        "INDEX_RECOMMENDATION" ? (
                          <Zap className="text-amber-400" size={18} />
                        ) : (
                          <CheckCircle
                            className="text-emerald-400"
                            size={18}
                          />
                        )}

                        <span className="font-semibold">
                          {suggestion.type}
                        </span>
                      </div>

                      <p className="mt-2 text-sm text-slate-300">
                        {suggestion.message}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        {suggestion.reason}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-400">
                    No optimization suggestions found.
                  </p>
                )}
              </div>
            </section>

            {/* Benchmark Comparison */}
            {benchmark && (
              <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
                <h2 className="mb-4 text-xl font-semibold">
                  Benchmark Comparison
                </h2>

                <div className="grid gap-4 md:grid-cols-2">
                  <ComparisonCard
                    title="Baseline"
                    time={benchmark.baseline?.median_execution_time_ms}
                    plan={benchmark.baseline?.plan?.Plan?.["Node Type"]}
                  />

                  <ComparisonCard
                    title="Optimized"
                    time={benchmark.optimized?.median_execution_time_ms}
                    plan={benchmark.optimized?.plan?.Plan?.["Node Type"]}
                  />
                </div>

                <div className="mt-4 rounded-lg bg-emerald-950/40 p-4 text-emerald-300">
                  <p className="font-semibold">
                    {benchmark.recommendation?.decision ||
                      "Benchmark completed"}
                  </p>
                </div>
              </section>
            )}
          </>
        )}
          </>
        )}
      </main>
    </div>
  );
}

function MetricCard({ title, value, icon }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-3 flex items-center gap-2 text-slate-400">
        {icon}
        <span className="text-sm">{title}</span>
      </div>

      <p className="text-2xl font-bold text-cyan-400">
        {value}
      </p>
    </div>
  );
}

function ComparisonCard({ title, time, plan }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <h3 className="font-semibold text-slate-200">{title}</h3>

      <p className="mt-2 text-2xl font-bold text-cyan-400">
        {time !== undefined ? `${time.toFixed(3)} ms` : "N/A"}
      </p>

      <p className="mt-2 text-sm text-slate-400">
        Plan: {plan || "Unavailable"}
      </p>
    </div>
  );
}

export default App;