"""Email delivery service for Alchymine.

Supports Resend as the email provider. Gracefully degrades to logging
when no API key is configured (useful for local development).
"""

from __future__ import annotations

import logging
from datetime import datetime

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


async def send_feedback_notification_email(
    *,
    category: str,
    message: str,
    email: str | None,
    entry_id: int,
) -> bool:
    """Send a feedback notification email to the admin team.

    Called after a user submits feedback via ``POST /api/v1/feedback``.
    Returns ``True`` on successful delivery, ``False`` otherwise.
    Never raises — failures are logged so the calling endpoint stays fast.
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY not set — skipping feedback notification for entry id=%s",
            entry_id,
        )
        return False

    admin_panel_url = f"{settings.frontend_url}/admin/feedback"
    sender_line = (
        f"<p><strong>From:</strong> {email}</p>"
        if email
        else "<p><strong>From:</strong> <em>anonymous</em></p>"
    )

    try:
        resend.api_key = settings.resend_api_key

        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [settings.email_from],
                "subject": f"[Alchymine Feedback] New {category} submission (#{entry_id})",
                "html": (
                    "<div style='font-family: sans-serif; max-width: 600px; margin: 0 auto;'>"
                    "<h2 style='color: #1a1a2e;'>New Feedback Received</h2>"
                    f"<p><strong>Category:</strong> {category}</p>"
                    f"{sender_line}"
                    "<p><strong>Message:</strong></p>"
                    f"<blockquote style='border-left: 4px solid #1a1a2e; margin: 0; "
                    f"padding: 12px 16px; background: #f4f4f8; border-radius: 0 6px 6px 0;'>"
                    f"{message}"
                    "</blockquote>"
                    "<p style='margin-top: 24px;'>"
                    f"<a href='{admin_panel_url}' style='display: inline-block; "
                    "padding: 10px 20px; background: #1a1a2e; color: #ffffff; "
                    "text-decoration: none; border-radius: 6px;'>"
                    "View in Admin Panel</a></p>"
                    "<p style='color: #999; font-size: 12px; margin-top: 24px;'>"
                    f"Entry #{entry_id} — Alchymine Feedback System</p>"
                    "</div>"
                ),
            }
        )
        logger.info("Feedback notification sent to admin for entry id=%s", entry_id)
        return True
    except Exception:
        logger.exception("Failed to send feedback notification email for entry id=%s", entry_id)
        return False


async def send_invitation_email(
    to: str,
    invite_code: str,
    invited_by: str | None = None,
    expires_at: datetime | None = None,
) -> bool:
    """Send an invitation email to *to* containing a registration link with *invite_code*.

    *invited_by* is an optional display name or email of the admin who sent the invite.
    *expires_at* is an optional expiry datetime shown in the email body.
    Returns ``True`` on successful delivery, ``False`` otherwise.
    Never raises — failures are logged so the calling endpoint stays fast.
    """
    settings = get_settings()
    signup_url = f"{settings.frontend_url}/signup?invite={invite_code}"

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY not set — skipping invitation email delivery for %s",
            to,
        )
        return False

    invited_line = ""
    if invited_by:
        invited_line = f"<p style='color: #666; font-size: 14px;'>Invited by {invited_by}</p>"

    expiry_line = ""
    if expires_at is not None:
        formatted = expires_at.strftime("%B %d, %Y")
        expiry_line = (
            f"<p style='color: #666; font-size: 14px;'>This invitation expires on {formatted}.</p>"
        )

    try:
        resend.api_key = settings.resend_api_key

        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to],
                "subject": "You've Been Invited to Alchymine",
                "html": (
                    "<div style='font-family: sans-serif; max-width: 480px; margin: 0 auto;'>"
                    "<h2 style='color: #1a1a2e;'>You've been invited to Alchymine</h2>"
                    "<p>You've been invited to join Alchymine — your AI-powered "
                    "Personal Transformation Operating System.</p>"
                    f"{invited_line}"
                    f"<p><a href='{signup_url}' style='display: inline-block; padding: 12px 24px; "
                    "background: #1a1a2e; color: #ffffff; text-decoration: none; border-radius: 6px;'>"
                    "Sign Up Now</a></p>"
                    "<p style='margin-top: 24px;'>Or use this code when signing up:</p>"
                    "<div style='background: #f4f4f8; border-radius: 6px; padding: 16px; "
                    "margin: 8px 0; text-align: center;'>"
                    f"<code style='font-family: monospace; font-size: 18px; letter-spacing: 2px; "
                    f"color: #1a1a2e; font-weight: bold;'>{invite_code}</code>"
                    "</div>"
                    f"{expiry_line}"
                    "<p style='color: #666; font-size: 14px; margin-top: 16px;'>"
                    "If you weren't expecting this, you can safely ignore this email.</p>"
                    "</div>"
                ),
            }
        )
        logger.info("Invitation email sent to %s", to)
        return True
    except Exception:
        logger.exception("Failed to send invitation email to %s", to)
        return False
