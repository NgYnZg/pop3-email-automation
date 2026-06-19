"""Generate RFC 2822 .eml fixtures for parser tests."""

from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path


def write_fixture(name: str, message: EmailMessage) -> None:
    path = Path(__file__).with_name(name)
    path.write_bytes(message.as_bytes(policy=message.policy.clone(linesep="\r\n")))
    print(f"Wrote {path}")


def plain_only() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Sender Name <sender@example.com>"
    msg["To"] = "you@company.com"
    msg["Subject"] = "Plain text email"
    msg["Message-Id"] = "<plain-only-001@example.com>"
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content("This is the plain text body.")
    return msg


def html_only() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "HTML Sender <html-sender@example.com>"
    msg["To"] = "you@company.com"
    msg["Subject"] = "HTML email"
    msg["Message-Id"] = "<html-only-002@example.com>"
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content("<html><body><p>This is the <b>HTML</b> body.</p></body></html>", subtype="html")
    return msg


def mixed() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Mixed Sender <mixed@example.com>"
    msg["To"] = "you@company.com"
    msg["Cc"] = "cc@company.com"
    msg["Subject"] = "Mixed plain and HTML email"
    msg["Message-Id"] = "<mixed-003@example.com>"
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content("This is the plain text fallback.")
    msg.add_alternative("<html><body><p>This is the <b>HTML</b> body.</p></body></html>", subtype="html")
    return msg


def unicode_content() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Unicode Sender <unicode@example.com>"
    msg["To"] = "recipient@company.com"
    msg["Subject"] = "Unicode: 你好世界 🌍"
    msg["Message-Id"] = "<unicode-004@example.com>"
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content("こんにちは、世界！ Это тестовое сообщение.")
    return msg


def with_attachment() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Attachment Sender <attachment@example.com>"
    msg["To"] = "you@company.com"
    msg["Subject"] = "Email with attachment"
    msg["Message-Id"] = "<attachment-005@example.com>"
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content("Please find the invoice attached.")
    pdf_bytes = b"%PDF-1.4 fake pdf content for testing"
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="invoice.pdf",
    )
    return msg


def entities() -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Entity Sender <entities@example.com>"
    msg["To"] = "you@company.com"
    msg["Subject"] = "Email with HTML entities"
    msg["Message-Id"] = "<entities-006@example.com>"
    msg["Date"] = "Wed, 18 Jun 2026 14:28:00 +0000"
    msg.set_content(
        "Price: &pound;10 &amp; &euro;5\n"
        "Less than &lt; greater than &gt;\n"
        'Quote: &quot;text&quot;\n'
        "Space:&nbsp;after&#160;and&#x00A0;hex\n"
        "Regular text with no entities."
    )
    msg.add_alternative(
        "<html><body>"
        "<p>Price: &pound;10 &amp; &euro;5</p>"
        "<p>Less than &lt; greater than &gt;</p>"
        '<p>Quote: &quot;text&quot;</p>'
        "<p>Space:&nbsp;after&#160;and&#x00A0;hex</p>"
        "<p><b>Bold regular text with no entities.</b></p>"
        "</body></html>",
        subtype="html",
    )
    return msg


if __name__ == "__main__":
    write_fixture("plain_only.eml", plain_only())
    write_fixture("html_only.eml", html_only())
    write_fixture("mixed.eml", mixed())
    write_fixture("unicode.eml", unicode_content())
    write_fixture("with_attachment.eml", with_attachment())
    write_fixture("entities.eml", entities())
