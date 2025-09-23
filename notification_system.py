"""
Critical failure notification system for Flickr to Instagram automation.

This module provides fail-safe notifications when state management fails,
preventing wrong photos from being posted due to state tracking errors.
"""

import os
import smtplib
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Email imports with fallback
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    MimeText = None
    MimeMultipart = None


class CriticalFailureNotifier:
    """Handles critical failure notifications to prevent wrong photo posting."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Email configuration from environment variables (using existing config)
        self.smtp_server = os.getenv('SMTP_HOST', os.getenv('SMTP_SERVER', 'smtp.gmail.com'))

        # Handle SMTP_PORT safely - default to 587 if empty or invalid
        smtp_port_str = os.getenv('SMTP_PORT', '587').strip()
        try:
            self.smtp_port = int(smtp_port_str) if smtp_port_str else 587
        except ValueError:
            self.logger.debug("Invalid SMTP_PORT value, defaulting to 587")
            self.smtp_port = 587

        self.email_user = os.getenv('SMTP_USERNAME')
        self.email_password = os.getenv('SMTP_PASSWORD')
        self.notification_recipient = os.getenv('NOTIFICATION_EMAIL')

        # GitHub Actions notification (fallback)
        self.github_run_id = os.getenv('GITHUB_RUN_ID')
        self.github_repository = os.getenv('GITHUB_REPOSITORY')

    def send_critical_failure_alert(self, error_type: str, error_details: str,
                                  context: Dict[str, Any] = None) -> bool:
        """
        Send immediate alert for critical state management failures.

        Args:
            error_type: Type of critical error (e.g., "STATE_ACCESS_DENIED", "WRONG_PHOTO_RISK")
            error_details: Detailed error information
            context: Additional context about the failure

        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            timestamp = datetime.now().isoformat()

            # Create comprehensive error report
            report = {
                "timestamp": timestamp,
                "error_type": error_type,
                "error_details": error_details,
                "context": context or {},
                "github_run_id": self.github_run_id,
                "repository": self.github_repository,
                "severity": "CRITICAL - AUTOMATION STOPPED"
            }

            # Format email content
            subject = f"🚨 CRITICAL: Flickr Automation Failure - {error_type}"

            body = f"""
CRITICAL AUTOMATION FAILURE DETECTED

⚠️  AUTOMATION HAS BEEN STOPPED TO PREVENT WRONG PHOTO POSTING ⚠️

Error Type: {error_type}
Timestamp: {timestamp}
GitHub Run: {self.github_run_id}

ERROR DETAILS:
{error_details}

CONTEXT:
{json.dumps(context or {}, indent=2)}

IMMEDIATE ACTION REQUIRED:
1. Check GitHub repository permissions
2. Verify state management system integrity
3. Manual review required before resuming automation

GitHub Workflow: https://github.com/{self.github_repository}/actions/runs/{self.github_run_id}

This is an automated safety alert. The automation has been halted to prevent posting incorrect content.
"""

            # Try email notification first
            email_sent = self._send_email_alert(subject, body)

            # Log critical failure regardless of email success
            self.logger.critical(f"CRITICAL FAILURE: {error_type}")
            self.logger.critical(f"Details: {error_details}")
            self.logger.critical(f"Report: {json.dumps(report, indent=2)}")

            # GitHub Actions annotation (visible in workflow)
            if self.github_run_id:
                print(f"::error title=Critical Automation Failure::{error_type} - {error_details}")

            return email_sent

        except Exception as e:
            self.logger.error(f"Failed to send critical failure notification: {e}")
            # Even if notification fails, log the critical issue
            self.logger.critical(f"UNNOTIFIED CRITICAL FAILURE: {error_type} - {error_details}")
            return False

    def _send_email_alert(self, subject: str, body: str) -> bool:
        """Send email alert if email configuration is available."""
        try:
            if not EMAIL_AVAILABLE:
                self.logger.warning("Email libraries not available - using GitHub Actions annotations only")
                return False

            if not all([self.email_user, self.email_password, self.notification_recipient]):
                self.logger.warning("Email notification not configured - using GitHub Actions annotations only")
                return False

            # Create email message
            msg = MimeMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.notification_recipient
            msg['Subject'] = subject
            msg.attach(MimeText(body, 'plain'))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            self.logger.info(f"Critical failure email sent to {self.notification_recipient}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False

    def validate_state_access_or_fail(self, operation: str) -> None:
        """
        Validate that state management operations can proceed safely.
        If not, send alert and raise exception to stop automation.

        Args:
            operation: Description of the operation being attempted

        Raises:
            CriticalStateFailure: If state management is compromised
        """
        # This method should be called before any state-dependent operations
        # Implementation will be added based on specific state management needs
        pass


class CriticalStateFailure(Exception):
    """Exception raised when state management is compromised and automation must stop."""
    pass


# Global notifier instance
notifier = CriticalFailureNotifier()


def fail_safe_state_operation(operation_name: str, operation_func, *args, **kwargs):
    """
    Wrapper for state operations that must not fail silently.

    Args:
        operation_name: Name of the operation for error reporting
        operation_func: Function to execute
        *args, **kwargs: Arguments for the operation function

    Returns:
        Result of operation_func

    Raises:
        CriticalStateFailure: If operation fails and automation should stop
    """
    try:
        result = operation_func(*args, **kwargs)

        # Validate result is not a dangerous fallback
        if result is None and operation_name in ['get_last_posted_position', 'get_instagram_posts']:
            error_msg = f"State operation '{operation_name}' returned None - possible permission/access failure"
            notifier.send_critical_failure_alert(
                "STATE_ACCESS_FAILURE",
                error_msg,
                {"operation": operation_name, "args": str(args), "kwargs": str(kwargs)}
            )
            raise CriticalStateFailure(error_msg)

        return result

    except Exception as e:
        error_msg = f"Critical failure in state operation '{operation_name}': {str(e)}"
        notifier.send_critical_failure_alert(
            "STATE_OPERATION_FAILURE",
            error_msg,
            {"operation": operation_name, "exception": str(e), "args": str(args)}
        )
        raise CriticalStateFailure(error_msg) from e