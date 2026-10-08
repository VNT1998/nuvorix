import React, { useState, useEffect } from "react";
import { Workload, EvaluationRun } from "../types";
import { api } from "../lib/api";
import { ShieldCheck, Play, AlertCircle, CheckCircle2, XCircle, Sliders } from "lucide-react";

interface EvaluationGatesViewProps {
  workloads: Workload[];
  onRefreshEvaluations: () => Promise<void>;
}

export const EvaluationGatesView: React.FC<EvaluationGatesViewProps> = ({
  workloads,
  onRefreshEvaluations,
}) => {
  const [selectedWorkloadId, setSelectedWorkloadId] = useState(workloads[0]?.id || "");
  const [versionToEval, setVersionToEval] = useState("v1.2.5-canary");
  
  // Policy parameters
  const [minFaithfulness, setMinFaithfulness] = useState(0.85);
  const [minCorrectness, setMinCorrectness] = useState(0.80);
  const [maxLatency, setMaxLatency] = useState(2500);
  const [maxCost, setMaxCost] = useState(0.015);

  const [evaluating, setEvaluating] = useState(false);
  const [lastEval, setLastEval] = useState<EvaluationRun | null>(null);
  const [evalHistory, setEvalHistory] = useState<EvaluationRun[]>([]);

  useEffect(() => {
    if (selectedWorkloadId) {
      loadHistory(selectedWorkloadId);
    }
  }, [selectedWorkloadId]);

  const loadHistory = async (wId: string) => {
    try {
      const history = await api.getEvaluations(wId);
      setEvalHistory(history);
    } catch (_) {}
  };

  const handleRunEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkloadId || !versionToEval.trim()) return;
    setEvaluating(true);
    try {
      const res = await api.runEvaluation(selectedWorkloadId, versionToEval, {
        min_faithfulness: minFaithfulness,
        min_answer_correctness: minCorrectness,
        max_p95_latency_ms: maxLatency,
        max_cost_per_request: maxCost,
      });
      setLastEval(res);
      await loadHistory(selectedWorkloadId);
      await onRefreshEvaluations();
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          Automated Quality Evaluation & Release Policy Gates
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Verify candidates prior to rollout. Candidates failing faithfulness, accuracy, latency, or cost budgets are deterministically blocked with explicit violation reasons.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Evaluation Configuration */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Evaluation Suite Configuration</h2>

          <form onSubmit={handleRunEvaluation} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Target Workload</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {workloads.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Candidate Version String</label>
              <input
                type="text"
                required
                value={versionToEval}
                onChange={(e) => setVersionToEval(e.target.value)}
                placeholder="e.g. v1.2.5 or v1.3.0-bad-canary"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-[11px]"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">
                Tip: Versions containing "bad" or "fail" simulate degraded metrics to test the release gate blocking workflow.
              </span>
            </div>

            {/* Release Policy Thresholds */}
            <div className="pt-2 border-t border-slate-800 space-y-3">
              <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5 uppercase">
                <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                Release Gate Policy Limits
              </span>

              <div>
                <div className="flex justify-between text-slate-400 text-[11px] mb-1">
                  <span>Min Faithfulness:</span>
                  <span className="font-mono text-cyan-400 font-bold">{(minFaithfulness * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={minFaithfulness}
                  onChange={(e) => setMinFaithfulness(parseFloat(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-slate-400 text-[11px] mb-1">
                  <span>Min Answer Correctness:</span>
                  <span className="font-mono text-cyan-400 font-bold">{(minCorrectness * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={minCorrectness}
                  onChange={(e) => setMinCorrectness(parseFloat(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 text-[10px] block mb-1">Max p95 Latency (ms)</label>
                  <input
                    type="number"
                    value={maxLatency}
                    onChange={(e) => setMaxLatency(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 text-[10px] block mb-1">Max Cost/Req ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={maxCost}
                    onChange={(e) => setMaxCost(parseFloat(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={evaluating || !selectedWorkloadId}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {evaluating ? "Evaluating Workload Metrics..." : "Run Evaluation Suite"}
            </button>
          </form>
        </div>

        {/* Right Column: Decision Banner & History */}
        <div className="lg:col-span-2 space-y-4">
          {/* Decision Card */}
          {lastEval && (
            <div
              className={`p-5 rounded-xl border shadow-lg ${
                lastEval.decision === "ALLOW"
                  ? "bg-emerald-950/20 border-emerald-500/40 shadow-emerald-900/10"
                  : "bg-rose-950/20 border-rose-500/40 shadow-rose-900/10"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {lastEval.decision === "ALLOW" ? (
                    <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                  ) : (
                    <XCircle className="w-6 h-6 text-rose-400" />
                  )}
                  <div>
                    <div className="text-xs uppercase font-bold tracking-wider text-slate-400">
                      Release Policy Decision
                    </div>
                    <div
                      className={`text-2xl font-black ${
                        lastEval.decision === "ALLOW" ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {lastEval.decision}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-slate-400">Candidate Version</div>
                  <div className="text-base font-mono font-bold text-slate-200">{lastEval.version}</div>
                </div>
              </div>

              {/* Reasons if blocked */}
              {lastEval.reasons && lastEval.reasons.length > 0 && (
                <div className="mt-4 p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 space-y-1">
                  <span className="text-[11px] font-bold text-rose-300 uppercase tracking-wider">
                    Release Block Reasons:
                  </span>
                  <ul className="text-xs text-rose-200 list-disc list-inside space-y-1">
                    {lastEval.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Metric Breakdown */}
              <div className="mt-4 grid grid-cols-4 gap-2 pt-3 border-t border-slate-800">
                {Object.entries(lastEval.metrics || {}).slice(0, 4).map(([k, v]) => (
                  <div key={k} className="p-2 rounded bg-slate-900/80 border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400 capitalize">{k.replace("_", " ")}</div>
                    <div className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                      {typeof v === "number" ? v.toFixed(3) : String(v)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Historical Runs Table */}
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">Evaluation Run History</h2>

            {evalHistory.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-lg">
                No evaluation runs logged for this workload yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                      <th className="pb-2.5 font-semibold">Version</th>
                      <th className="pb-2.5 font-semibold">Gate Decision</th>
                      <th className="pb-2.5 font-semibold">Violations</th>
                      <th className="pb-2.5 font-semibold">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {evalHistory.map((h) => (
                      <tr key={h.id} className="hover:bg-slate-800/30">
                        <td className="py-2.5 font-mono text-slate-200 font-semibold">{h.version}</td>
                        <td className="py-2.5">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                              h.decision === "ALLOW"
                                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                                : "bg-rose-500/20 text-rose-300 border-rose-500/30"
                            }`}
                          >
                            {h.decision}
                          </span>
                        </td>
                        <td className="py-2.5 text-[11px] text-slate-400">
                          {h.reasons && h.reasons.length > 0 ? (
                            <span className="text-rose-400 font-medium">{h.reasons.length} violations</span>
                          ) : (
                            <span className="text-emerald-400">0 violations</span>
                          )}
                        </td>
                        <td className="py-2.5 text-slate-500 text-[11px]">
                          {new Date(h.started_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
