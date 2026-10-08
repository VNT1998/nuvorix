import React from "react";
import {
  LayoutDashboard,
  Boxes,
  Cpu,
  BookOpen,
  Bot,
  ShieldCheck,
  Rocket,
  Coins,
  AlertTriangle,
  History,
} from "lucide-react";

export type NavView =
  | "dashboard"
  | "projects"
  | "ml_studio"
  | "rag_hub"
  | "agent_studio"
  | "evaluations"
  | "deployments"
  | "gateway"
  | "incidents"
  | "audit";

interface SidebarProps {
  activeView: NavView;
  onSelectView: (view: NavView) => void;
  incidentsCount?: number;
  workloadsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onSelectView,
  incidentsCount = 0,
  workloadsCount = 0,
}) => {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "projects", label: "Workloads & Projects", icon: Boxes, badge: workloadsCount > 0 ? workloadsCount : undefined },
    { id: "ml_studio", label: "ML Training Studio", icon: Cpu },
    { id: "rag_hub", label: "RAG & Knowledge", icon: BookOpen },
    { id: "agent_studio", label: "Agent Runtime & MCP", icon: Bot },
    { id: "evaluations", label: "Quality Release Gates", icon: ShieldCheck },
    { id: "deployments", label: "Deployments & Rollout", icon: Rocket },
    { id: "gateway", label: "LLM Gateway & FinOps", icon: Coins },
    { id: "incidents", label: "Incidents & RCA", icon: AlertTriangle, badge: incidentsCount > 0 ? incidentsCount : undefined, badgeColor: "bg-rose-500/20 text-rose-300 border-rose-500/30" },
    { id: "audit", label: "Security & Audit Trail", icon: History },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950/60 p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
          Platform Engineering
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectView(item.id as NavView)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                    item.badgeColor || "bg-slate-800 text-slate-300 border-slate-700"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Core Runtime</span>
          <span className="font-mono text-cyan-400">uv + Python 3.12</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">UI Stack</span>
          <span className="font-mono text-indigo-400">Vite + React 19</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Local Orchestration</span>
          <span className="font-mono text-emerald-400">Docker / kind</span>
        </div>
      </div>
    </aside>
  );
};
