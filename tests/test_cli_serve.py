"""
Tests for the serve CLI command.
"""
import pytest
from typer.testing import CliRunner
from factory.cli import app

runner = CliRunner()


def test_serve_invalid_port_negative():
    """Test that negative port values are rejected."""
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.stdout


def test_serve_invalid_port_too_high():
    """Test that port values above 65535 are rejected."""
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.stdout


def test_serve_valid_port_zero(monkeypatch):
    """Test that port 0 is accepted (auto-select)."""
    import factory.cli as cli_module

    # Mock uvicorn.run to prevent actual server startup
    def mock_run(*args, **kwargs):
        pass

    monkeypatch.setattr("uvicorn.run", mock_run)

    result = runner.invoke(app, ["serve", "--port", "0"])
    assert result.exit_code == 0


def test_serve_valid_port_max(monkeypatch):
    """Test that port 65535 is accepted."""
    import factory.cli as cli_module

    # Mock uvicorn.run to prevent actual server startup
    def mock_run(*args, **kwargs):
        pass

    monkeypatch.setattr("uvicorn.run", mock_run)

    result = runner.invoke(app, ["serve", "--port", "65535"])
    assert result.exit_code == 0


def test_serve_default_host_and_port(monkeypatch):
    """Test that serve command has correct defaults."""
    import factory.cli as cli_module

    # Mock uvicorn.run to capture the arguments
    captured_args = {}

    def mock_run(*args, **kwargs):
        captured_args.update(kwargs)

    monkeypatch.setattr("uvicorn.run", mock_run)

    result = runner.invoke(app, ["serve"])
    assert result.exit_code == 0
    assert captured_args.get("host") == "127.0.0.1"
    assert captured_args.get("port") == 8000
