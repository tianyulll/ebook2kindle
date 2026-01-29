from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


class EmailSendError(RuntimeError):
    pass


def send_files_via_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    to_addr: str,
    files: Iterable[str | Path],
    subject: str = "Send to Kindle",
    body: str = "Sent from ebook2kindle helper.",
    use_starttls: bool = True,
) -> None:
    files = [Path(f) for f in files]

    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise EmailSendError(f"Attachment(s) not found:\n" + "\n".join(missing))

    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    for f in files:
        ctype, encoding = mimetypes.guess_type(str(f))
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(
            f.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=f.name,
        )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            if use_starttls:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except smtplib.SMTPException as e:
        raise EmailSendError(f"SMTP send failed: {e}") from e
    except OSError as e:
        raise EmailSendError(f"Network/OS error: {e}") from e
