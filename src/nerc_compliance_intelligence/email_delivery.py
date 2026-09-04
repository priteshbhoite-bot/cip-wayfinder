"""Approval-gated SMTP delivery for an in-memory Word review package."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import make_msgid
import os
import re
import smtplib
import ssl
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from nerc_compliance_intelligence.package_export import WORD_MIME_TYPE


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmailDeliveryError(RuntimeError):
    """A safe, user-facing email configuration or delivery failure."""


class EmailDeliverySettings(BaseModel):
    """SMTP settings loaded from secret environment values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = Field(min_length=1)
    port: int = Field(default=587, ge=1, le=65535)
    username: str = Field(min_length=1)
    password: SecretStr
    from_address: str
    use_starttls: bool = True
    timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    @field_validator("from_address")
    @classmethod
    def validate_from_address(cls, value: str) -> str:
        return validate_email_address(value)


class WordEmailRequest(BaseModel):
    """The reviewed destination and attachment approved for one send."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    recipient: str
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2_000)
    attachment_name: str = Field(pattern=r"^[^\\/]+\.docx$")
    attachment_bytes: bytes = Field(min_length=1)

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, value: str) -> str:
        return validate_email_address(value)


class EmailDeliveryResult(BaseModel):
    """Non-secret delivery receipt safe to retain in browser session state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    masked_recipient: str
    attachment_name: str
    sent_at: datetime
    message_id: str


class EmailTransport(Protocol):
    """Transport seam that keeps tests offline."""

    def send(self, message: EmailMessage, settings: EmailDeliverySettings) -> None: ...


class SmtpEmailTransport:
    """Send one message through the explicitly configured SMTP service."""

    def send(self, message: EmailMessage, settings: EmailDeliverySettings) -> None:
        with smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout_seconds) as client:
            if settings.use_starttls:
                client.starttls(context=ssl.create_default_context())
            client.login(settings.username, settings.password.get_secret_value())
            client.send_message(message)


def validate_email_address(value: str) -> str:
    """Return a normalized, conservatively validated email address."""
    normalized = value.strip()
    if len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address, such as reviewer@example.com.")
    return normalized


def mask_email_address(value: str) -> str:
    """Mask the local part so session receipts expose less personal data."""
    local_part, domain = value.split("@", 1)
    visible = local_part[:1]
    return f"{visible}{'*' * max(2, len(local_part) - 1)}@{domain}"


def load_email_delivery_settings(environ: Mapping[str, str] | None = None) -> EmailDeliverySettings:
    """Load SMTP configuration without displaying or logging secret values."""
    source = os.environ if environ is None else environ
    required = (
        "NCI_SMTP_HOST",
        "NCI_SMTP_USERNAME",
        "NCI_SMTP_PASSWORD",
        "NCI_SMTP_FROM_ADDRESS",
    )
    if any(not source.get(name, "").strip() for name in required):
        raise EmailDeliveryError("Email delivery is not configured. Add the required NCI_SMTP settings to the ignored .env file.")
    try:
        return EmailDeliverySettings(
            host=source["NCI_SMTP_HOST"],
            port=int(source.get("NCI_SMTP_PORT", "587")),
            username=source["NCI_SMTP_USERNAME"],
            password=SecretStr(source["NCI_SMTP_PASSWORD"]),
            from_address=source["NCI_SMTP_FROM_ADDRESS"],
            use_starttls=source.get("NCI_SMTP_USE_STARTTLS", "true").strip().lower() not in {"0", "false", "no"},
            timeout_seconds=float(source.get("NCI_SMTP_TIMEOUT_SECONDS", "10")),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise EmailDeliveryError("Email delivery settings are invalid. Check the non-secret SMTP host, port, sender, and timeout values.") from error


def build_word_email_message(request: WordEmailRequest, settings: EmailDeliverySettings) -> EmailMessage:
    """Build the exact message that the user reviewed and approved."""
    message = EmailMessage()
    message["From"] = settings.from_address
    message["To"] = request.recipient
    message["Subject"] = request.subject
    message["Message-ID"] = make_msgid(domain=settings.from_address.split("@", 1)[1])
    message.set_content(request.body)
    main_type, sub_type = WORD_MIME_TYPE.split("/", 1)
    message.add_attachment(
        request.attachment_bytes,
        maintype=main_type,
        subtype=sub_type,
        filename=request.attachment_name,
    )
    return message


def send_word_package_email(
    request: WordEmailRequest,
    settings: EmailDeliverySettings,
    transport: EmailTransport | None = None,
) -> EmailDeliveryResult:
    """Send one already approved package and return only a safe receipt."""
    message = build_word_email_message(request, settings)
    try:
        (transport or SmtpEmailTransport()).send(message, settings)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("The email could not be sent. Nothing was saved; check the SMTP service and try again only if you still approve the destination.") from error
    return EmailDeliveryResult(
        masked_recipient=mask_email_address(request.recipient),
        attachment_name=request.attachment_name,
        sent_at=datetime.now(timezone.utc),
        message_id=str(message["Message-ID"]),
    )
