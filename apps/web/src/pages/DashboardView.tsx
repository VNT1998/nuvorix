import React from "react";
import { Workload, Deployment, EvaluationRun, Incident, CostSummary } from "../types";
import {
  Boxes,
  ShieldCheck,
  AlertTriangle,
  Coins,
  Rocket,
  ArrowRight,
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
      <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-bold text-blue-600 tracking-wider">Production Platform Overview</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Self-Service AI/ML Infrastructure</h1>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Build, evaluate with strict release policy gates, deploy with Blue/Green safety, monitor token costs, and remediate incidents across your ML models, RAG pipelines, and LangGraph agents.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => onNavigate("evaluations")}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-all flex items-center gap-2 cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4" />
            Run Release Gate
          </button>
          <button
            onClick={() => onNavigate("agent_studio")}
            className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 shadow-xs transition-all flex items-center gap-2 cursor-pointer"
          >
            <Rocket className="w-4 h-4 text-blue-600" />
            Launch Agent Studio
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Workloads */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Active Workloads</span>
            <Boxes className="w-4 h-4 text-blue-600" />
          </div>
          <div className="mt-3 text-3xl font-bold text-slate-900">{workloads.length}</div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center gap-1.5">
            <span className="text-blue-600 font-semibold">{workloads.filter((w) => w.type === "agent").length} agents</span>
            <span>•</span>
            <span className="text-indigo-600 font-semibold">{workloads.filter((w) => w.type === "rag").length} RAG</span>
            <span>•</span>
            <span className="text-emerald-600 font-semibold">{workloads.filter((w) => w.type === "ml_model").length} ML models</span>
          </div>
        </div>

        {/* Evaluation Pass Rate */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Release Gate Pass Rate</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-3 text-3xl font-bold text-emerald-600">{passRate}%</div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center gap-1">
            <span>{passedEvals} allowed of {evaluations.length} evaluation suites</span>
          </div>
        </div>

        {/* FinOps Spend */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Total FinOps Spend</span>
            <Coins className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-3 text-3xl font-bold text-slate-900 font-mono">
            ${costs ? costs.total_cost.toFixed(4) : "0.0000"}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center gap-1">
            <span>{costs?.total_requests || 0} tracked LLM / embedding requests</span>
          </div>
        </div>

        {/* Open Incidents */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Open Incidents & RCA</span>
            <AlertTriangle className={`w-4 h-4 ${openIncidents.length > 0 ? "text-rose-500" : "text-emerald-600"}`} />
          </div>
          <div className={`mt-3 text-3xl font-bold ${openIncidents.length > 0 ? "text-rose-600" : "text-emerald-600"}`}>
            {openIncidents.length}
          </div>
          <div className="mt-2 text-[11px] text-slate-500">
            {openIncidents.length > 0 ? "Requires automated or operator rollback" : "All platform SLOs healthy"}
          </div>
        </div>
      </div>

      {/* Two Column Layout: Workloads & Recent Deployments */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workloads List */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-900">Registered Workloads</h2>
            <button
              onClick={() => onNavigate("projects")}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 cursor-pointer"
            >
              Manage all <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2.5">
            {workloads.map((w) => (
              <div
                key={w.id}
                className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between hover:bg-slate-100/70 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${
                      w.status === "healthy" ? "bg-emerald-500" : "bg-amber-500"
                    }`}
                  />
                  <div>
                    <div className="text-xs font-bold text-slate-800">{w.name}</div>
                    <div className="text-[11px] text-slate-500 font-mono">ID: {w.id}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                    {w.type.toUpperCase()}
                  </span>
                  <span className="text-xs font-mono text-blue-700 px-2.5 py-0.5 rounded bg-blue-50 border border-blue-200 font-medium">
                    {w.active_version || "no active version"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Deployments Rollout */}
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-900">Recent Deployments</h2>
            <button
              onClick={() => onNavigate("deployments")}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 cursor-pointer"
            >
              View rollout <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {deployments.slice(0, 4).map((d) => (
              <div key={d.id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-semibold text-slate-900">{d.version}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase border ${
                      d.status === "active"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : d.status === "rolled_back"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : "bg-slate-100 text-slate-600 border-slate-200"
                    }`}
                  >
                    {d.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <span>Env: {d.environment}</span>
                  <span>Strategy: {d.strategy}</span>
                  <span className="font-mono text-blue-700 font-semibold">{d.traffic_percentage}% traffic</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
