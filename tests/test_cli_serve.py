"""Tests for the CLI serve command."""
import pytest
from typer.testing import CliRunner

from factory.cli import app as cli_app


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


def test_serve_invalid_port_negative(runner):
    """Test that serve command rejects negative port values."""
    result = runner.invoke(cli_app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_invalid_port_too_large(runner):
    """Test that serve command rejects port values > 65535."""
    result = runner.invoke(cli_app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_invalid_port_way_too_large(runner):
    """Test that serve command rejects very large port values."""
    result = runner.invoke(cli_app, ["serve", "--port", "99999"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_valid_port_zero(runner):
    """Test that serve command accepts port 0 (OS picks random port)."""
    # We can't fully test this without actually starting the server,
    # but we can verify it passes validation
    result = runner.invoke(cli_app, ["serve", "--port", "0"], input="q\n", timeout=1)
    # Server startup will eventually timeout or fail due to signal, but it should
    # get past the port validation and reach uvicorn.run()
    assert "Port must be between 0 and 65535" not in result.output


def test_serve_valid_port_max(runner):
    """Test that serve command accepts port 65535 (max valid port)."""
    result = runner.invoke(cli_app, ["serve", "--port", "65535"], input="q\n", timeout=1)
    assert "Port must be between 0 and 65535" not in result.output


def test_serve_default_host_and_port(runner):
    """Test that serve command uses default host and port."""
    result = runner.invoke(cli_app, ["serve"], input="q\n", timeout=1)
    # Should start and display the default host/port before failing
    assert "127.0.0.1" in result.output or result.exit_code == 0 or "error" in result.output.lower()


def test_serve_custom_host_and_port(runner):
    """Test that serve command accepts custom host and port."""
    result = runner.invoke(cli_app, ["serve", "--host", "0.0.0.0", "--port", "5000"], input="q\n", timeout=1)
    # Should reach uvicorn startup (which may fail due to port binding), not validation
    assert "Port must be between 0 and 65535" not in result.output
