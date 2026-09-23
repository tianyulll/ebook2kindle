from __future__ import annotations

import mimetypes
import smtplib
import ssl
import time
from dataclasses import dataclass, replace
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable


class TlsMode(str, Enum):
    STARTTLS = "starttls"
    IMPLICIT_TLS = "implicit_tls"


class DeliveryStatus(str, Enum):
    SUBMITTED = "submitted"
    FAILED = "failed"


class DeliveryErrorKind(str, Enum):
    CONFIGURATION = "configuration"
    ATTACHMENT = "attachment"
    AUTHENTICATION = "authentication"
    TLS = "tls"
    CONNECTION = "connection"
    RECIPIENT = "recipient"
    SERVER = "server"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DeliveryConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    to_addr: str
    tls_mode: TlsMode | str = TlsMode.STARTTLS
    timeout_seconds: float = 30.0
    max_retries: int = 1
    max_attachment_bytes: int | None = None
    allowed_extensions: tuple[str, ...] = (".epub",)


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    file: Path
    status: DeliveryStatus
    attempts: int
    message_id: str | None = None
    error_kind: DeliveryErrorKind | None = None
    error_message: str | None = None
    smtp_code: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is DeliveryStatus.SUBMITTED


class EmailSendError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        kind: DeliveryErrorKind = DeliveryErrorKind.UNKNOWN,
        retryable: bool = False,
        smtp_code: int | None = None,
        file: Path | None = None,
    ):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.smtp_code = smtp_code
        self.file = file


class DeliveryValidationError(EmailSendError):
    pass


class DeliveryBatchError(EmailSendError):
    def __init__(self, results: list[DeliveryResult]):
        failures = [result for result in results if not result.succeeded]
        first = failures[0] if failures else None
        message = first.error_message if first and first.error_message else "Delivery failed."
        super().__init__(
            message,
            kind=first.error_kind if first and first.error_kind else DeliveryErrorKind.UNKNOWN,
            smtp_code=first.smtp_code if first else None,
            file=first.file if first else None,
        )
        self.results = results


def _validated_address(value: str, field_name: str) -> str:
    value = (value or "").strip()
    if not value or "\r" in value or "\n" in value:
        raise DeliveryValidationError(
            f"{field_name} is missing or invalid.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )
    try:
        address = Address(addr_spec=value)
    except (TypeError, ValueError) as exc:
        raise DeliveryValidationError(
            f"{field_name} is not a valid email address.",
            kind=DeliveryErrorKind.CONFIGURATION,
        ) from exc
    if not address.username or not address.domain:
        raise DeliveryValidationError(
            f"{field_name} is not a valid email address.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )
    return address.addr_spec


def validate_delivery_config(config: DeliveryConfig) -> DeliveryConfig:
    host = (config.smtp_host or "").strip()
    if not host or any(character.isspace() for character in host):
        raise DeliveryValidationError(
            "SMTP host is missing or invalid.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )

    try:
        port = int(config.smtp_port)
    except (TypeError, ValueError) as exc:
        raise DeliveryValidationError(
            "SMTP port must be a number.",
            kind=DeliveryErrorKind.CONFIGURATION,
        ) from exc
    if not 1 <= port <= 65535:
        raise DeliveryValidationError(
            "SMTP port must be between 1 and 65535.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )

    try:
        tls_mode = TlsMode(config.tls_mode)
    except (TypeError, ValueError) as exc:
        raise DeliveryValidationError(
            "Choose STARTTLS or implicit TLS for the SMTP connection.",
            kind=DeliveryErrorKind.CONFIGURATION,
        ) from exc

    if not config.smtp_password:
        raise DeliveryValidationError(
            "Sender password is empty. Re-enter it in Settings.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )
    if config.timeout_seconds <= 0:
        raise DeliveryValidationError(
            "SMTP timeout must be greater than zero.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )
    if not 0 <= config.max_retries <= 3:
        raise DeliveryValidationError(
            "SMTP retries must be between zero and three.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )
    if config.max_attachment_bytes is not None and config.max_attachment_bytes <= 0:
        raise DeliveryValidationError(
            "The attachment-size limit must be greater than zero.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )

    extensions = tuple(
        extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        for extension in config.allowed_extensions
    )
    if not extensions:
        raise DeliveryValidationError(
            "At least one attachment type must be allowed.",
            kind=DeliveryErrorKind.CONFIGURATION,
        )

    return replace(
        config,
        smtp_host=host,
        smtp_port=port,
        smtp_user=_validated_address(config.smtp_user, "Sender email"),
        to_addr=_validated_address(config.to_addr, "Kindle email"),
        tls_mode=tls_mode,
        allowed_extensions=extensions,
    )


def validate_attachments(
    files: Iterable[str | Path],
    config: DeliveryConfig,
) -> list[Path]:
    paths = [Path(file).expanduser().resolve() for file in files]
    if not paths:
        raise DeliveryValidationError(
            "Choose at least one book to send.",
            kind=DeliveryErrorKind.ATTACHMENT,
        )

    for path in paths:
        if not path.exists():
            raise DeliveryValidationError(
                f"Attachment not found: {path.name}",
                kind=DeliveryErrorKind.ATTACHMENT,
                file=path,
            )
        if not path.is_file():
            raise DeliveryValidationError(
                f"Attachment is not a file: {path.name}",
                kind=DeliveryErrorKind.ATTACHMENT,
                file=path,
            )
        if path.suffix.lower() not in config.allowed_extensions:
            allowed = ", ".join(config.allowed_extensions)
            raise DeliveryValidationError(
                f"Unsupported attachment type for {path.name}. Allowed: {allowed}.",
                kind=DeliveryErrorKind.ATTACHMENT,
                file=path,
            )
        try:
            size = path.stat().st_size
            with path.open("rb") as attachment:
                attachment.read(1)
        except OSError as exc:
            raise DeliveryValidationError(
                f"Attachment cannot be read: {path.name}",
                kind=DeliveryErrorKind.ATTACHMENT,
                file=path,
            ) from exc
        if size <= 0:
            raise DeliveryValidationError(
                f"Attachment is empty: {path.name}",
                kind=DeliveryErrorKind.ATTACHMENT,
                file=path,
            )
        if config.max_attachment_bytes is not None and size > config.max_attachment_bytes:
            raise DeliveryValidationError(
                f"Attachment exceeds the configured size limit: {path.name}",
                kind=DeliveryErrorKind.ATTACHMENT,
                file=path,
            )
    return paths


def _build_message(
    config: DeliveryConfig,
    file: Path,
    subject: str,
    body: str,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = config.smtp_user
    message["To"] = config.to_addr
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message_id = make_msgid(domain=config.smtp_user.rsplit("@", 1)[1])
    message["Message-ID"] = message_id
    message.set_content(body)

    content_type, encoding = mimetypes.guess_type(str(file))
    if file.suffix.lower() == ".epub":
        content_type = "application/epub+zip"
    elif content_type is None or encoding is not None:
        content_type = "application/octet-stream"
    maintype, subtype = content_type.split("/", 1)
    try:
        payload = file.read_bytes()
    except OSError as exc:
        raise EmailSendError(
            f"Attachment cannot be read: {file.name}",
            kind=DeliveryErrorKind.ATTACHMENT,
            file=file,
        ) from exc
    message.add_attachment(
        payload,
        maintype=maintype,
        subtype=subtype,
        filename=file.name,
    )
    return message


def _classify_smtp_error(exc: Exception, file: Path) -> EmailSendError:
    if isinstance(exc, EmailSendError):
        return exc
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return EmailSendError(
            "The mail provider rejected the sender email or app password.",
            kind=DeliveryErrorKind.AUTHENTICATION,
            smtp_code=exc.smtp_code,
            file=file,
        )
    if isinstance(exc, (ssl.SSLError, smtplib.SMTPNotSupportedError)):
        return EmailSendError(
            "A secure connection could not be established with the mail provider.",
            kind=DeliveryErrorKind.TLS,
            file=file,
        )
    if isinstance(exc, (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused)):
        return EmailSendError(
            "The mail provider rejected the sender or Kindle destination address.",
            kind=DeliveryErrorKind.RECIPIENT,
            smtp_code=getattr(exc, "smtp_code", None),
            file=file,
        )
    if isinstance(
        exc,
        (
            TimeoutError,
            ConnectionError,
            smtplib.SMTPConnectError,
            smtplib.SMTPServerDisconnected,
        ),
    ):
        return EmailSendError(
            "The connection to the mail provider was interrupted.",
            kind=DeliveryErrorKind.CONNECTION,
            retryable=True,
            smtp_code=getattr(exc, "smtp_code", None),
            file=file,
        )
    if isinstance(exc, smtplib.SMTPResponseException):
        code = int(exc.smtp_code)
        return EmailSendError(
            "The mail provider rejected the message.",
            kind=DeliveryErrorKind.SERVER,
            retryable=400 <= code < 500,
            smtp_code=code,
            file=file,
        )
    if isinstance(exc, OSError):
        return EmailSendError(
            "The mail provider could not be reached.",
            kind=DeliveryErrorKind.CONNECTION,
            retryable=True,
            file=file,
        )
    if isinstance(exc, smtplib.SMTPException):
        return EmailSendError(
            "The mail provider could not submit the message.",
            kind=DeliveryErrorKind.SERVER,
            file=file,
        )
    return EmailSendError(
        "An unexpected delivery error occurred.",
        kind=DeliveryErrorKind.UNKNOWN,
        file=file,
    )


def _submit_message(config: DeliveryConfig, message: EmailMessage, file: Path) -> None:
    context = ssl.create_default_context()
    submission_started = False
    submission_accepted = False
    try:
        if config.tls_mode is TlsMode.IMPLICIT_TLS:
            client = smtplib.SMTP_SSL(
                config.smtp_host,
                config.smtp_port,
                timeout=config.timeout_seconds,
                context=context,
            )
        else:
            client = smtplib.SMTP(
                config.smtp_host,
                config.smtp_port,
                timeout=config.timeout_seconds,
            )

        with client as server:
            server.ehlo()
            if config.tls_mode is TlsMode.STARTTLS:
                server.starttls(context=context)
                server.ehlo()
            server.login(config.smtp_user, config.smtp_password)
            submission_started = True
            refused = server.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
            submission_accepted = True
    except Exception as exc:
        # A successful DATA response is authoritative. QUIT/cleanup failures
        # cannot undo acceptance and must never cause a second submission.
        if submission_accepted:
            return
        error = _classify_smtp_error(exc, file)
        if submission_started and error.kind is DeliveryErrorKind.CONNECTION:
            error = EmailSendError(
                "The connection closed during submission, so delivery status is unknown. "
                "Automatic retry was stopped to avoid a duplicate.",
                kind=DeliveryErrorKind.CONNECTION,
                retryable=False,
                file=file,
            )
        raise error from exc


def deliver_files_via_smtp(
    config: DeliveryConfig,
    files: Iterable[str | Path],
    *,
    subject: str = "Send to Kindle",
    body: str = "Sent from ebook2kindle.",
    on_result: Callable[[DeliveryResult], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[DeliveryResult]:
    """Submit each book independently and return one structured result per file."""
    config = validate_delivery_config(config)
    paths = validate_attachments(files, config)
    results: list[DeliveryResult] = []

    for file in paths:
        result: DeliveryResult | None = None
        for attempt in range(1, config.max_retries + 2):
            try:
                message = _build_message(config, file, subject, body)
                _submit_message(config, message, file)
                result = DeliveryResult(
                    file=file,
                    status=DeliveryStatus.SUBMITTED,
                    attempts=attempt,
                    message_id=message["Message-ID"],
                )
                break
            except Exception as exc:
                error = _classify_smtp_error(exc, file)
                if error.retryable and attempt <= config.max_retries:
                    sleep(min(2 ** (attempt - 1), 4))
                    continue
                result = DeliveryResult(
                    file=file,
                    status=DeliveryStatus.FAILED,
                    attempts=attempt,
                    error_kind=error.kind,
                    error_message=str(error),
                    smtp_code=error.smtp_code,
                )
                break

        if result is None:
            result = DeliveryResult(
                file=file,
                status=DeliveryStatus.FAILED,
                attempts=0,
                error_kind=DeliveryErrorKind.UNKNOWN,
                error_message="An unexpected delivery error occurred.",
            )
        results.append(result)
        if on_result is not None:
            on_result(result)

    return results


def send_files_via_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    to_addr: str,
    files: Iterable[str | Path],
    subject: str = "Send to Kindle",
    body: str = "Sent from ebook2kindle.",
    use_starttls: bool = True,
) -> list[DeliveryResult]:
    """Compatibility wrapper for callers using the original function signature."""
    config = DeliveryConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        to_addr=to_addr,
        tls_mode=TlsMode.STARTTLS if use_starttls else TlsMode.IMPLICIT_TLS,
    )
    results = deliver_files_via_smtp(config, files, subject=subject, body=body)
    if any(not result.succeeded for result in results):
        raise DeliveryBatchError(results)
    return results
