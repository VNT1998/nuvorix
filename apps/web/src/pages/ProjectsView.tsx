import React, { useState } from "react";
import { Project, Workload } from "../types";
import { Plus, Boxes, FolderPlus, Layers, Trash2 } from "lucide-react";

interface ProjectsViewProps {
  projects: Project[];
  workloads: Workload[];
  selectedProjectId: string;
  onSelectProject: (id: string) => void;
  onCreateProject: (name: string, description: string) => Promise<void>;
  onCreateWorkload: (projectId: string, name: string, type: string) => Promise<void>;
  onDeleteProject: (id: string) => Promise<void>;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({
  projects,
  workloads,
  selectedProjectId,
  onSelectProject,
  onCreateProject,
  onCreateWorkload,
  onDeleteProject,
}) => {
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");

  const [showNewWorkloadModal, setShowNewWorkloadModal] = useState(false);
  const [newWorkloadName, setNewWorkloadName] = useState("");
  const [newWorkloadType, setNewWorkloadType] = useState("agent");

  const [loading, setLoading] = useState(false);

  const currentProject = projects.find((p) => p.id === selectedProjectId) || projects[0];
  const projectWorkloads = workloads.filter((w) => w.project_id === selectedProjectId);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setLoading(true);
    try {
      await onCreateProject(newProjectName, newProjectDesc);
      setNewProjectName("");
      setNewProjectDesc("");
      setShowNewProjectModal(false);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkloadName.trim() || !selectedProjectId) return;
    setLoading(true);
    try {
      await onCreateWorkload(selectedProjectId, newWorkloadName, newWorkloadType);
      setNewWorkloadName("");
      setShowNewWorkloadModal(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Projects & Workloads</h1>
          <p className="text-xs text-slate-400 mt-1">
            Organize machine learning models, RAG subsystems, and agents under project boundaries.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <FolderPlus className="w-3.5 h-3.5 text-indigo-400" />
            New Project
          </button>
          <button
            onClick={() => setShowNewWorkloadModal(true)}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            New Workload
          </button>
        </div>
      </div>

      {/* Projects Grid / Selector Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {projects.map((p) => {
          const isSelected = p.id === selectedProjectId;
          const count = workloads.filter((w) => w.project_id === p.id).length;
          return (
            <div
              key={p.id}
              onClick={() => onSelectProject(p.id)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                isSelected
                  ? "bg-indigo-950/20 border-indigo-500/50 shadow-md shadow-indigo-500/10"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Layers className={`w-4 h-4 ${isSelected ? "text-indigo-400" : "text-slate-500"}`} />
                  <span className="text-xs font-bold text-slate-200">{p.name}</span>
                </div>
                {projects.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete project ${p.name}?`)) onDeleteProject(p.id);
                    }}
                    className="text-slate-600 hover:text-rose-400 transition-colors p-1"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-2 line-clamp-2">{p.description || "No description provided."}</p>
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                <span>{count} Workloads</span>
                <span className="font-mono text-[10px] text-slate-600">{p.id.slice(0, 14)}...</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Project's Workloads Table */}
      <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">
              Workloads in <span className="text-indigo-400 font-bold">{currentProject?.name}</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Active lifecycle states, semantic versions, and deployment readiness.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-300">
            {projectWorkloads.length} Workloads
          </span>
        </div>

        {projectWorkloads.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-lg">
            No workloads registered under this project yet. Click "New Workload" to add an ML Model, RAG Subsystem, or Agent.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                  <th className="pb-3 font-semibold">Workload Name</th>
                  <th className="pb-3 font-semibold">Type</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Active Version</th>
                  <th className="pb-3 font-semibold">Workload ID</th>
                  <th className="pb-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {projectWorkloads.map((w) => (
                  <tr key={w.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 font-medium text-slate-200 flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-400" />
                      {w.name}
                    </td>
                    <td className="py-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                          w.type === "agent"
                            ? "bg-purple-500/10 text-purple-300 border-purple-500/20"
                            : w.type === "rag"
                            ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
                            : "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                        }`}
                      >
                        {w.type}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="text-[11px] text-emerald-400 font-medium">{w.status}</span>
                    </td>
                    <td className="py-3 font-mono text-[11px] text-cyan-400">
                      {w.active_version || "—"}
                    </td>
                    <td className="py-3 font-mono text-[11px] text-slate-500">
                      {w.id}
                    </td>
                    <td className="py-3 text-slate-500 text-[11px]">
                      {new Date(w.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-base font-bold text-slate-100">Create Platform Project</h2>
            <form onSubmit={handleCreateProject} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. Risk Assessment Platform"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Goals and platform scope..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewProjectModal(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 cursor-pointer"
                >
                  {loading ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Workload Modal */}
      {showNewWorkloadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <h2 className="text-base font-bold text-slate-100">Create Workload</h2>
            <form onSubmit={handleCreateWorkload} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Workload Name</label>
                <input
                  type="text"
                  required
                  value={newWorkloadName}
                  onChange={(e) => setNewWorkloadName(e.target.value)}
                  placeholder="e.g. support-agent or churn-model"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Workload Type</label>
                <select
                  value={newWorkloadType}
                  onChange={(e) => setNewWorkloadType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="agent">Agent (LangGraph + MCP Tools)</option>
                  <option value="rag">RAG Subsystem (Knowledge Base + Vectors)</option>
                  <option value="ml_model">ML Model (Scikit-Learn / MLflow)</option>
                  <option value="llm_service">LLM Service (Gateway Router)</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewWorkloadModal(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 cursor-pointer"
                >
                  {loading ? "Creating..." : "Create Workload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
