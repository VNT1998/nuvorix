import React, { useState } from "react";
import { Workload, Deployment } from "../types";
import { api } from "../lib/api";
import { Rocket, RotateCcw } from "lucide-react";

interface DeploymentsViewProps {
  workloads: Workload[];
  deployments: Deployment[];
  onRefreshDeployments: () => Promise<void>;
  onRefreshWorkloads: () => Promise<void>;
}

export const DeploymentsView: React.FC<DeploymentsViewProps> = ({
  workloads,
  deployments,
  onRefreshDeployments,
  onRefreshWorkloads,
}) => {
  const [selectedEnv, setSelectedEnv] = useState<"all" | "dev" | "staging" | "production">("all");
  const [selectedWorkloadId, setSelectedWorkloadId] = useState(workloads[0]?.id || "");
  const [versionToDeploy, setVersionToDeploy] = useState("v1.2.0");
  const [targetEnv, setTargetEnv] = useState("staging");
  const [strategy, setStrategy] = useState("blue_green");

  const [deploying, setDeploying] = useState(false);
  const [rollingBack, setRollingBack] = useState<string | null>(null);

  const filteredDeployments =
    selectedEnv === "all"
      ? deployments
      : deployments.filter((d) => d.environment === selectedEnv);

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkloadId || !versionToDeploy.trim()) return;
    setDeploying(true);
    try {
      await api.createDeployment(selectedWorkloadId, versionToDeploy, targetEnv, strategy);
      alert(`Deployment created successfully in ${targetEnv}!`);
      await onRefreshDeployments();
      await onRefreshWorkloads();
    } catch (err: any) {
      alert(`Deployment failed: ${err.message}`);
    } finally {
      setDeploying(false);
    }
  };

  const handleRollback = async (depId: string) => {
    if (!confirm("Are you sure you want to rollback this deployment? Traffic will immediately revert to the previous active release.")) return;
    setRollingBack(depId);
    try {
      const res = await api.rollbackDeployment(depId);
      alert(res.message);
      await onRefreshDeployments();
      await onRefreshWorkloads();
    } catch (err: any) {
      alert(`Rollback failed: ${err.message}`);
    } finally {
      setRollingBack(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Rocket className="w-5 h-5 text-blue-600" />
            Deployments & Blue/Green Rollout Engine
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Promote evaluated workloads to target environments with progressive traffic switching and instant rollback guarantees.
          </p>
        </div>

        {/* Environment Filters */}
        <div className="flex bg-slate-100 border border-slate-200 rounded-lg p-1 text-xs shadow-2xs">
          {(["all", "dev", "staging", "production"] as const).map((env) => (
            <button
              key={env}
              onClick={() => setSelectedEnv(env)}
              className={`px-3 py-1 rounded font-medium capitalize cursor-pointer transition-colors ${
                selectedEnv === env
                  ? "bg-white text-slate-900 shadow-xs font-semibold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {env}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Create Deployment */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">Launch New Deployment</h2>

          <form onSubmit={handleDeploy} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-700 font-medium mb-1">Target Workload</label>
              <select
                value={selectedWorkloadId}
                onChange={(e) => setSelectedWorkloadId(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
              >
                {workloads.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} (Active: {w.active_version || "none"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-700 font-medium mb-1">Version to Deploy</label>
              <input
                type="text"
                required
                value={versionToDeploy}
                onChange={(e) => setVersionToDeploy(e.target.value)}
                placeholder="e.g. v1.2.0"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs font-mono text-[11px]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-medium mb-1">Environment</label>
                <select
                  value={targetEnv}
                  onChange={(e) => setTargetEnv(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
                >
                  <option value="dev">dev</option>
                  <option value="staging">staging</option>
                  <option value="production">production</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-medium mb-1">Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
                >
                  <option value="blue_green">Blue / Green</option>
                  <option value="direct">Direct</option>
                  <option value="canary">Canary (5%)</option>
                </select>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-[11px] text-blue-800">
              Note: The Nuvorix control plane checks evaluation gate records before allowing promotion. Blocked candidates will be rejected.
            </div>

            <button
              type="submit"
              disabled={deploying || !selectedWorkloadId}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              <Rocket className="w-3.5 h-3.5" />
              {deploying ? "Deploying Release..." : "Launch Deployment"}
            </button>
          </form>
        </div>

        {/* Right Column: Active & Historical Deployments Table */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-white border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Rollout States & Traffic Routing</h2>
            <span className="text-[11px] text-slate-500 font-mono font-medium">
              {filteredDeployments.length} Deployments
            </span>
          </div>

          <div className="space-y-3">
            {filteredDeployments.map((d) => {
              const workload = workloads.find((w) => w.id === d.workload_id);
              const isActive = d.status === "active";
              return (
                <div
                  key={d.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isActive
                      ? "bg-white border-blue-300 shadow-xs ring-1 ring-blue-200/60"
                      : "bg-white border-slate-200 shadow-xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${
                          isActive
                            ? "bg-emerald-500"
                            : d.status === "rolled_back"
                            ? "bg-rose-500"
                            : "bg-slate-400"
                        }`}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">{workload?.name || d.workload_id}</span>
                          <span className="font-mono text-xs font-bold text-blue-700">{d.version}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                          Deployment ID: {d.id}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[11px] px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold uppercase border border-slate-200">
                        {d.environment}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                          isActive
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : d.status === "rolled_back"
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {d.status}
                      </span>
                    </div>
                  </div>

                  {/* Traffic bar & Rollback action */}
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-slate-500">Traffic Allocation:</span>
                      <div className="w-32 h-2 rounded-full bg-slate-100 border border-slate-200 overflow-hidden">
                        <div
                          className="h-full bg-blue-600 rounded-full transition-all"
                          style={{ width: `${d.traffic_percentage}%` }}
                        />
                      </div>
                      <span className="font-mono font-bold text-blue-700">{d.traffic_percentage}%</span>
                    </div>

                    {isActive && (
                      <button
                        onClick={() => handleRollback(d.id)}
                        disabled={rollingBack === d.id}
                        className="px-3 py-1 bg-white hover:bg-rose-50 text-rose-700 rounded-lg text-xs font-semibold border border-rose-300 shadow-2xs flex items-center gap-1.5 cursor-pointer transition-all"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        {rollingBack === d.id ? "Rolling back..." : "Instant Rollback"}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
