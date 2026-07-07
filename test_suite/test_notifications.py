"""WP4 — notification consolidation.

Spec: docs/refactor/01-work-packages.md (WP4). Absorbs/extends
test_email_config.py. Uses the captured_emails fixture.

Goal state: email_notifier.py owns a single send_email(...) core;
CriticalFailureNotifier delegates to it; dead notification_system code
(fail_safe_state_operation, validate_state_access_or_fail) is deleted.
"""

import inspect
import re
from datetime import datetime
from unittest.mock import patch

import pytest

import email_notifier
import notification_system
from config import Config
from email_notifier import EmailNotifier
from notification_system import CriticalFailureNotifier


class TestSingleSendPath:
    def test_single_smtp_send_path(self, full_env, captured_emails):
        """Album-completion email, WordPress-API-failure email, and
        critical-state-failure alert ALL arrive via captured_emails patched at
        ONE send point. Grep-level assertion: exactly one construction of
        smtplib.SMTP in production code."""
        full_env(
            SMTP_USERNAME='bot@example.com',
            SMTP_PASSWORD='pw',
            NOTIFICATION_EMAIL='manager@example.com',
        )
        config = Config()
        email_notifier_instance = EmailNotifier(config)
        critical_notifier = CriticalFailureNotifier()

        assert email_notifier_instance.send_completion_notification(5, 'Test Album') is True
        assert email_notifier_instance.send_api_failure_alert(
            'https://example.com', {'http_status': 500}, 'primary'
        ) is True
        assert critical_notifier.send_critical_failure_alert('TEST_ERROR', 'details') is True

        assert len(captured_emails) == 3

        # Grep-level assertion: exactly one `smtplib.SMTP(` construction across
        # the production modules that send email.
        production_sources = [
            inspect.getsource(email_notifier),
            inspect.getsource(notification_system),
        ]
        construction_count = sum(
            len(re.findall(r'smtplib\.SMTP\(', src)) for src in production_sources
        )
        assert construction_count == 1

    def test_critical_failure_notifier_delegates_to_email_notifier(self, full_env, captured_emails):
        """CriticalFailureNotifier.send_critical_failure_alert routes through
        email_notifier's send core — it does not build its own SMTP
        connection or re-read SMTP env vars independently."""
        full_env(
            SMTP_USERNAME='bot@example.com',
            SMTP_PASSWORD='pw',
            NOTIFICATION_EMAIL='manager@example.com',
        )
        with patch.object(notification_system, 'send_email', wraps=email_notifier.send_email) as mock_send:
            notifier = CriticalFailureNotifier()
            notifier.send_critical_failure_alert('TEST_ERROR', 'details')

        mock_send.assert_called_once()
        # notification_system no longer imports smtplib at all
        assert 'smtplib' not in inspect.getsource(notification_system)

    def test_smtp_config_read_once(self, full_env):
        """SMTP host/port/credentials are read from the environment in exactly
        one place; all senders share that configuration (same defaulting rules
        as today — see test_email_config.py issue #171 regressions)."""
        full_env(SMTP_HOST='', SMTP_SERVER='smtp.legacy.example.com')

        cfg = email_notifier._smtp_config()
        assert cfg['host'] == 'smtp.legacy.example.com'

        # CriticalFailureNotifier's smtp_server delegates to the same function
        notifier = CriticalFailureNotifier()
        assert notifier.smtp_server == cfg['host']

        # Only email_notifier.py defines an SMTP-config-reading function;
        # notification_system.py must not read SMTP_* env vars itself.
        notification_source = inspect.getsource(notification_system)
        assert "os.getenv('SMTP_" not in notification_source
        assert 'os.getenv("SMTP_' not in notification_source


class TestContentUnchanged:
    def test_completion_email_content_unchanged(self, full_env):
        """REGRESSION: subject and text/HTML bodies of the album-completion
        email match a snapshot captured from the CURRENT builder output before
        the consolidation. Capture the snapshot first, then refactor."""
        full_env(
            SMTP_USERNAME='bot@example.com',
            SMTP_PASSWORD='pw',
            NOTIFICATION_EMAIL='manager@example.com',
        )
        config = Config()
        notifier = EmailNotifier(config)

        with patch('email_notifier.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 7, 12, 0, 0)
            msg = notifier._create_completion_email(42, 'Test Album')

        assert msg['Subject'] == 'Album Complete: Test Album (42 photos published)'
        assert msg['From'] == 'bot@example.com'
        assert msg['To'] == 'manager@example.com'

        parts = {part.get_content_type(): part.get_payload() for part in msg.walk()
                  if part.get_content_type() in ('text/plain', 'text/html')}

        assert parts['text/plain'] == (
            "Album Publishing Complete!\n\n"
            "Album: Test Album\n"
            "Total Photos Published: 42\n"
            "Completion Date: 2026-07-07 12:00 UTC\n"
            f"Album URL: {config.album_url}\n\n"
            'All photos from the "Test Album" Flickr album have been successfully published to Instagram.\n\n'
            "Next Steps:\n"
            "1. Review the published posts on Instagram\n"
            "2. Configure the next Flickr album for automation\n"
            "3. Update the FLICKR_ALBUM_ID environment variable\n"
            "4. Update the album name in config.py if needed\n\n"
            "The automation system is ready for the next album configuration.\n\n"
            "---\n"
            "Flickr to Instagram Automation System\n"
            "Generated automatically on 2026-07-07 12:00 UTC\n"
        )

        html = parts['text/html']
        assert '<h1 style="margin: 0;">Album Publishing Complete!</h1>' in html
        assert '<td style="padding: 8px;">Test Album</td>' in html
        assert '<td style="padding: 8px;"><strong>42</strong></td>' in html
        assert '<td style="padding: 8px;">2026-07-07 12:00 UTC</td>' in html
        assert f'href="{config.album_url}"' in html


class TestNonAsciiPayloadDecoding:
    def test_emoji_body_decoded_not_base64(self, full_env):
        """REGRESSION: _send_email must decode transfer-encoded (base64/
        quoted-printable) payloads before handing them to send_email(). The
        API-failure templates contain emoji (🚨/✅/❌), which forces MIMEText
        to base64-encode the part — get_payload() without decode=True returns
        that raw encoded string, corrupting the delivered body if sent as-is.

        Asserts on the arguments send_email() actually receives (the
        production boundary the bug crossed), rather than re-parsing a
        reconstructed message, which has its own separate encoding step."""
        full_env(
            SMTP_USERNAME='bot@example.com',
            SMTP_PASSWORD='pw',
            NOTIFICATION_EMAIL='manager@example.com',
        )
        config = Config()
        notifier = EmailNotifier(config)

        with patch.object(email_notifier, 'send_email', return_value=True) as mock_send:
            notifier.send_api_failure_alert(
                'https://example.com', {'http_status': 500}, 'primary'
            )

        mock_send.assert_called_once()
        subject, text_body, html_body = mock_send.call_args[0]

        assert '🚨' in subject
        # A corrupted (still-encoded) body would be an opaque base64 blob,
        # not readable text containing the known template content.
        assert 'WordPress API Access Failure Alert' in text_body
        assert 'ACCOUNT: primary' in text_body
        # The HTML template's Yes/No cells use ✅/❌, forcing base64 transfer
        # encoding — this is the exact content that exposed the bug.
        assert '✅' in html_body or '❌' in html_body
        assert '<html>' in html_body
