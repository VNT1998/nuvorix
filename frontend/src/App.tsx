import React, { useState, useEffect, useCallback } from "react";
import {
  Project,
  Workload,
  Deployment,
  EvaluationRun,
  Incident,
  KnowledgeBase,
  CostSummary,
  HealthStatus,
} from "./types";
import { api } from "./lib/api";
import { Navbar } from "./components/Navbar";
import { Sidebar, NavView } from "./components/Sidebar";
import { ErrorBoundary } from "./components/ErrorBoundary";

import { DashboardView } from "./pages/DashboardView";
import { ProjectsView } from "./pages/ProjectsView";
import { MLStudioView } from "./pages/MLStudioView";
import { RAGHubView } from "./pages/RAGHubView";
import { AgentStudioView } from "./pages/AgentStudioView";
import { EvaluationGatesView } from "./pages/EvaluationGatesView";
import { DeploymentsView } from "./pages/DeploymentsView";
import { LLMGatewayView } from "./pages/LLMGatewayView";
import { IncidentsView } from "./pages/IncidentsView";
import { AuditTrailView } from "./pages/AuditTrailView";

const VALID_VIEWS: NavView[] = [
  "dashboard",
  "projects",
  "ml_studio",
  "rag_hub",
  "agent_studio",
  "evaluations",
  "deployments",
  "gateway",
  "incidents",
  "audit",
];

const getInitialView = (): NavView => {
  const hash = window.location.hash.replace("#", "") as NavView;
  return VALID_VIEWS.includes(hash) ? hash : "dashboard";
};

export function App() {
  const [activeView, setActiveView] = useState<NavView>(getInitialView);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [workloads, setWorkloads] = useState<Workload[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationRun[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [costs, setCosts] = useState<CostSummary | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [userRole, setUserRole] = useState("admin");

  const [loading, setLoading] = useState(true);

  const loadInitialData = useCallback(async () => {
    try {
      // 1. Health
      try {
        const h = await api.getHealth();
        setHealth(h);
      } catch (_) {}

      // 2. Projects
      const projs = await api.getProjects();
      setProjects(projs);
      if (projs.length > 0) {
        setSelectedProjectId((prev) => prev || projs[0].id);
      }

      // 3. Workloads
      const wl = await api.getWorkloads();
      setWorkloads(wl);

      // 4. Deployments
      const dep = await api.getDeployments();
      setDeployments(dep);

      // 5. Evaluations (fetch for first workload if available)
      if (wl.length > 0) {
        const evals = await api.getEvaluations(wl[0].id);
        setEvaluations(evals);
      }

      // 6. Incidents
      const inc = await api.getIncidents();
      setIncidents(inc);

      // 7. Knowledge Bases
      const kbs = await api.getKnowledgeBases();
      setKnowledgeBases(kbs);

      // 8. Costs
      const c = await api.getCosts();
      setCosts(c);
    } catch (err) {
      console.error("Error loading initial data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();

    const onHashChange = () => {
      const hash = window.location.hash.replace("#", "") as NavView;
      if (VALID_VIEWS.includes(hash)) {
        setActiveView(hash);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [loadInitialData]);

  const handleSelectView = (view: NavView) => {
    setActiveView(view);
    window.location.hash = view;
  };

  const handleRoleChange = (role: string) => {
    setUserRole(role);
    api.setRole(role);
  };

  const handleCreateProject = async (name: string, description: string) => {
    const newProj = await api.createProject(name, description);
    setProjects([newProj, ...projects]);
    setSelectedProjectId(newProj.id);
  };

  const handleDeleteProject = async (id: string) => {
    await api.deleteProject(id);
    const remaining = projects.filter((p) => p.id !== id);
    setProjects(remaining);
    if (selectedProjectId === id && remaining.length > 0) {
      setSelectedProjectId(remaining[0].id);
    }
  };

  const handleCreateWorkload = async (projectId: string, name: string, type: string) => {
    const newW = await api.createWorkload(projectId, name, type);
    setWorkloads([newW, ...workloads]);
  };

  const refreshWorkloads = async () => {
    const wl = await api.getWorkloads();
    setWorkloads(wl);
  };

  const refreshDeployments = async () => {
    const dep = await api.getDeployments();
    setDeployments(dep);
  };

  const refreshIncidents = async () => {
    const inc = await api.getIncidents();
    setIncidents(inc);
  };

  const refreshEvaluations = async () => {
    if (workloads.length > 0) {
      const evals = await api.getEvaluations(workloads[0].id);
      setEvaluations(evals);
    }
  };

  const refreshKBs = async () => {
    const kbs = await api.getKnowledgeBases();
    setKnowledgeBases(kbs);
  };

  const refreshCosts = async () => {
    const c = await api.getCosts();
    setCosts(c);
  };

  const openIncidentsCount = incidents.filter((i) => i.status !== "resolved").length;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Navbar
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={setSelectedProjectId}
        currentRole={userRole}
        onSelectRole={handleRoleChange}
        health={health}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          activeView={activeView}
          onSelectView={handleSelectView}
          incidentsCount={openIncidentsCount}
          workloadsCount={workloads.length}
        />

        <main className="flex-1 overflow-y-auto p-8 max-w-7xl mx-auto w-full">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-slate-500 text-xs font-mono">
              Connecting to Nuvorix Control Plane...
            </div>
          ) : (
            <ErrorBoundary fallbackTitle="View Failed to Render">
              {activeView === "dashboard" && (
                <DashboardView
                  workloads={workloads}
                  deployments={deployments}
                  evaluations={evaluations}
                  incidents={incidents}
                  costs={costs}
                  onNavigate={handleSelectView}
                />
              )}

              {activeView === "projects" && (
                <ProjectsView
                  projects={projects}
                  workloads={workloads}
                  selectedProjectId={selectedProjectId}
                  onSelectProject={setSelectedProjectId}
                  onCreateProject={handleCreateProject}
                  onCreateWorkload={handleCreateWorkload}
                  onDeleteProject={handleDeleteProject}
                />
              )}

              {activeView === "ml_studio" && (
                <MLStudioView
                  workloads={workloads}
                  onRefreshWorkloads={refreshWorkloads}
                />
              )}

              {activeView === "rag_hub" && (
                <RAGHubView
                  knowledgeBases={knowledgeBases}
                  selectedProjectId={selectedProjectId}
                  onRefreshKBs={refreshKBs}
                />
              )}

              {activeView === "agent_studio" && (
                <AgentStudioView
                  workloads={workloads}
                  knowledgeBases={knowledgeBases}
                />
              )}

              {activeView === "evaluations" && (
                <EvaluationGatesView
                  workloads={workloads}
                  onRefreshEvaluations={refreshEvaluations}
                />
              )}

              {activeView === "deployments" && (
                <DeploymentsView
                  workloads={workloads}
                  deployments={deployments}
                  onRefreshDeployments={refreshDeployments}
                  onRefreshWorkloads={refreshWorkloads}
                />
              )}

              {activeView === "gateway" && (
                <LLMGatewayView
                  workloads={workloads}
                  costs={costs}
                  onRefreshCosts={refreshCosts}
                />
              )}

              {activeView === "incidents" && (
                <IncidentsView
                  incidents={incidents}
                  onRefreshIncidents={refreshIncidents}
                  onRefreshDeployments={refreshDeployments}
                  onRefreshWorkloads={refreshWorkloads}
                />
              )}

              {activeView === "audit" && <AuditTrailView />}
            </ErrorBoundary>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
