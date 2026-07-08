"""
Automated long-lived token refresh for Instagram (IGAA) and Threads.

Refreshes INSTAGRAM_ACCESS_TOKEN / THREADS_ACCESS_TOKEN before their 60-day
expiry and writes the rotated value back to the environment-scoped GitHub
secret via `gh secret set`. Designed to run standalone in
.github/workflows/token-refresh.yml (matrixed over primary-account /
secondary-account), independent of Config/main.py's posting flow.

Meta requires a token be >= 24h old (and not yet expired) to refresh, but
does not document a distinguishable error for a too-young token, and this
module has no way to know a token's issuance time (only its value). The
weekly workflow cadence is the age guarantee instead: every refresh either
targets a token rotated at least a week ago, or the initial manually-issued
token, both always well past 24h. A too-young rejection would surface as an
ordinary TokenRefreshError and alert - a scenario the rollout order in the
spec is designed to never hit in practice.

Spec: docs/refactor/04-token-refresh-spec.md.
"""
import argparse
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

import requests

from notification_system import notifier

logger = logging.getLogger(__name__)


@dataclass
class RefreshResult:
    """Outcome of a successful token refresh."""
    access_token: str
    expires_in_seconds: int


class TokenRefreshError(Exception):
    """Raised when a refresh call fails or returns an unexpected payload."""


def _masked(token: str) -> str:
    """Prefix/length only - the token value itself must never be logged."""
    prefix = token[:4] if token else ''
    return f"{prefix}...(len={len(token)})"


def refresh_igaa_token(token: str) -> RefreshResult:
    """Refresh a long-lived Instagram (IGAA) access token.

    Makes ZERO HTTP calls for a non-IGAA token - refuses immediately so a
    stray EAA token in an environment can never be silently exchanged
    against the wrong endpoint.
    """
    if not (token or '').startswith(('IGAA', 'IGA')):
        raise TokenRefreshError(
            "Token is not an Instagram Login (IGAA) token; refresh_access_token "
            "only supports IGAA tokens. See docs/refactor/runbooks/"
            "eaa-to-igaa-migration.md to migrate a legacy EAA token first."
        )

    logger.info(f"Refreshing Instagram token {_masked(token)}")
    try:
        response = requests.get(
            'https://graph.instagram.com/refresh_access_token',
            params={'grant_type': 'ig_refresh_token', 'access_token': token},
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        # requests/urllib3 exception strings often embed the full request URL
        # (including the access_token query param) - log only the exception
        # type, never str(e), to preserve the no-token-in-logs guarantee.
        raise TokenRefreshError(f"Instagram refresh request failed: {type(e).__name__}") from e

    return _parse_refresh_response(response, 'Instagram')


def refresh_threads_token(token: str) -> RefreshResult:
    """Refresh a long-lived Threads access token.

    Mirrors the Instagram flow: graph.threads.net/refresh_access_token with
    grant_type=th_refresh_token, same 24h-minimum-age / 60-day-lifetime
    contract, same response shape (confirmed against Meta's Threads API docs
    during WP7 implementation).
    """
    logger.info(f"Refreshing Threads token {_masked(token)}")
    try:
        response = requests.get(
            'https://graph.threads.net/refresh_access_token',
            params={'grant_type': 'th_refresh_token', 'access_token': token},
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        # See refresh_igaa_token: never interpolate str(e) - it can embed the
        # request URL with access_token in it.
        raise TokenRefreshError(f"Threads refresh request failed: {type(e).__name__}") from e

    return _parse_refresh_response(response, 'Threads')


def _parse_refresh_response(response: requests.Response, label: str) -> RefreshResult:
    if response.status_code != 200:
        raise TokenRefreshError(
            f"{label} refresh returned HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        data = response.json()
        access_token = data['access_token']
        expires_in_seconds = int(data['expires_in'])
    except (ValueError, KeyError, TypeError) as e:
        raise TokenRefreshError(
            f"{label} refresh returned an unexpected payload: {e}"
        ) from e

    return RefreshResult(access_token=access_token, expires_in_seconds=expires_in_seconds)


def update_github_secret(secret_name: str, env_name: str, value: str) -> None:
    """Write a secret to a GitHub Environment via the gh CLI.

    The value is delivered on stdin only - never as an argv token (visible
    in `ps`/process lists on the runner) and never logged.
    """
    logger.info(f"Writing {secret_name} to environment '{env_name}' ({_masked(value)})")
    try:
        result = subprocess.run(
            ['gh', 'secret', 'set', secret_name, '--env', env_name, '--body', '-'],
            input=value,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise TokenRefreshError(f"gh secret set failed to launch: {e}") from e

    if result.returncode != 0:
        raise TokenRefreshError(
            f"gh secret set {secret_name} --env {env_name} failed "
            f"(exit {result.returncode}): {result.stderr.strip()[:300]}"
        )


def _alert_and_exit(context_label: str, error: Exception) -> None:
    """Send the consolidated critical-failure alert and exit non-zero."""
    logger.error(f"{context_label}: {error}")
    notifier.send_critical_failure_alert(
        error_type="TOKEN_REFRESH_FAILED",
        error_details=f"{context_label}: {error}",
        context={"component": context_label},
    )
    sys.exit(1)


def run_refresh(env_name: str, instagram_token: Optional[str],
                 threads_token: Optional[str] = None) -> None:
    """Refresh and write back tokens for one environment.

    instagram_token is required (every environment has one). threads_token
    is optional - environments without Threads cross-posting configured
    pass None and are skipped without error.
    """
    try:
        result = refresh_igaa_token(instagram_token)
    except TokenRefreshError as e:
        _alert_and_exit(f"Instagram token refresh ({env_name})", e)
        return  # pragma: no cover - _alert_and_exit exits the process

    try:
        update_github_secret('INSTAGRAM_ACCESS_TOKEN', env_name, result.access_token)
    except TokenRefreshError as e:
        _alert_and_exit(f"Instagram secret write-back ({env_name})", e)
        return  # pragma: no cover

    logger.info(
        f"Instagram token refreshed for {env_name}: expires in "
        f"{result.expires_in_seconds}s (~{result.expires_in_seconds // 86400}d)"
    )

    if not threads_token:
        logger.info(f"No Threads token configured for {env_name}; skipping")
        return

    try:
        threads_result = refresh_threads_token(threads_token)
    except TokenRefreshError as e:
        _alert_and_exit(f"Threads token refresh ({env_name})", e)
        return  # pragma: no cover

    try:
        update_github_secret('THREADS_ACCESS_TOKEN', env_name, threads_result.access_token)
    except TokenRefreshError as e:
        _alert_and_exit(f"Threads secret write-back ({env_name})", e)
        return  # pragma: no cover

    logger.info(
        f"Threads token refreshed for {env_name}: expires in "
        f"{threads_result.expires_in_seconds}s (~{threads_result.expires_in_seconds // 86400}d)"
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description='Refresh IGAA/Threads long-lived tokens')
    parser.add_argument('--env-name', required=True,
                         help='GitHub Environment name (e.g. primary-account)')
    args = parser.parse_args()

    instagram_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    if not instagram_token:
        _alert_and_exit(
            f"Instagram token refresh ({args.env_name})",
            TokenRefreshError("INSTAGRAM_ACCESS_TOKEN is not set in this environment"),
        )
        return

    threads_token = os.getenv('THREADS_ACCESS_TOKEN') or None
    run_refresh(args.env_name, instagram_token, threads_token)


if __name__ == '__main__':
    main()
