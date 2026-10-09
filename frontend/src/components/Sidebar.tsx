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
    {
      id: "incidents",
      label: "Incidents & RCA",
      icon: AlertTriangle,
      badge: incidentsCount > 0 ? incidentsCount : undefined,
      badgeColor: "bg-rose-50 text-rose-700 border-rose-200",
    },
    { id: "audit", label: "Security & Audit Trail", icon: History },
  ];

  return (
    <aside className="w-64 border-r border-slate-200 bg-white p-4 flex flex-col justify-between shrink-0 shadow-2xs">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
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
                  ? "bg-blue-50 text-blue-700 font-semibold border border-blue-200/80 shadow-2xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                    item.badgeColor || "bg-slate-100 text-slate-700 border-slate-200"
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
      <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1.5 shadow-2xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Core Runtime</span>
          <span className="font-mono text-slate-800 font-semibold">uv + Python 3.12</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">UI Stack</span>
          <span className="font-mono text-slate-800 font-semibold">Vite + React 19</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">API Contract</span>
          <span className="font-mono text-emerald-700 font-semibold">REST + MCP 2.0</span>
        </div>
      </div>
    </aside>
  );
};
