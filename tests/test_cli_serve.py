"""Tests for the serve CLI command."""
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from factory.cli import app


runner = CliRunner()


def test_serve_port_validation_negative():
    """Test that negative ports are rejected."""
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_port_validation_too_high():
    """Test that ports > 65535 are rejected."""
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Port must be between 0 and 65535" in result.output


def test_serve_port_validation_valid_edge_cases():
    """Test that valid edge cases (0 and 65535) pass port validation."""
    # Mock uvicorn.run to prevent actual server startup
    with patch("factory.cli.uvicorn") as mock_uvicorn:
        mock_uvicorn.run = MagicMock()

        # Test port 0 (valid edge case)
        result = runner.invoke(app, ["serve", "--port", "0"], input="")
        # Port validation passes for 0, though server startup is mocked
        assert "Port must be between 0 and 65535" not in result.output

        # Test port 65535 (valid edge case)
        result = runner.invoke(app, ["serve", "--port", "65535"], input="")
        # Port validation passes for 65535
        assert "Port must be between 0 and 65535" not in result.output


def test_serve_accepts_host_option():
    """Test that the serve command accepts --host option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--host" in result.output
    assert "-h" in result.output


def test_serve_accepts_port_option():
    """Test that the serve command accepts --port option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--port" in result.output
    assert "-p" in result.output


def test_serve_missing_dependencies():
    """Test that helpful error is shown when fastapi/uvicorn are not installed."""
    with patch.dict("sys.modules", {"factory.server": None, "uvicorn": None}):
        result = runner.invoke(app, ["serve"])
        # Should fail with helpful error message about missing dependencies
        assert result.exit_code == 1


def test_serve_port_in_use_error():
    """Test that friendly error is shown when port is already in use."""
    with patch("factory.cli.uvicorn") as mock_uvicorn:
        mock_uvicorn.run.side_effect = OSError("Address already in use")

        result = runner.invoke(app, ["serve", "--port", "8000"])
        assert result.exit_code == 1
        assert "already in use" in result.output


def test_serve_permission_denied_error():
    """Test that friendly error is shown for permission denied on privileged ports."""
    with patch("factory.cli.uvicorn") as mock_uvicorn:
        mock_uvicorn.run.side_effect = OSError("Permission denied")

        result = runner.invoke(app, ["serve", "--port", "80"])
        assert result.exit_code == 1
        assert "Permission denied" in result.output or "privileges" in result.output


def test_serve_keyboard_interrupt():
    """Test that Ctrl+C is handled gracefully."""
    with patch("factory.cli.uvicorn") as mock_uvicorn:
        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        result = runner.invoke(app, ["serve", "--port", "8000"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()
