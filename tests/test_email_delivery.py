"""Offline tests for approval-gated Word package email delivery."""

from email.message import EmailMessage
import smtplib
import ssl

import pytest

from nerc_compliance_intelligence.email_delivery import (
    EmailDeliveryError,
    EmailDeliverySettings,
    SmtpEmailTransport,
    WordEmailRequest,
    build_word_email_message,
    load_email_delivery_settings,
    mask_email_address,
    send_word_package_email,
    validate_email_address,
)


class RecordingTransport:
    def __init__(self) -> None:
        self.message: EmailMessage | None = None

    def send(self, message: EmailMessage, settings: EmailDeliverySettings) -> None:
        self.message = message


class FailingTransport:
    def send(self, message: EmailMessage, settings: EmailDeliverySettings) -> None:
        raise smtplib.SMTPException("synthetic failure")


class RecordingSmtpClient:
    """Minimal SMTP stand-in that records the TLS context used by production transport."""

    last_instance: "RecordingSmtpClient | None" = None

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.tls_context: ssl.SSLContext | None = None
        self.logged_in = False
        self.message: EmailMessage | None = None
        type(self).last_instance = self

    def __enter__(self) -> "RecordingSmtpClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self, *, context: ssl.SSLContext) -> None:
        self.tls_context = context

    def login(self, username: str, password: str) -> None:
        self.logged_in = bool(username and password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def _settings() -> EmailDeliverySettings:
    return EmailDeliverySettings(
        host="smtp.example.com",
        username="mailer@example.com",
        password="not-a-real-secret",
        from_address="mailer@example.com",
    )


def _request() -> WordEmailRequest:
    return WordEmailRequest(
        recipient="reviewer@example.com",
        subject="Draft CIP review",
        body="Draft guidance for SME review only.",
        attachment_name="cip_wayfinder_cip_010_5_draft_review.docx",
        attachment_bytes=b"PK synthetic docx",
    )


def test_email_configuration_requires_secret_values() -> None:
    with pytest.raises(EmailDeliveryError, match="not configured"):
        load_email_delivery_settings({})


def test_email_configuration_loads_without_exposing_password() -> None:
    settings = load_email_delivery_settings(
        {
            "NCI_SMTP_HOST": "smtp.example.com",
            "NCI_SMTP_USERNAME": "mailer@example.com",
            "NCI_SMTP_PASSWORD": "secret-value",
            "NCI_SMTP_FROM_ADDRESS": "mailer@example.com",
        }
    )

    assert settings.password.get_secret_value() == "secret-value"
    assert "secret-value" not in repr(settings)


@pytest.mark.parametrize("value", ["missing-at.example.com", "a@b", "two words@example.com"])
def test_invalid_email_address_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="valid email address"):
        validate_email_address(value)


def test_word_message_contains_the_reviewed_destination_and_attachment() -> None:
    message = build_word_email_message(_request(), _settings())

    assert message["To"] == "reviewer@example.com"
    assert message["Subject"] == "Draft CIP review"
    attachment = list(message.iter_attachments())[0]
    assert attachment.get_filename() == "cip_wayfinder_cip_010_5_draft_review.docx"
    assert attachment.get_content_type() == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert attachment.get_payload(decode=True) == b"PK synthetic docx"


def test_send_uses_injected_transport_and_returns_masked_receipt() -> None:
    transport = RecordingTransport()

    result = send_word_package_email(_request(), _settings(), transport)

    assert transport.message is not None
    assert result.masked_recipient == "r*******@example.com"
    assert mask_email_address("a@example.com") == "a**@example.com"
    assert result.attachment_name.endswith(".docx")
    assert result.message_id.startswith("<")


def test_transport_failure_returns_safe_error() -> None:
    with pytest.raises(EmailDeliveryError, match="could not be sent"):
        send_word_package_email(_request(), _settings(), FailingTransport())


def test_smtp_transport_uses_certificate_verifying_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smtplib, "SMTP", RecordingSmtpClient)

    SmtpEmailTransport().send(build_word_email_message(_request(), _settings()), _settings())

    client = RecordingSmtpClient.last_instance
    assert client is not None
    assert client.tls_context is not None
    assert client.tls_context.verify_mode == ssl.CERT_REQUIRED
    assert client.tls_context.check_hostname is True
    assert client.logged_in is True
    assert client.message is not None
