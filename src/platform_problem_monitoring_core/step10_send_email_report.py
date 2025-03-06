#!/usr/bin/env python3
"""Send email report."""

import argparse
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from platform_problem_monitoring_core.utils import logger


def wrap_long_lines(content: str, max_line_length: int = 998) -> str:
    """
    Wrap long lines in content to ensure they don't exceed max_line_length.

    Uses a more careful approach for HTML content.

    Args:
        content: The content to wrap
        max_line_length: Maximum length for each line (default 998, as per RFC)

    Returns:
        Content with lines wrapped to max_line_length
    """
    # Use a more conservative limit (default is still 998 per RFC, but we default to 998)
    result = []

    for line in content.splitlines():
        if len(line) <= max_line_length:
            # Line is already short enough
            result.append(line)
            continue

        # For HTML content, we need to be careful about where we insert line breaks
        # to avoid breaking HTML tags
        current_position = 0
        current_line = ""

        while current_position < len(line):
            # If adding the next character would exceed the limit
            if len(current_line) >= max_line_length - 1:
                result.append(current_line)
                current_line = ""

            # Handle HTML tags to avoid breaking them across lines
            if line[current_position] == "<":
                # Find the end of the tag
                tag_end = line.find(">", current_position)
                if tag_end == -1:  # No closing bracket found
                    tag_end = current_position + 1
                else:
                    tag_end += 1  # Include the '>' character

                # If adding the whole tag would exceed the line length and the current line
                # is not empty, start a new line
                tag_content = line[current_position:tag_end]
                if len(current_line) + len(tag_content) > max_line_length and current_line:
                    result.append(current_line)
                    current_line = tag_content
                    current_position = tag_end
                else:
                    # Add the tag to the current line
                    current_line += tag_content
                    current_position = tag_end
            else:
                # Regular character
                current_line += line[current_position]
                current_position += 1

        # Add any remaining content
        if current_line:
            result.append(current_line)

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

    try:
        # Read the email bodies
        with Path(html_file).open("r") as f:
            html_body = f.read()

        with Path(text_file).open("r") as f:
            text_body = f.read()

        # Wrap long lines to avoid SMTP line length limits (RFC 5322 says 998 characters max)
        # Use a more conservative 4000 characters to be safe with different SMTP servers
        # Some SMTP servers have a limit of 8192 characters, so staying well below that
        html_body = wrap_long_lines(html_body, max_line_length=4000)
        text_body = wrap_long_lines(text_body, max_line_length=4000)

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
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        logger.info("Email report sent successfully")
    except FileNotFoundError as e:
        logger.error(f"Email body file not found: {str(e)}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
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
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error sending email report: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
