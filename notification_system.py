"""
Critical failure notification system for Flickr to Instagram automation.

This module provides fail-safe notifications when state management fails,
preventing wrong photos from being posted due to state tracking errors.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
import json

from email_notifier import send_email, _smtp_config


class CriticalFailureNotifier:
    """Handles critical failure notifications to prevent wrong photo posting."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # GitHub Actions notification (fallback)
        self.github_run_id = os.getenv('GITHUB_RUN_ID')
        self.github_repository = os.getenv('GITHUB_REPOSITORY')

    @property
    def smtp_server(self) -> str:
        """SMTP host, resolved via email_notifier's single config-read point."""
        return _smtp_config()['host']

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
        """Send email alert via the shared send_email() core.

        Delegates to email_notifier.send_email — CriticalFailureNotifier does
        not build its own SMTP connection or re-read SMTP env vars.
        """
        try:
            sent = send_email(subject, body)
            if sent:
                self.logger.info("Critical failure email sent")
            else:
                self.logger.warning(
                    "Email notification not configured or failed - "
                    "using GitHub Actions annotations only"
                )
            return sent
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False


class CriticalStateFailure(Exception):
    """Exception raised when state management is compromised and automation must stop."""
    pass


# Global notifier instance
notifier = CriticalFailureNotifier()