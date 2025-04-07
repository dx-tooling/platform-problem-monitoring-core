#!/usr/bin/env python3
"""Send email report."""

import argparse
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from platform_problem_monitoring_core.utils import logger


def wrap_long_lines(content: str, max_line_length: int = 990) -> str:
    """
    Wrap long lines in content to ensure they don't exceed max_line_length.

    Uses a more careful approach for HTML content.

    Args:
        content: The content to wrap
        max_line_length: Maximum length for each line (default 990, as per RFC 5322)

    Returns:
        Content with lines wrapped to max_line_length
    """
    result = []

    for line in content.splitlines():
        if len(line) <= max_line_length:
            # Line is already short enough
            result.append(line)
            continue

        # For HTML content, we need to be careful about where we insert line breaks
        current_position = 0
        line_length = len(line)

        while current_position < line_length:
            # Determine where to cut the line
            end_pos = min(current_position + max_line_length, line_length)

            # If we're in the middle of an HTML tag, try to find the end of it
            if "<" in line[current_position:end_pos]:
                # We are potentially cutting through an HTML tag
                last_open_tag = line.rfind("<", current_position, end_pos)
                last_close_tag = line.rfind(">", current_position, end_pos)

                if last_open_tag > last_close_tag:
                    # We're inside a tag, cut before the tag starts
                    if last_open_tag > current_position:
                        end_pos = last_open_tag
                    else:
                        # The tag itself is very long, find the next closing bracket
                        next_close = line.find(">", current_position)
                        if next_close != -1 and next_close < current_position + max_line_length * 2:
                            # If closing tag is within reasonable distance, include the whole tag
                            end_pos = next_close + 1

            # Add the segment to result
            result.append(line[current_position:end_pos])
            current_position = end_pos

    return "\n".join(result)


def send_email_report(
    html_file: str,
    text_file: str,
    subject: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    sender: str,
    receiver: str,
    use_tls: bool = True,
) -> None:
    """
    Send email report.

    Args:
        html_file: Path to the HTML email body file
        text_file: Path to the plaintext email body file
        subject: Email subject
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_user: SMTP username
        smtp_pass: SMTP password
        sender: Sender email address
        receiver: Receiver email address
        use_tls: Whether to use TLS encryption (default: True)

    Raises:
        FileNotFoundError: If either email body file doesn't exist
        smtplib.SMTPException: If there's an error sending the email
        OSError: If there's an error reading the email body files
    """
    logger.info("Sending email report")
    logger.info(f"HTML file: {html_file}")
    logger.info(f"Text file: {text_file}")
    logger.info(f"Subject: {subject}")
    logger.info(f"SMTP host: {smtp_host}")
    logger.info(f"SMTP port: {smtp_port}")
    logger.info(f"SMTP user: {smtp_user}")
    logger.info(f"Sender: {sender}")
    logger.info(f"Receiver: {receiver}")
    logger.info(f"Use TLS: {use_tls}")

    # Check if files exist
    html_path = Path(html_file)
    text_path = Path(text_file)

    if not html_path.exists():
        error_msg = f"HTML email body file not found: {html_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    if not text_path.exists():
        error_msg = f"Text email body file not found: {text_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        # Read the email bodies
        with html_path.open("r") as f:
            html_body = f.read()

        with text_path.open("r") as f:
            text_body = f.read()

        # Wrap long lines to avoid SMTP line length limits (RFC 5322 says 998 characters max)
        # Use a more conservative 900 characters to be safe with different SMTP servers
        html_body = wrap_long_lines(html_body, max_line_length=900)
        text_body = wrap_long_lines(text_body, max_line_length=900)

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = receiver

        # Attach parts
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}")

        # Send the email
        server = None
        try:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)

            # Optional: Enable debug output
            # server.set_debuglevel(1)

            # Use TLS if requested
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)

            server.login(smtp_user, smtp_pass)
            server.sendmail(sender, receiver, msg.as_string())
            logger.info("Email report sent successfully")
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            raise
        finally:
            if server is not None:
                server.quit()
                logger.debug("SMTP connection closed")

    except (OSError, smtplib.SMTPException) as e:
        if isinstance(e, FileNotFoundError):
            logger.error(f"Email body file not found: {e}")
        elif isinstance(e, smtplib.SMTPException):
            logger.error(f"SMTP error: {e}")
        else:
            logger.error(f"Error sending email: {e}")
        raise


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Send email report")
    parser.add_argument("--html-file", required=True, help="Path to the HTML email body file")
    parser.add_argument("--text-file", required=True, help="Path to the plaintext email body file")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--smtp-host", required=True, help="SMTP server hostname")
    parser.add_argument("--smtp-port", type=int, required=True, help="SMTP server port")
    parser.add_argument("--smtp-user", required=True, help="SMTP username")
    parser.add_argument("--smtp-pass", required=True, help="SMTP password")
    parser.add_argument("--sender", required=True, help="Sender email address")
    parser.add_argument("--receiver", required=True, help="Receiver email address")
    parser.add_argument("--no-tls", action="store_true", help="Disable TLS encryption")

    args = parser.parse_args()

    try:
        send_email_report(
            args.html_file,
            args.text_file,
            args.subject,
            args.smtp_host,
            args.smtp_port,
            args.smtp_user,
            args.smtp_pass,
            args.sender,
            args.receiver,
            not args.no_tls,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error sending email report: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
