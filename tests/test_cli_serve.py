"""Tests for the CLI serve command."""
import pytest
from typer.testing import CliRunner
from factory.cli import app


runner = CliRunner()


def test_serve_invalid_port_negative():
    """Test that negative ports are rejected."""
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_invalid_port_too_large():
    """Test that ports > 65535 are rejected."""
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_valid_port_zero():
    """Test that port 0 is accepted (auto-assign)."""
    # We don't actually start the server in the test, just verify it validates correctly
    # This would need a more sophisticated mock to test fully, but we check that
    # it doesn't fail validation
    result = runner.invoke(app, ["serve", "--port", "0"], catch_exceptions=False)
    # The command will fail to start the server in test environment, but port validation passes
    assert "Port must be between 0 and 65535" not in result.output


def test_serve_valid_port_max():
    """Test that port 65535 is accepted."""
    result = runner.invoke(app, ["serve", "--port", "65535"], catch_exceptions=False)
    # The command will fail to start the server in test environment, but port validation passes
    assert "Port must be between 0 and 65535" not in result.output


def test_serve_custom_host_and_port():
    """Test that custom host and port parameters are accepted."""
    result = runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "5000"], catch_exceptions=False)
    # The command will fail to start the server in test environment, but parameters are accepted
    assert "Port must be between 0 and 65535" not in result.output
