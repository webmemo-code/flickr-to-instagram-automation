"""WP4 scaffold — notification consolidation.

Spec: docs/refactor/01-work-packages.md (WP4). Absorbs/extends
test_email_config.py. Uses the captured_emails fixture.

Goal state: email_notifier.py owns a single send_email(...) core;
CriticalFailureNotifier delegates to it; dead notification_system code
(fail_safe_state_operation, validate_state_access_or_fail) is deleted.
"""

import pytest

WP4 = pytest.mark.xfail(reason="WP4 not implemented", strict=False)


class TestSingleSendPath:
    @WP4
    def test_single_smtp_send_path(self):
        """Album-completion email, WordPress-API-failure email, and
        critical-state-failure alert ALL arrive via captured_emails patched at
        ONE send point. Grep-level assertion: exactly one construction of
        smtplib.SMTP in production code."""
        pytest.fail("scaffold: implement per docstring")

    @WP4
    def test_critical_failure_notifier_delegates_to_email_notifier(self):
        """CriticalFailureNotifier.send_critical_failure_alert routes through
        email_notifier's send core — it does not build its own SMTP
        connection or re-read SMTP env vars independently."""
        pytest.fail("scaffold: implement per docstring")

    @WP4
    def test_smtp_config_read_once(self):
        """SMTP host/port/credentials are read from the environment in exactly
        one place; all senders share that configuration (same defaulting rules
        as today — see test_email_config.py issue #171 regressions)."""
        pytest.fail("scaffold: implement per docstring")


class TestContentUnchanged:
    @WP4
    def test_completion_email_content_unchanged(self):
        """REGRESSION: subject and text/HTML bodies of the album-completion
        email match a snapshot captured from the CURRENT builder output before
        the consolidation. Capture the snapshot first, then refactor."""
        pytest.fail("scaffold: implement per docstring")
