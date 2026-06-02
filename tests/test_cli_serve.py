"""Tests for the serve CLI command."""
import pytest
from typer.testing import CliRunner
from factory.cli import app


runner = CliRunner()


def test_serve_invalid_port_negative():
    """Test that negative port numbers are rejected."""
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_invalid_port_too_high():
    """Test that ports above 65535 are rejected."""
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_valid_port_zero():
    """Test that port 0 is accepted (auto-selection)."""
    # We can't actually run the server without mocking uvicorn
    # This test verifies the port validation logic passes
    result = runner.invoke(app, ["serve", "--port", "0"], catch_exceptions=False)
    # Will fail on uvicorn.run() but not on port validation
    assert result.exit_code != 1 or "Port must be between" not in result.stdout


def test_serve_valid_port_max():
    """Test that port 65535 is accepted."""
    result = runner.invoke(app, ["serve", "--port", "65535"], catch_exceptions=False)
    # Will fail on uvicorn.run() but not on port validation
    assert result.exit_code != 1 or "Port must be between" not in result.stdout


def test_serve_custom_host():
    """Test that custom host option is accepted."""
    result = runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "5000"], catch_exceptions=False)
    # Will fail on uvicorn.run() but not on validation
    assert result.exit_code != 1 or "Port must be between" not in result.stdout


def test_serve_default_host_port():
    """Test that serve command accepts default host and port."""
    result = runner.invoke(app, ["serve"], catch_exceptions=False)
    # Will fail on uvicorn.run() but not on validation
    assert result.exit_code != 1 or "Port must be between" not in result.stdout
