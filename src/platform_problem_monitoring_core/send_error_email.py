#!/usr/bin/env python3
"""Send error email notification."""

import argparse
import smtplib
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from platform_problem_monitoring_core.utils import logger


def send_error_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    sender: str,
    receiver: str,
    subject: str,
    error_message: str,
    step_name: str,
    stack_trace: Optional[str] = None,
) -> None:
    """
    Send an error notification email.
    
    Args:
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_user: SMTP username
        smtp_pass: SMTP password
        sender: Sender email address
        receiver: Receiver email address
        subject: Email subject
        error_message: Error message
        step_name: Name of the step where the error occurred
        stack_trace: Stack trace of the error (optional)
    
    Raises:
        Exception: If sending the email fails
    """
    logger.info(f"Sending error email to {receiver}")
    
    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    
    # Create HTML version
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #d9534f; }}
            .error-details {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
            .stack-trace {{ background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 15px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Platform Problem Monitoring Error</h1>
            <div class="error-details">
                <p><strong>Error occurred in step:</strong> {step_name}</p>
                <p><strong>Error message:</strong> {error_message}</p>
            </div>
            
            {f'<h2>Stack Trace</h2><div class="stack-trace">{stack_trace}</div>' if stack_trace else ''}
            
            <p>Please check the system logs for more details.</p>
        </div>
    </body>
    </html>
    """
    
    # Create plaintext version
    text = f"""
    Platform Problem Monitoring Error
    ================================
    
    Error occurred in step: {step_name}
    Error message: {error_message}
    
    {f'Stack Trace:\n\n{stack_trace}' if stack_trace else ''}
    
    Please check the system logs for more details.
    """
    
    # Attach parts
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    
    # Send email
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        logger.info("Error email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send error email: {str(e)}")
        raise


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Send error email notification")
    parser.add_argument("--smtp-host", required=True, help="SMTP server hostname")
    parser.add_argument("--smtp-port", type=int, required=True, help="SMTP server port")
    parser.add_argument("--smtp-user", required=True, help="SMTP username")
    parser.add_argument("--smtp-pass", required=True, help="SMTP password")
    parser.add_argument("--sender", required=True, help="Sender email address")
    parser.add_argument("--receiver", required=True, help="Receiver email address")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--error-message", required=True, help="Error message")
    parser.add_argument("--step-name", required=True, help="Name of the step where the error occurred")
    parser.add_argument("--stack-trace", help="Stack trace of the error")
    
    args = parser.parse_args()
    
    try:
        send_error_email(
            args.smtp_host,
            args.smtp_port,
            args.smtp_user,
            args.smtp_pass,
            args.sender,
            args.receiver,
            args.subject,
            args.error_message,
            args.step_name,
            args.stack_trace,
        )
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
