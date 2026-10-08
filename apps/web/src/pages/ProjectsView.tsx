import React, { useState } from "react";
import { Project, Workload } from "../types";
import { Plus, FolderPlus, Layers, Trash2 } from "lucide-react";

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
          <h1 className="text-xl font-bold text-slate-900">Projects & Workloads</h1>
          <p className="text-xs text-slate-500 mt-1">
            Organize machine learning models, RAG subsystems, and agents under project boundaries.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 shadow-xs flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <FolderPlus className="w-3.5 h-3.5 text-blue-600" />
            New Project
          </button>
          <button
            onClick={() => setShowNewWorkloadModal(true)}
            className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer transition-all"
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
                  ? "bg-blue-50/40 border-blue-300 shadow-xs ring-1 ring-blue-200/60"
                  : "bg-white border-slate-200 hover:border-slate-300 shadow-xs"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Layers className={`w-4 h-4 ${isSelected ? "text-blue-600" : "text-slate-400"}`} />
                  <span className="text-xs font-bold text-slate-900">{p.name}</span>
                </div>
                {projects.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete project ${p.name}?`)) onDeleteProject(p.id);
                    }}
                    className="text-slate-400 hover:text-rose-600 transition-colors p-1 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <p className="text-[11px] text-slate-600 mt-2 line-clamp-2">{p.description || "No description provided."}</p>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span className="font-medium">{count} Workloads</span>
                <span className="font-mono text-[10px] text-slate-400">{p.id.slice(0, 14)}...</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Project's Workloads Table */}
      <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Workloads in <span className="text-blue-600 font-bold">{currentProject?.name}</span>
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Active lifecycle states, semantic versions, and deployment readiness.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
            {projectWorkloads.length} Workloads
          </span>
        </div>

        {projectWorkloads.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-200 rounded-lg">
            No workloads registered under this project yet. Click "New Workload" to add an ML Model, RAG Subsystem, or Agent.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] tracking-wider bg-slate-50/75">
                  <th className="py-2.5 px-3 font-semibold">Workload Name</th>
                  <th className="py-2.5 px-3 font-semibold">Type</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold">Active Version</th>
                  <th className="py-2.5 px-3 font-semibold">Workload ID</th>
                  <th className="py-2.5 px-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {projectWorkloads.map((w) => (
                  <tr key={w.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-3 font-medium text-slate-900 flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      {w.name}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                          w.type === "agent"
                            ? "bg-purple-50 text-purple-700 border-purple-200"
                            : w.type === "rag"
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200"
                        }`}
                      >
                        {w.type}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-[11px] text-emerald-700 font-semibold">{w.status}</span>
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-blue-700 font-semibold">
                      {w.active_version || "—"}
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-500">
                      {w.id}
                    </td>
                    <td className="py-3 px-3 text-slate-500 text-[11px]">
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-slate-900">Create Platform Project</h2>
            <form onSubmit={handleCreateProject} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. Risk Assessment Platform"
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Goals and platform scope..."
                  rows={3}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewProjectModal(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-slate-900">
              Create Workload in <span className="text-blue-600">{currentProject?.name}</span>
            </h2>
            <form onSubmit={handleCreateWorkload} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Workload Name</label>
                <input
                  type="text"
                  required
                  value={newWorkloadName}
                  onChange={(e) => setNewWorkloadName(e.target.value)}
                  placeholder="e.g. churn-predictor or support-agent"
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Workload Type</label>
                <select
                  value={newWorkloadType}
                  onChange={(e) => setNewWorkloadType(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs cursor-pointer"
                >
                  <option value="agent">Autonomous LangGraph Agent</option>
                  <option value="rag">RAG Retrieval Pipeline</option>
                  <option value="ml_model">Scikit-Learn ML Model</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewWorkloadModal(false)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer"
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
