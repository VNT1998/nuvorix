import {
  Project,
  Workload,
  ModelVersion,
  EvaluationRun,
  Deployment,
  Incident,
  KnowledgeBase,
  KnowledgeDocument,
  QueryResponse,
  AgentRunResponse,
  ToolDeclaration,
  CostSummary,
  AuditEvent,
  HealthStatus,
} from "../types";

class ApiClient {
  private role: string = "admin";

  setRole(newRole: string) {
    this.role = newRole;
  }

  getRole() {
    return this.role;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");
    headers.set("X-User-Role", this.role);

    const res = await fetch(path, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errorMsg = errJson.detail;
      } catch (_) {
        // use default error message
      }
      throw new Error(errorMsg);
    }

    if (res.status === 204) {
      return {} as T;
    }
    return res.json();
  }

  // Health
  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>("/health");
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>("/api/v1/projects");
  }

  async createProject(name: string, description: string = ""): Promise<Project> {
    return this.request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  }

  async deleteProject(id: string): Promise<void> {
    return this.request<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
  }

  // Workloads
  async getWorkloads(): Promise<Workload[]> {
    return this.request<Workload[]>("/api/v1/workloads");
  }

  async createWorkload(projectId: string, name: string, type: string): Promise<Workload> {
    return this.request<Workload>(`/api/v1/projects/${projectId}/workloads`, {
      method: "POST",
      body: JSON.stringify({ name, type }),
    });
  }

  // ML Training
  async trainModel(workloadId: string, modelName: string, alpha: number, maxIter: number) {
    return this.request<any>(`/api/v1/workloads/${workloadId}/train`, {
      method: "POST",
      body: JSON.stringify({
        model_name: modelName,
        hyperparameters: { alpha, max_iter: maxIter },
      }),
    });
  }

  async getModelVersions(modelId: string): Promise<ModelVersion[]> {
    return this.request<ModelVersion[]>(`/api/v1/models/${modelId}/versions`);
  }

  async promoteModelVersion(versionId: string, targetEnv: string) {
    return this.request<any>(`/api/v1/model-versions/${versionId}/promote`, {
      method: "POST",
      body: JSON.stringify({ target_environment: targetEnv }),
    });
  }

  // RAG
  async getKnowledgeBases(): Promise<KnowledgeBase[]> {
    return this.request<KnowledgeBase[]>("/api/v1/knowledge-bases");
  }

  async createKnowledgeBase(projectId: string, name: string, description: string): Promise<KnowledgeBase> {
    return this.request<KnowledgeBase>(`/api/v1/projects/${projectId}/knowledge-bases`, {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  }

  async getDocuments(kbId: string): Promise<KnowledgeDocument[]> {
    return this.request<KnowledgeDocument[]>(`/api/v1/knowledge-bases/${kbId}/documents`);
  }

  async ingestDocument(kbId: string, title: string, content: string, sourceUri: string): Promise<KnowledgeDocument> {
    return this.request<KnowledgeDocument>(`/api/v1/knowledge-bases/${kbId}/documents`, {
      method: "POST",
      body: JSON.stringify({ title, content, source_uri: sourceUri }),
    });
  }

  async queryKnowledge(kbId: string, query: string, topK: number = 4) {
    return this.request<QueryResponse>(`/api/v1/knowledge-bases/${kbId}/query`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  // Agents
  async runAgent(workloadId: string, prompt: string, kbId?: string, allowHighRisk: boolean = false): Promise<AgentRunResponse> {
    return this.request<AgentRunResponse>(`/api/v1/workloads/${workloadId}/agents/run`, {
      method: "POST",
      body: JSON.stringify({ prompt, knowledge_base_id: kbId, allow_high_risk_tools: allowHighRisk }),
    });
  }

  async getTools(): Promise<ToolDeclaration[]> {
    return this.request<ToolDeclaration[]>("/api/v1/agents/tools");
  }

  // Evaluations
  async getEvaluations(workloadId: string): Promise<EvaluationRun[]> {
    return this.request<EvaluationRun[]>(`/api/v1/workloads/${workloadId}/evaluations`);
  }

  async runEvaluation(workloadId: string, version: string, policy?: any): Promise<EvaluationRun> {
    return this.request<EvaluationRun>(`/api/v1/workloads/${workloadId}/evaluations`, {
      method: "POST",
      body: JSON.stringify({ version, policy }),
    });
  }

  // Deployments
  async getDeployments(): Promise<Deployment[]> {
    return this.request<Deployment[]>("/api/v1/deployments");
  }

  async createDeployment(workloadId: string, version: string, environment: string, strategy: string): Promise<Deployment> {
    return this.request<Deployment>(`/api/v1/workloads/${workloadId}/deployments`, {
      method: "POST",
      body: JSON.stringify({ version, environment, strategy }),
    });
  }

  async rollbackDeployment(deploymentId: string) {
    return this.request<any>(`/api/v1/deployments/${deploymentId}/rollback`, {
      method: "POST",
    });
  }

  // Incidents
  async getIncidents(): Promise<Incident[]> {
    return this.request<Incident[]>("/api/v1/incidents");
  }

  async remediateIncident(incidentId: string, action: string = "rollback") {
    return this.request<any>(`/api/v1/incidents/${incidentId}/remediate`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
  }

  // Gateway & FinOps
  async gatewayChat(workloadId: string, prompt: string, provider: string, model: string) {
    return this.request<any>(`/api/v1/workloads/${workloadId}/gateway/chat`, {
      method: "POST",
      body: JSON.stringify({ prompt, provider, model }),
    });
  }

  async getCosts(): Promise<CostSummary> {
    return this.request<CostSummary>("/api/v1/costs");
  }

  // Audit
  async getAuditEvents(): Promise<AuditEvent[]> {
    return this.request<AuditEvent[]>("/api/v1/audit-events");
  }
}

export const api = new ApiClient();
