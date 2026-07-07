"""
Unit tests for email/SMTP configuration.

Focuses on how Config and CriticalFailureNotifier handle empty / missing SMTP
env vars, since GitHub Actions plumbing exports optional secrets as empty
strings ("") rather than leaving them unset — and an empty SMTP_HOST silently
breaks smtplib (skips connect(), then starttls() raises "please run connect()
first"). See PR #172 / issue #171.
"""
import os
from unittest.mock import patch

from config import Config
from notification_system import CriticalFailureNotifier


class TestSmtpHostDefault:
    def test_unset_smtp_host_uses_gmail_default(self, full_env):
        full_env()
        assert Config().smtp_host == 'smtp.gmail.com'

    def test_empty_smtp_host_uses_gmail_default(self, full_env):
        # Reproduces the issue #171 production state: GitHub Actions exports
        # `SMTP_HOST: ${{ secrets.SMTP_HOST || '' }}` as "" when the secret
        # is unset; without the fallback, smtplib.SMTP('', 587) hangs at starttls.
        full_env(SMTP_HOST='')
        assert Config().smtp_host == 'smtp.gmail.com'

    def test_explicit_smtp_host_used_verbatim(self, full_env):
        full_env(SMTP_HOST='smtp.example.com')
        assert Config().smtp_host == 'smtp.example.com'


class TestCriticalFailureNotifierSmtpServer:
    def test_unset_smtp_host_uses_gmail_default(self):
        with patch.dict(os.environ, {}, clear=True):
            notifier = CriticalFailureNotifier()
        assert notifier.smtp_server == 'smtp.gmail.com'

    def test_empty_smtp_host_uses_gmail_default(self):
        with patch.dict(os.environ, {'SMTP_HOST': ''}, clear=True):
            notifier = CriticalFailureNotifier()
        assert notifier.smtp_server == 'smtp.gmail.com'

    def test_empty_smtp_host_falls_through_to_smtp_server(self):
        with patch.dict(
            os.environ,
            {'SMTP_HOST': '', 'SMTP_SERVER': 'smtp.legacy.example.com'},
            clear=True,
        ):
            notifier = CriticalFailureNotifier()
        assert notifier.smtp_server == 'smtp.legacy.example.com'

    def test_explicit_smtp_host_takes_precedence(self):
        with patch.dict(
            os.environ,
            {'SMTP_HOST': 'smtp.primary.example.com', 'SMTP_SERVER': 'smtp.legacy.example.com'},
            clear=True,
        ):
            notifier = CriticalFailureNotifier()
        assert notifier.smtp_server == 'smtp.primary.example.com'
