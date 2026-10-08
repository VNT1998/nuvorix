import React, { useState } from "react";
import { Workload } from "../types";
import { api } from "../lib/api";
import { Cpu, Play, CheckCircle2, Award, ArrowUpRight, BarChart2 } from "lucide-react";

interface MLStudioViewProps {
  workloads: Workload[];
  onRefreshWorkloads: () => Promise<void>;
}

export const MLStudioView: React.FC<MLStudioViewProps> = ({ workloads, onRefreshWorkloads }) => {
  const mlWorkloads = workloads.filter((w) => w.type === "ml_model");
  const [selectedWorkloadId, setSelectedWorkloadId] = useState(mlWorkloads[0]?.id || "");
  const [modelName, setModelName] = useState("performance_regressor");
  const [alpha, setAlpha] = useState(1.0);
  const [maxIter, setMaxIter] = useState(1000);

  const [training, setTraining] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);

  const handleTrain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkloadId) return;
    setTraining(true);
    try {
      const res = await api.trainModel(selectedWorkloadId, modelName, alpha, maxIter);
      setLastResult(res);
      await onRefreshWorkloads();
    } catch (err: any) {
      alert(`Training failed: ${err.message}`);
    } finally {
      setTraining(false);
    }
  };

  const handlePromote = async (versionId: string, env: string) => {
    try {
      await api.promoteModelVersion(versionId, env);
      alert(`Promoted version to ${env}!`);
      await onRefreshWorkloads();
    } catch (err: any) {
      alert(`Promotion error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-emerald-400" />
          ML Training Lifecycle & Model Registry
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Train scikit-learn models, log experiment metrics (RMSE, MAE, R²), persist joblib artifacts, and enforce promotion quality gates.
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Training Configuration */}
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Execution Parameters</h2>

          <form onSubmit={handleTrain} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Target ML Workload</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {mlWorkloads.length === 0 ? (
                  <option value="">No ML Workloads found</option>
                ) : (
                  mlWorkloads.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} (Active: {w.active_version || "none"})
                    </option>
                  ))
                )}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Model Name</label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Alpha (L2 Penalty)</label>
                <input
                  type="number"
                  step="0.1"
                  value={alpha}
                  onChange={(e) => setAlpha(parseFloat(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Max Iterations</label>
                <input
                  type="number"
                  value={maxIter}
                  onChange={(e) => setMaxIter(parseInt(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={training || !selectedWorkloadId}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {training ? "Training Scikit-Learn Model..." : "Train & Register Model"}
            </button>
          </form>
        </div>

        {/* Right Column: Training Run Output & Metrics */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Latest Training Run Metrics</h2>

          {lastResult ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400">Registered Version</div>
                  <div className="text-lg font-bold font-mono text-cyan-400">{lastResult.version}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400">Status</div>
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
                    {lastResult.status}
                  </span>
                </div>
              </div>

              {/* Metric Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">RMSE</div>
                  <div className="text-xl font-bold text-slate-100 mt-1">{lastResult.metrics.rmse}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">MAE</div>
                  <div className="text-xl font-bold text-slate-100 mt-1">{lastResult.metrics.mae}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[11px] text-slate-400">R² Score</div>
                  <div className="text-xl font-bold text-emerald-400 mt-1">{lastResult.metrics.r2_score}</div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 text-[11px] space-y-1">
                <div className="text-slate-400">
                  Artifact Path: <span className="font-mono text-slate-300">{lastResult.artifact_uri}</span>
                </div>
                <div className="text-slate-400">
                  Training Duration: <span className="font-mono text-indigo-300">{lastResult.metrics.training_duration_sec}s</span>
                </div>
              </div>

              {/* Promotion Actions */}
              <div className="pt-2 flex gap-2">
                <button
                  onClick={() => handlePromote(lastResult.version_id, "staging")}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 cursor-pointer flex items-center gap-1"
                >
                  <ArrowUpRight className="w-3.5 h-3.5 text-amber-400" />
                  Promote to Staging
                </button>
                <button
                  onClick={() => handlePromote(lastResult.version_id, "production")}
                  className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 rounded-lg text-xs font-medium border border-emerald-500/30 cursor-pointer flex items-center gap-1"
                >
                  <Award className="w-3.5 h-3.5 text-emerald-400" />
                  Promote to Production
                </button>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-lg">
              No training run executed yet in this session. Configure hyperparameters on the left and click "Train & Register Model" to view live metrics and artifact paths.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
