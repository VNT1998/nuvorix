import React from "react";
import { Project, HealthStatus } from "../types";
import { Activity, Shield, Layers, ChevronDown } from "lucide-react";

interface NavbarProps {
  projects: Project[];
  selectedProjectId: string;
  onSelectProject: (id: string) => void;
  currentRole: string;
  onSelectRole: (role: string) => void;
  health: HealthStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  currentRole,
  onSelectRole,
  health,
}) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Project Selector */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 via-indigo-500 to-fuchsia-500 p-[1px] shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[7px] flex items-center justify-center font-black text-cyan-400 text-sm tracking-tighter">
              NX
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100 tracking-wider text-base">NUVORIX</span>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Control Plane
              </span>
            </div>
          </div>
        </div>

        {/* Project Selector */}
        <div className="h-6 w-[1px] bg-slate-800" />
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-slate-400" />
          <div className="relative">
            <select
              value={selectedProjectId}
              onChange={(e) => onSelectProject(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-md px-3 py-1.5 pr-8 appearance-none focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Status & Role Switcher */}
      <div className="flex items-center gap-4">
        {/* System Health Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 text-xs">
          <div
            className={`w-2 h-2 rounded-full ${
              health?.status === "healthy" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
            }`}
          />
          <span className="text-slate-400">Platform:</span>
          <span className="font-medium text-slate-200">
            {health ? health.status.toUpperCase() : "CHECKING..."}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">DB:</span>
          <span className="font-mono text-[11px] text-emerald-400">{health?.database || "ready"}</span>
        </div>

        {/* RBAC Role Switcher */}
        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 rounded-md px-3 py-1.5 text-xs">
          <Shield className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-400">Role:</span>
          <select
            value={currentRole}
            onChange={(e) => onSelectRole(e.target.value)}
            className="bg-transparent text-indigo-300 font-medium focus:outline-none cursor-pointer"
          >
            <option value="admin">admin (Full Access)</option>
            <option value="platform_engineer">platform_engineer</option>
            <option value="ml_engineer">ml_engineer</option>
            <option value="developer">developer</option>
            <option value="viewer">viewer (Read Only)</option>
          </select>
        </div>
      </div>
    </header>
  );
};
