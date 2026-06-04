import pytest
from typer.testing import CliRunner
from factory.cli import app

runner = CliRunner()


def test_serve_with_valid_port():
    result = runner.invoke(app, ["serve", "--port", "8000", "--help"])
    assert result.exit_code == 0


def test_serve_with_negative_port():
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 1
    assert "Invalid port" in result.stdout


def test_serve_with_port_over_65535():
    result = runner.invoke(app, ["serve", "--port", "65536"])
    assert result.exit_code == 1
    assert "Invalid port" in result.stdout


def test_serve_with_port_zero():
    result = runner.invoke(app, ["serve", "--port", "0", "--help"])
    assert result.exit_code == 0


def test_serve_with_port_65535():
    result = runner.invoke(app, ["serve", "--port", "65535", "--help"])
    assert result.exit_code == 0


def test_serve_with_custom_host():
    result = runner.invoke(app, ["serve", "--host", "0.0.0.0", "--help"])
    assert result.exit_code == 0


def test_serve_default_port():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
