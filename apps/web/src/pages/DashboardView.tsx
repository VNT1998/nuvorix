import React from "react";
import { Workload, Deployment, EvaluationRun, Incident, CostSummary } from "../types";
import {
  Boxes,
  Cpu,
  ShieldCheck,
  AlertTriangle,
  Coins,
  Rocket,
  CheckCircle2,
  XCircle,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

interface DashboardViewProps {
  workloads: Workload[];
  deployments: Deployment[];
  evaluations: EvaluationRun[];
  incidents: Incident[];
  costs: CostSummary | null;
  onNavigate: (view: any) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  workloads,
  deployments,
  evaluations,
  incidents,
  costs,
  onNavigate,
}) => {
  const openIncidents = incidents.filter((i) => i.status !== "resolved");
  const passedEvals = evaluations.filter((e) => e.passed).length;
  const passRate = evaluations.length > 0 ? Math.round((passedEvals / evaluations.length) * 100) : 100;

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 flex items-center justify-between shadow-lg">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-bold text-indigo-400 tracking-wider">Production Platform Overview</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Self-Service AI/ML Infrastructure</h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Build, evaluate with strict release policy gates, deploy with Blue/Green safety, monitor token costs, and remediate incidents across your ML models, RAG pipelines, and LangGraph agents.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => onNavigate("evaluations")}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all flex items-center gap-2 cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            Run Release Gate
          </button>
          <button
            onClick={() => onNavigate("agent_studio")}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition-all flex items-center gap-2 cursor-pointer"
          >
            <Rocket className="w-4 h-4" />
            Launch Agent Studio
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Workloads */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Active Workloads</span>
            <Boxes className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-slate-100">{workloads.length}</div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
            <span className="text-cyan-400 font-semibold">{workloads.filter((w) => w.type === "agent").length} agents</span>
            <span>•</span>
            <span className="text-indigo-400 font-semibold">{workloads.filter((w) => w.type === "rag").length} RAG</span>
            <span>•</span>
            <span className="text-emerald-400 font-semibold">{workloads.filter((w) => w.type === "ml_model").length} ML models</span>
          </div>
        </div>

        {/* Evaluation Pass Rate */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Release Gate Pass Rate</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-emerald-400">{passRate}%</div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <span>{passedEvals} allowed of {evaluations.length} evaluation suites</span>
          </div>
        </div>

        {/* FinOps Spend */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total FinOps Spend</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-amber-300">
            ${costs ? costs.total_cost.toFixed(4) : "0.0000"}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <span>{costs?.total_requests || 0} tracked LLM / embedding requests</span>
          </div>
        </div>

        {/* Open Incidents */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Open Incidents & RCA</span>
            <AlertTriangle className={`w-4 h-4 ${openIncidents.length > 0 ? "text-rose-400" : "text-emerald-400"}`} />
          </div>
          <div className={`mt-3 text-3xl font-bold ${openIncidents.length > 0 ? "text-rose-400" : "text-emerald-400"}`}>
            {openIncidents.length}
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            {openIncidents.length > 0 ? "Requires automated or operator rollback" : "All platform SLOs healthy"}
          </div>
        </div>
      </div>

      {/* Two Column Layout: Workloads & Recent Deployments */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workloads List */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-200">Registered Workloads</h2>
            <button
              onClick={() => onNavigate("projects")}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
            >
              Manage all <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2.5">
            {workloads.map((w) => (
              <div
                key={w.id}
                className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${
                      w.status === "healthy" ? "bg-emerald-400" : "bg-amber-400 animate-pulse"
                    }`}
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-200">{w.name}</div>
                    <div className="text-[11px] text-slate-500 font-mono">ID: {w.id}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                    {w.type.toUpperCase()}
                  </span>
                  <span className="text-xs font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/30">
                    {w.active_version || "no active version"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Deployments Rollout */}
        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-200">Recent Deployments</h2>
            <button
              onClick={() => onNavigate("deployments")}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
            >
              View rollout <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {deployments.slice(0, 4).map((d) => (
              <div key={d.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-semibold text-slate-200">{d.version}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                      d.status === "active"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : d.status === "rolled_back"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {d.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>Env: {d.environment}</span>
                  <span>Strategy: {d.strategy}</span>
                  <span className="font-mono text-indigo-400">{d.traffic_percentage}% traffic</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
