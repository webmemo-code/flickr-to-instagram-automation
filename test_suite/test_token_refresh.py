"""WP7 — token refresh automation (token_refresh.py).

Spec: docs/refactor/04-token-refresh-spec.md. Fixtures: graph_api,
captured_emails. ALL tests offline/mocked — no live Meta or gh calls.
"""
import logging
from unittest.mock import MagicMock, patch

import pytest


class TestRefreshCall:
    def test_refresh_success_returns_new_token_and_expiry(self, graph_api):
        """refresh_igaa_token(token) GETs
        graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token
        and returns RefreshResult(access_token=<new>, expires_in_seconds=...)
        parsed from the JSON payload."""
        from token_refresh import refresh_igaa_token

        graph_api.refresh_token_success(new_token='IGAA-new-token', expires_in=5183944)

        result = refresh_igaa_token('IGAA-old-token')

        assert result.access_token == 'IGAA-new-token'
        assert result.expires_in_seconds == 5183944

    def test_refresh_refuses_non_igaa_token(self):
        """An 'EAA...'-prefixed (or otherwise non-IGAA) token is refused with
        an actionable error pointing at the eaa-to-igaa-migration runbook, and
        ZERO HTTP calls are made — never fall back to a graph.facebook.com
        exchange."""
        from token_refresh import refresh_igaa_token, TokenRefreshError

        with patch('token_refresh.requests.get') as mock_get:
            with pytest.raises(TokenRefreshError, match='eaa-to-igaa-migration'):
                refresh_igaa_token('EAA-legacy-token')
            mock_get.assert_not_called()

    def test_refresh_refuses_empty_token(self):
        """An empty/missing token is refused the same way (not IGAA-prefixed)."""
        from token_refresh import refresh_igaa_token, TokenRefreshError

        with patch('token_refresh.requests.get') as mock_get:
            with pytest.raises(TokenRefreshError):
                refresh_igaa_token('')
            mock_get.assert_not_called()

    def test_expiry_threshold_logic(self, graph_api):
        """Refresh proceeds normally for an eligible token (>= 24h old, not
        expired) — this module has no client-side notion of token age (only
        its value), so eligibility is enforced entirely by the refresh
        endpoint. A rejection (simulating a too-young or otherwise ineligible
        token) surfaces as an ordinary TokenRefreshError via run_refresh's
        alert path rather than crashing the whole workflow — see
        TestFailureHandling for that behavior exercised end-to-end."""
        from token_refresh import refresh_igaa_token

        graph_api.refresh_token_success(new_token='IGAA-eligible', expires_in=5183944)
        result = refresh_igaa_token('IGAA-eligible-token')
        assert result.access_token == 'IGAA-eligible'


class TestFailureHandling:
    def test_refresh_http_error_sends_alert_and_exits_nonzero(self, graph_api, captured_emails, monkeypatch):
        """An HTTP error (or unexpected payload) from the refresh endpoint
        sends an alert email via the consolidated WP4 path (captured_emails)
        and the process exits non-zero so the workflow run is red."""
        from token_refresh import run_refresh

        monkeypatch.setenv('SMTP_USERNAME', 'bot@example.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'secret')
        monkeypatch.setenv('NOTIFICATION_EMAIL', 'ops@example.com')

        graph_api.refresh_token_failure()

        with pytest.raises(SystemExit) as exc_info:
            run_refresh('primary-account', 'IGAA-old-token')

        assert exc_info.value.code != 0
        assert len(captured_emails) == 1
        assert 'token' in captured_emails[0]['subject'].lower()

    def test_secret_writeback_failure_sends_alert_and_exits_nonzero(self, graph_api, captured_emails, monkeypatch):
        """If the refresh succeeds but `gh secret set` fails, that also
        alerts and exits non-zero (new token is live at Meta but GitHub
        still holds the old one — must be visibly red)."""
        from token_refresh import run_refresh

        monkeypatch.setenv('SMTP_USERNAME', 'bot@example.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'secret')
        monkeypatch.setenv('NOTIFICATION_EMAIL', 'ops@example.com')

        graph_api.refresh_token_success(new_token='IGAA-new-token', expires_in=5183944)

        fake_result = MagicMock(returncode=1, stderr='gh: authentication failed')
        with patch('token_refresh.subprocess.run', return_value=fake_result):
            with pytest.raises(SystemExit) as exc_info:
                run_refresh('primary-account', 'IGAA-old-token')

        assert exc_info.value.code != 0
        assert len(captured_emails) == 1


class TestSecretWriteback:
    def test_secret_update_invokes_gh_secret_set_env_scoped(self):
        """update_github_secret runs
        `gh secret set <NAME> --env <environment> --body -` with the token
        delivered via STDIN — the token never appears in argv. Subprocess is
        mocked; assert on command list and stdin payload."""
        from token_refresh import update_github_secret

        fake_result = MagicMock(returncode=0, stderr='')
        with patch('token_refresh.subprocess.run', return_value=fake_result) as mock_run:
            update_github_secret('INSTAGRAM_ACCESS_TOKEN', 'primary-account', 'IGAA-secret-value')

        args, kwargs = mock_run.call_args
        command = args[0]
        assert command == ['gh', 'secret', 'set', 'INSTAGRAM_ACCESS_TOKEN',
                            '--env', 'primary-account', '--body', '-']
        assert kwargs['input'] == 'IGAA-secret-value'
        # Token must not appear anywhere in the argv command list.
        assert not any('IGAA-secret-value' in str(part) for part in command)

    def test_secret_update_raises_on_gh_failure(self):
        """A non-zero gh exit raises TokenRefreshError (caller alerts)."""
        from token_refresh import update_github_secret, TokenRefreshError

        fake_result = MagicMock(returncode=1, stderr='gh: environment not found')
        with patch('token_refresh.subprocess.run', return_value=fake_result):
            with pytest.raises(TokenRefreshError, match='environment not found'):
                update_github_secret('INSTAGRAM_ACCESS_TOKEN', 'bogus-env', 'IGAA-value')


class TestNoTokenLeaks:
    def test_token_value_never_logged(self, graph_api, caplog):
        """With logging captured at DEBUG across a full refresh+writeback run
        (success and failure variants), no log record contains the token
        value. Prefix/length logging (e.g. 'IGAA…(len=183)') is acceptable."""
        from token_refresh import refresh_igaa_token, update_github_secret

        old_token = 'IGAA-super-secret-old-token-value'
        new_token = 'IGAA-super-secret-new-token-value'

        graph_api.refresh_token_success(new_token=new_token, expires_in=5183944)

        with caplog.at_level(logging.DEBUG):
            result = refresh_igaa_token(old_token)
            fake_result = MagicMock(returncode=0, stderr='')
            with patch('token_refresh.subprocess.run', return_value=fake_result):
                update_github_secret('INSTAGRAM_ACCESS_TOKEN', 'primary-account', result.access_token)

        for record in caplog.records:
            assert old_token not in record.getMessage()
            assert new_token not in record.getMessage()

    def test_token_value_never_logged_on_failure(self, graph_api, captured_emails, caplog, monkeypatch):
        """Same guarantee on the failure/alert path."""
        from token_refresh import run_refresh

        monkeypatch.setenv('SMTP_USERNAME', 'bot@example.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'secret')
        monkeypatch.setenv('NOTIFICATION_EMAIL', 'ops@example.com')

        old_token = 'IGAA-super-secret-failing-token'
        graph_api.refresh_token_failure()

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(SystemExit):
                run_refresh('primary-account', old_token)

        for record in caplog.records:
            assert old_token not in record.getMessage()
        for email in captured_emails:
            assert old_token not in email.get('subject', '')
            message = email.get('message')
            if message is not None:
                assert old_token not in str(message.get_payload())


class TestThreads:
    def test_threads_token_refresh(self, graph_api):
        """Threads long-lived tokens are refreshable via
        graph.threads.net/refresh_access_token?grant_type=th_refresh_token
        (confirmed against Meta's Threads API docs during WP7
        implementation — same 24h/60-day contract and response shape as
        Instagram). THREADS_ACCESS_TOKEN is refreshed and written back in
        the same run, with the same no-log and stdin rules."""
        from token_refresh import refresh_threads_token
        import responses as responses_lib

        with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(
                responses_lib.GET,
                'https://graph.threads.net/refresh_access_token',
                json={'access_token': 'THREADS-new-token', 'token_type': 'bearer', 'expires_in': 5183944},
                status=200,
            )
            result = refresh_threads_token('THREADS-old-token')

        assert result.access_token == 'THREADS-new-token'
        assert result.expires_in_seconds == 5183944

    def test_run_refresh_skips_threads_when_not_configured(self, graph_api):
        """An environment with no Threads token configured (None) is skipped
        without error — Threads cross-posting is optional per-account."""
        from token_refresh import run_refresh

        graph_api.refresh_token_success(new_token='IGAA-new-token', expires_in=5183944)

        fake_result = MagicMock(returncode=0, stderr='')
        with patch('token_refresh.subprocess.run', return_value=fake_result) as mock_run:
            run_refresh('primary-account', 'IGAA-old-token', threads_token=None)

        # Only the Instagram secret was written back - no Threads call attempted.
        assert mock_run.call_count == 1
        assert mock_run.call_args.args[0][3] == 'INSTAGRAM_ACCESS_TOKEN'

    def test_run_refresh_writes_back_both_tokens(self, graph_api):
        """With both tokens configured, run_refresh refreshes and writes
        back Instagram then Threads in the same run."""
        from token_refresh import run_refresh
        import responses as responses_lib

        graph_api.refresh_token_success(new_token='IGAA-new-token', expires_in=5183944)
        graph_api._rsps.add(
            responses_lib.GET,
            'https://graph.threads.net/refresh_access_token',
            json={'access_token': 'THREADS-new-token', 'token_type': 'bearer', 'expires_in': 5183944},
            status=200,
        )

        fake_result = MagicMock(returncode=0, stderr='')
        with patch('token_refresh.subprocess.run', return_value=fake_result) as mock_run:
            run_refresh('primary-account', 'IGAA-old-token', threads_token='THREADS-old-token')

        assert mock_run.call_count == 2
        secret_names = [call.args[0][3] for call in mock_run.call_args_list]
        assert secret_names == ['INSTAGRAM_ACCESS_TOKEN', 'THREADS_ACCESS_TOKEN']
