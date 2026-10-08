from click.testing import CliRunner
from nuvorix import NuvorixClient
from nuvorix_cli.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Nuvorix CLI" in result.output
    assert "health" in result.output
    assert "project" in result.output
    assert "workload" in result.output
    assert "evaluate" in result.output
    assert "deploy" in result.output
    assert "rollback" in result.output


def test_sdk_instantiation():
    client = NuvorixClient(base_url="http://localhost:8000")
    assert client.base_url == "http://localhost:8000"
    assert hasattr(client, "projects")
    assert hasattr(client, "workloads")
    assert hasattr(client, "models")
    assert hasattr(client, "evaluations")
    assert hasattr(client, "deployments")
    assert hasattr(client, "knowledge")
    assert hasattr(client, "agents")
    assert hasattr(client, "incidents")
    assert hasattr(client, "costs")
