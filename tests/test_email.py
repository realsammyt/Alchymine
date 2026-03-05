"""Unit tests for the email delivery module."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from alchymine.email import send_password_reset_email


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the lru_cache on get_settings so each test gets fresh settings."""
    from alchymine.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email()."""

    @pytest.mark.asyncio
    async def test_no_api_key_logs_warning_and_returns_false(self, caplog):
        """With an empty RESEND_API_KEY, the function should log a warning and return False."""
        with patch.dict(
            "os.environ",
            {"RESEND_API_KEY": "", "FRONTEND_URL": "http://localhost:3000"},
            clear=False,
        ):
            with caplog.at_level(logging.WARNING, logger="alchymine.email"):
                result = await send_password_reset_email("user@example.com", "tok123")

        assert result is False
        assert "RESEND_API_KEY not set" in caplog.text
        assert "http://localhost:3000/reset-password?token=tok123" in caplog.text

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """With a valid API key, the function should call resend.Emails.send and return True."""
        mock_send = MagicMock()
        with (
            patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_test_key123",
                    "EMAIL_FROM": "test@alchymine.app",
                    "FRONTEND_URL": "https://app.alchymine.app",
                },
                clear=False,
            ),
            patch.object(
                __import__("alchymine.email", fromlist=["resend"]).resend,
                "Emails",
            ) as mock_emails,
        ):
            mock_emails.send = mock_send
            result = await send_password_reset_email("user@example.com", "abc123")

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == ["user@example.com"]
        assert call_args["subject"] == "Reset Your Alchymine Password"
        assert "abc123" in call_args["html"]

    @pytest.mark.asyncio
    async def test_send_email_exception_returns_false(self, caplog):
        """If resend raises an exception, the function should return False and log."""
        with (
            patch.dict(
                "os.environ",
                {"RESEND_API_KEY": "re_test_key123"},
                clear=False,
            ),
            patch.object(
                __import__("alchymine.email", fromlist=["resend"]).resend,
                "Emails",
            ) as mock_emails,
        ):
            mock_emails.send.side_effect = RuntimeError("API down")

            with caplog.at_level(logging.ERROR, logger="alchymine.email"):
                result = await send_password_reset_email("user@example.com", "tok456")

        assert result is False
        assert "Failed to send password reset email" in caplog.text
