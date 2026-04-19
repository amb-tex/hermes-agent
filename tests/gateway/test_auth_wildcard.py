"""Tests for fnmatch-style glob patterns in *_ALLOWED_USERS.

Covers the wildcard branch of ``GatewayRunner._is_user_authorized`` that
admits entries like ``*@example.com`` alongside exact matches.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.session import SessionSource


def _clear_auth_env(monkeypatch) -> None:
    for key in (
        "TELEGRAM_ALLOWED_USERS",
        "DISCORD_ALLOWED_USERS",
        "WHATSAPP_ALLOWED_USERS",
        "SLACK_ALLOWED_USERS",
        "SIGNAL_ALLOWED_USERS",
        "EMAIL_ALLOWED_USERS",
        "SMS_ALLOWED_USERS",
        "MATTERMOST_ALLOWED_USERS",
        "MATRIX_ALLOWED_USERS",
        "DINGTALK_ALLOWED_USERS",
        "FEISHU_ALLOWED_USERS",
        "WECOM_ALLOWED_USERS",
        "QQ_ALLOWED_USERS",
        "QQ_GROUP_ALLOWED_USERS",
        "GATEWAY_ALLOWED_USERS",
        "TELEGRAM_ALLOW_ALL_USERS",
        "DISCORD_ALLOW_ALL_USERS",
        "WHATSAPP_ALLOW_ALL_USERS",
        "SLACK_ALLOW_ALL_USERS",
        "SIGNAL_ALLOW_ALL_USERS",
        "EMAIL_ALLOW_ALL_USERS",
        "SMS_ALLOW_ALL_USERS",
        "MATTERMOST_ALLOW_ALL_USERS",
        "MATRIX_ALLOW_ALL_USERS",
        "DINGTALK_ALLOW_ALL_USERS",
        "FEISHU_ALLOW_ALL_USERS",
        "WECOM_ALLOW_ALL_USERS",
        "QQ_ALLOW_ALL_USERS",
        "GATEWAY_ALLOW_ALL_USERS",
    ):
        monkeypatch.delenv(key, raising=False)


def _make_runner(platform: Platform, config: GatewayConfig):
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = config
    runner.adapters = {platform: SimpleNamespace(send=AsyncMock())}
    runner.pairing_store = MagicMock()
    runner.pairing_store.is_approved.return_value = False
    runner.pairing_store._is_rate_limited.return_value = False
    return runner


def _email_source(user_id: str) -> SessionSource:
    return SessionSource(
        platform=Platform.EMAIL,
        user_id=user_id,
        chat_id=user_id,
        user_name="tester",
        chat_type="dm",
    )


def _email_runner() -> "GatewayRunner":  # noqa: F821 — typing for clarity only
    return _make_runner(
        Platform.EMAIL,
        GatewayConfig(platforms={Platform.EMAIL: PlatformConfig(enabled=True)}),
    )


def test_domain_glob_matches_address_in_that_domain(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("EMAIL_ALLOWED_USERS", "*@agents.example.com")
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("alice@agents.example.com")) is True


def test_domain_glob_rejects_address_in_other_domain(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("EMAIL_ALLOWED_USERS", "*@agents.example.com")
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("alice@other.example.com")) is False


def test_glob_matching_is_case_insensitive(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("EMAIL_ALLOWED_USERS", "*@Agents.Example.COM")
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("ALICE@agents.example.com")) is True


def test_exact_entry_alongside_glob_still_matches_exact(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv(
        "EMAIL_ALLOWED_USERS",
        "tom@example.com,*@agents.example.com",
    )
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("tom@example.com")) is True
    assert runner._is_user_authorized(_email_source("bot@agents.example.com")) is True
    assert runner._is_user_authorized(_email_source("mallory@elsewhere.net")) is False


def test_standalone_star_still_means_allow_all(monkeypatch):
    """Backward-compat regression — "*" by itself is allow-all, not a glob."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("EMAIL_ALLOWED_USERS", "*")
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("anyone@anywhere.example")) is True


def test_question_mark_glob_matches_single_character(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("EMAIL_ALLOWED_USERS", "user?@example.com")
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("user1@example.com")) is True
    assert runner._is_user_authorized(_email_source("userx@example.com")) is True
    assert runner._is_user_authorized(_email_source("user12@example.com")) is False


def test_global_allowlist_supports_globs(monkeypatch):
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("GATEWAY_ALLOWED_USERS", "*@agents.example.com")
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("alice@agents.example.com")) is True


def test_no_allowlists_configured_still_denies(monkeypatch):
    """Regression — empty allowlist + no allow-all flag → deny."""
    _clear_auth_env(monkeypatch)
    runner = _email_runner()

    assert runner._is_user_authorized(_email_source("alice@example.com")) is False


def test_exact_non_email_id_unaffected_by_wildcard_branch(monkeypatch):
    """Regression — exact Telegram numeric ID still matches without a glob."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "123456789")
    runner = _make_runner(
        Platform.TELEGRAM,
        GatewayConfig(
            platforms={Platform.TELEGRAM: PlatformConfig(enabled=True, token="t")}
        ),
    )
    source = SessionSource(
        platform=Platform.TELEGRAM,
        user_id="123456789",
        chat_id="123456789",
        user_name="tester",
        chat_type="dm",
    )

    assert runner._is_user_authorized(source) is True
