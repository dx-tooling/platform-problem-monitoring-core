#!/usr/bin/env python3
"""Send email report."""

import argparse
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from platform_problem_monitoring_core.utils import logger


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
    
    # Read the email bodies
    with open(html_file, "r") as f:
        html_body = f.read()
    
    with open(text_file, "r") as f:
        text_body = f.read()
    
    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    
    # Attach parts
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    # Placeholder implementation
    # In a real implementation, we would send the email
    # For now, we'll just log that we would send it
    logger.info("Would send email with the following content:")
    logger.info(f"Subject: {subject}")
    logger.info(f"From: {sender}")
    logger.info(f"To: {receiver}")
    logger.info(f"Text body length: {len(text_body)} characters")
    logger.info(f"HTML body length: {len(html_body)} characters")
    
    # Uncomment to actually send the email
    # server = smtplib.SMTP(smtp_host, smtp_port)
    # server.starttls()
    # server.login(smtp_user, smtp_pass)
    # server.sendmail(sender, receiver, msg.as_string())
    # server.quit()
    
    logger.info("Email report sent successfully")


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
