import sys

import click
import httpx

DEFAULT_BASE_URL = "http://localhost:8000"


def get_client(base_url: str):
    return httpx.Client(base_url=base_url.rstrip("/"), timeout=30.0)


@click.group()
@click.option("--base-url", default=DEFAULT_BASE_URL, help="Nuvorix API base URL.")
@click.pass_context
def cli(ctx, base_url):
    """Nuvorix CLI — AI/ML Production Platform."""
    ctx.ensure_object(dict)
    ctx.obj["BASE_URL"] = base_url


@cli.command()
@click.pass_context
def health(ctx):
    """Check health and readiness of Nuvorix platform."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        try:
            r = client.get("/health")
            r.raise_for_status()
            data = r.json()
            click.echo(f"Status: {data['status'].upper()} (Version: {data['version']})")
            click.echo(f"Database: {data['database']}")
        except Exception as e:
            click.echo(f"Error connecting to Nuvorix: {e}", err=True)
            sys.exit(1)


# --- Project Group ---
@cli.group()
def project():
    """Manage projects."""


@project.command("list")
@click.pass_context
def list_projects(ctx):
    """List all projects."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        r = client.get("/api/v1/projects")
        r.raise_for_status()
        for p in r.json():
            click.echo(f"[{p['id']}] {p['name']} — {p.get('description', '')}")


@project.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Project description")
@click.pass_context
def create_project(ctx, name, description):
    """Create a new project."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        r = client.post("/api/v1/projects", json={"name": name, "description": description})
        r.raise_for_status()
        p = r.json()
        click.echo(f"Created project: [{p['id']}] {p['name']}")


# --- Workload Group ---
@cli.group()
def workload():
    """Manage workloads."""


@workload.command("list")
@click.pass_context
def list_workloads(ctx):
    """List all workloads."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        r = client.get("/api/v1/workloads")
        r.raise_for_status()
        for w in r.json():
            click.echo(f"[{w['id']}] {w['name']} (Type: {w['type']}, Active Version: {w.get('active_version', 'none')})")


@workload.command("create")
@click.argument("project_id")
@click.argument("name")
@click.option("--type", "-t", default="agent", type=click.Choice(["ml_model", "rag", "agent", "llm_service"]))
@click.pass_context
def create_workload(ctx, project_id, name, type):
    """Create a workload under a project."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        r = client.post(f"/api/v1/projects/{project_id}/workloads", json={"name": name, "type": type})
        r.raise_for_status()
        w = r.json()
        click.echo(f"Created workload: [{w['id']}] {w['name']} ({w['type']})")


# --- Evaluation Command ---
@cli.command()
@click.argument("workload_id")
@click.option("--version", "-v", default="v1.0.0", help="Candidate version to evaluate")
@click.pass_context
def evaluate(ctx, workload_id, version):
    """Run automated evaluation and release policy gate."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        click.echo(f"Triggering evaluation suite for workload {workload_id} version {version}...")
        r = client.post(f"/api/v1/workloads/{workload_id}/evaluations", json={"version": version})
        r.raise_for_status()
        e = r.json()
        click.echo(f"Decision: {e['decision']} (Passed: {e['passed']})")
        if e["reasons"]:
            click.echo("Gate Violations:")
            for reason in e["reasons"]:
                click.echo(f" - {reason}")
        else:
            click.echo("Quality Gate: All policies passed cleanly!")


# --- Deployment Group ---
@cli.command()
@click.argument("workload_id")
@click.option("--version", "-v", required=True, help="Version to deploy")
@click.option("--env", "-e", default="staging", help="Target environment")
@click.option("--strategy", "-s", default="blue_green", help="Deployment strategy")
@click.pass_context
def deploy(ctx, workload_id, version, env, strategy):
    """Deploy a workload version to target environment."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        click.echo(f"Deploying {workload_id} ({version}) to {env} via {strategy}...")
        try:
            r = client.post(
                f"/api/v1/workloads/{workload_id}/deployments",
                json={"version": version, "environment": env, "strategy": strategy},
            )
            r.raise_for_status()
            d = r.json()
            click.echo(f"Deployment [{d['id']}] successfully launched with {d['traffic_percentage']}% traffic.")
        except httpx.HTTPStatusError as err:
            click.echo(f"Deployment blocked: {err.response.json().get('detail', str(err))}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("deployment_id")
@click.pass_context
def rollback(ctx, deployment_id):
    """Rollback a deployment to its previous active version."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        click.echo(f"Executing rollback for deployment {deployment_id}...")
        r = client.post(f"/api/v1/deployments/{deployment_id}/rollback")
        r.raise_for_status()
        res = r.json()
        click.echo(f"Rollback Complete: Active version restored to {res['active_version']}.")
        click.echo(f"Message: {res['message']}")


# --- Agent Run Command ---
@cli.command("agent-run")
@click.argument("workload_id")
@click.argument("prompt")
@click.pass_context
def agent_run(ctx, workload_id, prompt):
    """Execute LangGraph agent workflow with prompt."""
    base_url = ctx.obj["BASE_URL"]
    with get_client(base_url) as client:
        click.echo(f"Running agent on workload {workload_id}...")
        r = client.post(f"/api/v1/workloads/{workload_id}/agents/run", json={"prompt": prompt})
        r.raise_for_status()
        data = r.json()
        click.echo(f"\nResponse:\n{data['final_response']}\n")
        click.echo(f"Tools Used: {', '.join(data['tools_used']) if data['tools_used'] else 'None'}")
        click.echo(f"Duration: {data['duration_ms']}ms | Cost: ${data['estimated_cost']}")


if __name__ == "__main__":
    cli()
