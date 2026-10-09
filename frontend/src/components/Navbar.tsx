import React from "react";
import { Project, HealthStatus } from "../types";
import { Layers, ChevronDown, Shield } from "lucide-react";

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
    <header className="h-16 border-b border-slate-200 bg-white/95 backdrop-blur-sm px-6 flex items-center justify-between sticky top-0 z-40 shadow-xs">
      {/* Brand & Project Selector */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white text-xs tracking-tight shadow-xs">
            NX
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 tracking-tight text-base">NUVORIX</span>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                Control Plane
              </span>
            </div>
          </div>
        </div>

        {/* Project Selector */}
        <div className="h-5 w-[1px] bg-slate-200" />
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-slate-400" />
          <div className="relative">
            <select
              value={selectedProjectId}
              onChange={(e) => onSelectProject(e.target.value)}
              className="bg-white border border-slate-200 text-slate-800 text-xs rounded-md px-3 py-1.5 pr-8 appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs hover:border-slate-300 transition-colors cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Status & Role Switcher */}
      <div className="flex items-center gap-3">
        {/* System Health Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs shadow-2xs">
          <div
            className={`w-2 h-2 rounded-full ${
              health?.status === "healthy" ? "bg-emerald-500" : "bg-amber-500"
            }`}
          />
          <span className="text-slate-500">Platform:</span>
          <span className="font-semibold text-slate-800">
            {health ? health.status.toUpperCase() : "CHECKING..."}
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-500">DB:</span>
          <span className="font-mono text-[11px] text-emerald-700 font-semibold">{health?.database || "ready"}</span>
        </div>

        {/* RBAC Role Switcher */}
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-md px-3 py-1.5 text-xs shadow-2xs">
          <Shield className="w-3.5 h-3.5 text-blue-600" />
          <span className="text-slate-500">Role:</span>
          <select
            value={currentRole}
            onChange={(e) => onSelectRole(e.target.value)}
            className="bg-transparent text-slate-800 font-medium focus:outline-none cursor-pointer"
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
