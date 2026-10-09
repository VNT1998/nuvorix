import React, { useState, useEffect } from "react";
import { Workload, EvaluationRun } from "../types";
import { api } from "../lib/api";
import { ShieldCheck, Play, CheckCircle2, XCircle, Sliders } from "lucide-react";

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
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          Automated Quality Evaluation & Release Policy Gates
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Verify candidates prior to rollout. Candidates failing faithfulness, accuracy, latency, or cost budgets are deterministically blocked with explicit violation reasons.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Evaluation Configuration */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">Evaluation Suite Configuration</h2>

          <form onSubmit={handleRunEvaluation} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-700 font-medium mb-1">Target Workload</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
              >
                {workloads.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-700 font-medium mb-1">Candidate Version String</label>
              <input
                type="text"
                required
                value={versionToEval}
                onChange={(e) => setVersionToEval(e.target.value)}
                placeholder="e.g. v1.2.5 or v1.3.0-bad-canary"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs font-mono text-[11px]"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">
                Evaluates empirical benchmarks (Recall@3, MRR@3, Tool Accuracy, p95 Latency) against threshold policy.
              </span>
            </div>

            {/* Release Policy Thresholds */}
            <div className="pt-2 border-t border-slate-200 space-y-3">
              <span className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5 uppercase">
                <Sliders className="w-3.5 h-3.5 text-blue-600" />
                Release Gate Policy Limits
              </span>

              <div>
                <div className="flex justify-between text-slate-600 text-[11px] mb-1">
                  <span>Min Faithfulness / Recall@3:</span>
                  <span className="font-mono text-blue-700 font-bold">{(minFaithfulness * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={minFaithfulness}
                  onChange={(e) => setMinFaithfulness(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-slate-600 text-[11px] mb-1">
                  <span>Min Correctness / Tool Acc:</span>
                  <span className="font-mono text-blue-700 font-bold">{(minCorrectness * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={minCorrectness}
                  onChange={(e) => setMinCorrectness(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-700 font-medium text-[10px] block mb-1">Max p95 Latency (ms)</label>
                  <input
                    type="number"
                    value={maxLatency}
                    onChange={(e) => setMaxLatency(parseFloat(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-900 shadow-2xs"
                  />
                </div>
                <div>
                  <label className="text-slate-700 font-medium text-[10px] block mb-1">Max Cost/Req ($)</label>
                  <input
                    type="number"
                    step="0.001"
                    value={maxCost}
                    onChange={(e) => setMaxCost(parseFloat(e.target.value))}
                    className="w-full bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-900 shadow-2xs"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={evaluating || !selectedWorkloadId}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
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
              className={`p-5 rounded-xl border shadow-xs ${
                lastEval.decision === "ALLOW"
                  ? "bg-emerald-50/70 border-emerald-200"
                  : "bg-rose-50/70 border-rose-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {lastEval.decision === "ALLOW" ? (
                    <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                  ) : (
                    <XCircle className="w-6 h-6 text-rose-600" />
                  )}
                  <div>
                    <div className="text-xs uppercase font-bold tracking-wider text-slate-500">
                      Release Policy Decision
                    </div>
                    <div
                      className={`text-2xl font-black ${
                        lastEval.decision === "ALLOW" ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {lastEval.decision}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-slate-500 font-medium">Candidate Version</div>
                  <div className="text-base font-mono font-bold text-slate-900">{lastEval.version}</div>
                </div>
              </div>

              {/* Reasons if blocked */}
              {lastEval.reasons && lastEval.reasons.length > 0 && (
                <div className="mt-4 p-3 rounded-lg bg-rose-100/70 border border-rose-200 space-y-1">
                  <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider">
                    Release Block Reasons:
                  </span>
                  <ul className="text-xs text-rose-900 list-disc list-inside space-y-1">
                    {lastEval.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Metric Breakdown */}
              <div className="mt-4 grid grid-cols-4 gap-2 pt-3 border-t border-slate-200">
                {Object.entries(lastEval.metrics || {}).slice(0, 4).map(([k, v]) => (
                  <div key={k} className="p-2.5 rounded bg-white border border-slate-200 text-center shadow-2xs">
                    <div className="text-[10px] text-slate-500 capitalize">{k.replace("_", " ")}</div>
                    <div className="text-xs font-mono font-bold text-slate-900 mt-0.5">
                      {typeof v === "number" ? v.toFixed(3) : String(v)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Historical Runs Table */}
          <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">Evaluation Run History</h2>

            {evalHistory.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-200 rounded-lg">
                No evaluation runs logged for this workload yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] tracking-wider bg-slate-50/75">
                      <th className="py-2.5 px-3 font-semibold">Version</th>
                      <th className="py-2.5 px-3 font-semibold">Gate Decision</th>
                      <th className="py-2.5 px-3 font-semibold">Violations</th>
                      <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {evalHistory.map((h) => (
                      <tr key={h.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-2.5 px-3 font-mono text-slate-900 font-semibold">{h.version}</td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                              h.decision === "ALLOW"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {h.decision}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-slate-500">
                          {h.reasons && h.reasons.length > 0 ? (
                            <span className="text-rose-700 font-semibold">{h.reasons.length} violations</span>
                          ) : (
                            <span className="text-emerald-700 font-semibold">0 violations</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500 text-[11px]">
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
