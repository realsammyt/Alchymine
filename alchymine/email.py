"""Email delivery service for Alchymine.

Supports Resend as the email provider. Gracefully degrades to logging
when no API key is configured (useful for local development).
"""

from __future__ import annotations

import logging

import resend

from alchymine.config import get_settings

logger = logging.getLogger(__name__)


async def send_password_reset_email(to: str, reset_token: str) -> bool:
    """Send a password-reset email to *to* containing a link with *reset_token*.

    Returns ``True`` on successful delivery, ``False`` otherwise.
    Never raises — failures are logged so the calling endpoint stays fast.
    """
    settings = get_settings()
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY not set — skipping email delivery for %s",
            to,
        )
        return False

    try:
        resend.api_key = settings.resend_api_key

        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to],
                "subject": "Reset Your Alchymine Password",
                "html": (
                    "<div style='font-family: sans-serif; max-width: 480px; margin: 0 auto;'>"
                    "<h2 style='color: #1a1a2e;'>Alchymine</h2>"
                    "<p>You requested a password reset. Click the link below to choose a new password:</p>"
                    f"<p><a href='{reset_url}' style='display: inline-block; padding: 12px 24px; "
                    "background: #1a1a2e; color: #ffffff; text-decoration: none; border-radius: 6px;'>"
                    "Reset Password</a></p>"
                    "<p style='color: #666; font-size: 14px;'>This link expires in 60 minutes. "
                    "If you didn't request this, you can safely ignore this email.</p>"
                    "</div>"
                ),
            }
        )
        logger.info("Password reset email sent to %s", to)
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", to)
        return False
