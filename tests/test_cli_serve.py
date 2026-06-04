import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from factory.cli import app

runner = CliRunner()


def test_serve_with_valid_port():
    """Test that serve command accepts valid port and calls uvicorn.run()"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve", "--port", "8000"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 8000
        assert call_kwargs["host"] == "127.0.0.1"


def test_serve_with_negative_port():
    """Test that serve command rejects negative port values"""
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Invalid port" in result.stdout


def test_serve_with_port_over_65535():
    """Test that serve command rejects ports above 65535"""
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Invalid port" in result.stdout


def test_serve_with_port_zero():
    """Test that port 0 (auto-assign) is accepted and uvicorn.run() is called"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve", "--port", "0"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 0


def test_serve_with_port_65535():
    """Test that port 65535 (max valid port) is accepted and uvicorn.run() is called"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve", "--port", "65535"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 65535


def test_serve_with_custom_host():
    """Test that serve command accepts custom host and calls uvicorn.run()"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve", "--host", "0.0.0.0"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"


def test_serve_default_port_and_host():
    """Test that serve command uses default port 8000 and host 127.0.0.1"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 8000
        assert call_kwargs["host"] == "127.0.0.1"


def test_serve_handles_address_in_use_error():
    """Test that serve command handles OSError when port is already in use"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        mock_run.side_effect = OSError("[Errno 48] Address already in use")
        result = runner.invoke(app, ["serve", "--port", "8000"])
        assert result.exit_code == 1
        assert "Cannot bind to" in result.stdout


def test_serve_handles_permission_denied_error():
    """Test that serve command handles OSError when permission is denied"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        mock_run.side_effect = OSError("Permission denied")
        result = runner.invoke(app, ["serve", "--port", "80"])
        assert result.exit_code == 1
        assert "Cannot bind to" in result.stdout


def test_serve_handles_network_error():
    """Test that serve command handles generic OSError network errors"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        mock_run.side_effect = OSError("Network is unreachable")
        result = runner.invoke(app, ["serve", "--port", "8000"])
        assert result.exit_code == 1
        assert "Network error" in result.stdout


def test_serve_handles_value_error():
    """Test that serve command handles ValueError for invalid configuration"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        mock_run.side_effect = ValueError("Invalid host/port combination")
        result = runner.invoke(app, ["serve", "--host", "invalid-host"])
        assert result.exit_code == 1
        assert "Invalid configuration" in result.stdout


def test_serve_handles_generic_exception():
    """Test that serve command handles unexpected exceptions gracefully"""
    with patch("factory.cli.uvicorn.run") as mock_run:
        mock_run.side_effect = RuntimeError("Unexpected server error")
        result = runner.invoke(app, ["serve", "--port", "8000"])
        assert result.exit_code == 1
        assert "Server startup failed" in result.stdout


def test_serve_with_missing_uvicorn():
    """Test that serve command provides helpful message when uvicorn is not installed"""
    with patch.dict("sys.modules", {"uvicorn": None}):
        with patch("factory.cli.uvicorn", side_effect=ImportError("No module named 'uvicorn'")):
            result = runner.invoke(app, ["serve"])
            assert result.exit_code == 1
            assert "uvicorn not installed" in result.stdout
