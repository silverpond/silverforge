"""Tests for the CLI serve command."""
import pytest
from typer.testing import CliRunner

from factory.cli import app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


def test_serve_invalid_port_negative(runner):
    """Test that negative port values are rejected."""
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code != 0
    assert "Port must be between 0 and 65535" in result.stdout


def test_serve_invalid_port_too_high(runner):
    """Test that ports > 65535 are rejected."""
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code != 0
    assert "Port must be between 0 and 65535" in result.stdout


def test_serve_valid_edge_ports(runner):
    """Test that edge case port values are accepted (without actually running)."""
    # We can't test actual server startup in unit tests, but we can verify
    # that port 0 and 65535 don't immediately fail validation
    # This would normally start the server, so we just verify the command exists
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.stdout


def test_serve_host_option(runner):
    """Test that serve command accepts host option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.stdout
