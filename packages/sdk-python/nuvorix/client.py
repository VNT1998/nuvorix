from typing import Any

import httpx


class _ResourceBase:
    def __init__(self, client: "NuvorixClient"):
        self._client = client


class ProjectsResource(_ResourceBase):
    def list(self) -> list[dict[str, Any]]:
        return self._client._get("/api/v1/projects")

    def create(self, name: str, description: str = "") -> dict[str, Any]:
        return self._client._post("/api/v1/projects", {"name": name, "description": description})

    def get(self, project_id: str) -> dict[str, Any]:
        return self._client._get(f"/api/v1/projects/{project_id}")


class WorkloadsResource(_ResourceBase):
    def list(self) -> list[dict[str, Any]]:
        return self._client._get("/api/v1/workloads")

    def create(self, project_id: str, name: str, workload_type: str = "agent") -> dict[str, Any]:
        return self._client._post(f"/api/v1/projects/{project_id}/workloads", {"name": name, "type": workload_type})

    def get(self, workload_id: str) -> dict[str, Any]:
        return self._client._get(f"/api/v1/workloads/{workload_id}")


class ModelsResource(_ResourceBase):
    def train(self, workload_id: str, model_name: str = "regressor", hyperparameters: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"model_name": model_name, "hyperparameters": hyperparameters or {}}
        return self._client._post(f"/api/v1/workloads/{workload_id}/train", payload)

    def promote(self, version_id: str, target_environment: str = "staging") -> dict[str, Any]:
        return self._client._post(f"/api/v1/model-versions/{version_id}/promote", {"target_environment": target_environment})


class EvaluationsResource(_ResourceBase):
    def run(self, workload_id: str, version: str, policy: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"version": version}
        if policy:
            payload["policy"] = policy
        return self._client._post(f"/api/v1/workloads/{workload_id}/evaluations", payload)


class DeploymentsResource(_ResourceBase):
    def create(self, workload_id: str, version: str, environment: str = "staging", strategy: str = "blue_green") -> dict[str, Any]:
        return self._client._post(
            f"/api/v1/workloads/{workload_id}/deployments",
            {"version": version, "environment": environment, "strategy": strategy},
        )

    def rollback(self, deployment_id: str) -> dict[str, Any]:
        return self._client._post(f"/api/v1/deployments/{deployment_id}/rollback")


class KnowledgeResource(_ResourceBase):
    def ingest(self, kb_id: str, title: str, content: str, source_uri: str = "sdk_upload") -> dict[str, Any]:
        return self._client._post(
            f"/api/v1/knowledge-bases/{kb_id}/documents",
            {"title": title, "content": content, "source_uri": source_uri},
        )

    def query(self, kb_id: str, query: str, top_k: int = 4) -> dict[str, Any]:
        return self._client._post(f"/api/v1/knowledge-bases/{kb_id}/query", {"query": query, "top_k": top_k})


class AgentsResource(_ResourceBase):
    def run(self, workload_id: str, prompt: str, allow_high_risk: bool = False) -> dict[str, Any]:
        return self._client._post(
            f"/api/v1/workloads/{workload_id}/agents/run",
            {"prompt": prompt, "allow_high_risk_tools": allow_high_risk},
        )


class IncidentsResource(_ResourceBase):
    def list(self) -> list[dict[str, Any]]:
        return self._client._get("/api/v1/incidents")

    def remediate(self, incident_id: str, action: str = "rollback") -> dict[str, Any]:
        return self._client._post(f"/api/v1/incidents/{incident_id}/remediate", {"action": action})


class CostsResource(_ResourceBase):
    def get_summary(self, workload_id: str | None = None) -> dict[str, Any]:
        endpoint = f"/api/v1/costs?workload_id={workload_id}" if workload_id else "/api/v1/costs"
        return self._client._get(endpoint)


class NuvorixClient:
    """Nuvorix Python SDK Client."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str | None = None, role: str = "admin"):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json", "X-User-Role": role}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        self.projects = ProjectsResource(self)
        self.workloads = WorkloadsResource(self)
        self.models = ModelsResource(self)
        self.evaluations = EvaluationsResource(self)
        self.deployments = DeploymentsResource(self)
        self.knowledge = KnowledgeResource(self)
        self.agents = AgentsResource(self)
        self.incidents = IncidentsResource(self)
        self.costs = CostsResource(self)

    def _get(self, path: str) -> Any:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30.0) as client:
            resp = client.get(path)
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30.0) as client:
            resp = client.post(path, json=payload or {})
            resp.raise_for_status()
            return resp.json()

    def health(self) -> dict[str, Any]:
        return self._get("/health")
