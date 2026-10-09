export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface Workload {
  id: string;
  project_id: string;
  name: string;
  type: "ml_model" | "rag" | "agent" | "llm_service";
  status: string;
  active_version?: string | null;
  created_at: string;
}

export interface Model {
  id: string;
  workload_id: string;
  name: string;
  framework: string;
  created_at: string;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version: string;
  artifact_uri: string;
  metrics_json: Record<string, any>;
  parameters_json: Record<string, any>;
  status: string;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  workload_id: string;
  version: string;
  status: string;
  passed: boolean;
  decision: "ALLOW" | "BLOCK";
  metrics: Record<string, any>;
  reasons: string[];
  started_at: string;
  completed_at?: string | null;
}

export interface Deployment {
  id: string;
  workload_id: string;
  version: string;
  environment: "dev" | "staging" | "production";
  strategy: string;
  status: "active" | "candidate" | "retired" | "rolled_back" | "failed";
  traffic_percentage: number;
  created_at: string;
}

export interface Incident {
  id: string;
  project_id: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  title: string;
  status: "open" | "investigating" | "remediated" | "resolved";
  root_cause: string;
  recommendation: string;
  confidence: number;
  evidence: string[];
  created_at: string;
  resolved_at?: string | null;
}

export interface KnowledgeBase {
  id: string;
  project_id: string;
  name: string;
  description: string;
  embedding_model: string;
  created_at: string;
}

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  title: string;
  source_uri: string;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface RetrievalChunk {
  chunk_id: string;
  document_id: string;
  score: number;
  source: string;
  title: string;
  text: string;
}

export interface QueryResponse {
  query: string;
  knowledge_base_id: string;
  results: RetrievalChunk[];
}

export interface AgentStepTrace {
  step: number;
  stage: "planner" | "tool_call" | "observation" | "response";
  content: string;
  tool_name?: string | null;
  tool_input?: Record<string, any> | null;
  tool_output?: Record<string, any> | null;
  latency_ms: number;
}

export interface AgentRunResponse {
  workload_id: string;
  prompt: string;
  final_response: string;
  steps: AgentStepTrace[];
  tools_used: string[];
  total_tokens: number;
  estimated_cost: number;
  duration_ms: number;
}

export interface ToolDeclaration {
  name: string;
  description: string;
  risk: "low" | "high";
  required_permissions: string[];
}

export interface CostSummary {
  total_cost: number;
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  breakdown_by_model: Record<string, number>;
  breakdown_by_provider: Record<string, number>;
  breakdown_by_workload: Record<string, number>;
}

export interface AuditEvent {
  id: string;
  organization_id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  metadata: Record<string, any>;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  timestamp: string;
}
