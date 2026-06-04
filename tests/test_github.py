import pytest

from factory.github import get_token


def test_get_token_prefers_command_over_static(monkeypatch):
    monkeypatch.setenv("FACTORY_GITHUB_TOKEN", "static-token")
    monkeypatch.setenv("FACTORY_GITHUB_TOKEN_CMD", "printf 'fresh-token\\n'")
    assert get_token() == "fresh-token"


def test_get_token_falls_back_to_static(monkeypatch):
    monkeypatch.delenv("FACTORY_GITHUB_TOKEN_CMD", raising=False)
    monkeypatch.setenv("FACTORY_GITHUB_TOKEN", "static-token")
    assert get_token() == "static-token"


def test_get_token_raises_without_any_source(monkeypatch):
    monkeypatch.delenv("FACTORY_GITHUB_TOKEN_CMD", raising=False)
    monkeypatch.delenv("FACTORY_GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="FACTORY_GITHUB_TOKEN"):
        get_token()


@pytest.mark.parametrize("cmd", ["exit 3", "true"])  # non-zero exit, and empty output
def test_get_token_raises_on_bad_command(monkeypatch, cmd):
    monkeypatch.setenv("FACTORY_GITHUB_TOKEN", "static-token")
    monkeypatch.setenv("FACTORY_GITHUB_TOKEN_CMD", cmd)
    with pytest.raises(RuntimeError, match="FACTORY_GITHUB_TOKEN_CMD"):
        get_token()
