"""Shared fixture contract for the test suite.

See docs/refactor/02-test-scaffold-map.md for the fixture contract this
implements. No test file may redefine a fixture that this conftest provides.
"""

import copy
import json

import pytest

from photo_models import EnrichedPhoto


def safe_print(text):
    """Print text with Unicode characters safely on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'ignore').decode('ascii'))


REQUIRED_ENV = {
    'FLICKR_API_KEY': 'k',
    'FLICKR_USER_ID': 'u',
    'FLICKR_USERNAME': 'n',
    'ANTHROPIC_API_KEY': 'a',
    'GITHUB_TOKEN': 't',
    'FLICKR_ALBUM_ID': '123',
    'INSTAGRAM_ACCESS_TOKEN': 'tok',
    'INSTAGRAM_ACCOUNT_ID': 'acc',
}

# Every env var Config() reads (config.py), cleared before REQUIRED_ENV +
# overrides are applied so a developer/CI environment with e.g. SMTP_HOST or
# THREADS_API_VERSION already set can't leak into a test and make defaulting
# assertions flaky.
_CONFIG_ENV_KEYS = (
    'FLICKR_API_KEY', 'FLICKR_USER_ID', 'FLICKR_USERNAME', 'ANTHROPIC_API_KEY',
    'GITHUB_TOKEN', 'WORDPRESS_USERNAME', 'WORDPRESS_APP_PASSWORD',
    'FLICKR_ALBUM_ID', 'INSTAGRAM_ACCESS_TOKEN', 'INSTAGRAM_ACCOUNT_ID',
    'INSTAGRAM_APP_ID', 'FACEBOOK_PAGE_ID', 'FACEBOOK_PAGE_ACCESS_TOKEN',
    'THREADS_USER_ID', 'THREADS_ACCESS_TOKEN', 'THREADS_API_VERSION',
    'THREADS_POST_DELAY_HOURS', 'GRAPH_API_VERSION', 'ANTHROPIC_MODEL',
    'CREATE_AUDIT_ISSUES', 'BLOG_POST_URL', 'BLOG_POST_URLS',
    'NOTIFICATION_EMAIL', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME',
    'SMTP_PASSWORD', 'GITHUB_ACTIONS',
)


@pytest.fixture
def full_env(monkeypatch):
    """Factory fixture: set a complete, valid environment.

    Callable as ``full_env(**overrides)``; clears every env var Config()
    reads (so ambient developer/CI env vars can't leak in), monkeypatch-sets
    realistic dummy values for the required ones, then applies overrides.
    Returns the effective env dict.
    """
    def _apply(**overrides):
        for key in _CONFIG_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
        env = {**REQUIRED_ENV, **overrides}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return env

    return _apply


@pytest.fixture
def igaa_env(full_env):
    """`full_env` variant with INSTAGRAM_ACCESS_TOKEN prefixed 'IGAA...'."""
    def _apply(**overrides):
        return full_env(INSTAGRAM_ACCESS_TOKEN='IGAA-test-token', **overrides)

    return _apply


@pytest.fixture
def eaa_env(full_env):
    """`full_env` variant with INSTAGRAM_ACCESS_TOKEN prefixed 'EAA...'."""
    def _apply(**overrides):
        return full_env(INSTAGRAM_ACCESS_TOKEN='EAA-test-token', **overrides)

    return _apply


class FakeStorageAdapter:
    """In-memory StateStorageAdapter double with a call log.

    Records every call as (method, args) in ``.calls`` and every write in
    ``.writes``. Seedable via ``.seed(...)``. Failure injection via
    ``.fail_next(method, exc)``.
    """

    def __init__(self):
        self.calls = []
        self.writes = []
        self._posts = {}
        self._failed = {}
        self._metadata = {}
        self._pending_failures = {}

    def seed(self, posts=None, metadata=None, failed=None, account='primary', album_id='1'):
        key = (account, album_id)
        if posts is not None:
            self._posts[key] = copy.deepcopy(posts)
        if metadata is not None:
            self._metadata[key] = copy.deepcopy(metadata)
        if failed is not None:
            self._failed[key] = copy.deepcopy(failed)

    def fail_next(self, method, exc):
        self._pending_failures[method] = exc

    def _maybe_raise(self, method):
        if method in self._pending_failures:
            raise self._pending_failures.pop(method)

    def read_posts(self, account, album_id):
        self.calls.append(('read_posts', (account, album_id)))
        self._maybe_raise('read_posts')
        return copy.deepcopy(self._posts.get((account, album_id), []))

    def write_posts(self, account, album_id, posts):
        self.calls.append(('write_posts', (account, album_id)))
        self.writes.append(('write_posts', (account, album_id)))
        self._maybe_raise('write_posts')
        self._posts[(account, album_id)] = copy.deepcopy(posts)
        return True

    def read_failed_positions(self, account, album_id):
        self.calls.append(('read_failed_positions', (account, album_id)))
        self._maybe_raise('read_failed_positions')
        return copy.deepcopy(self._failed.get((account, album_id), []))

    def write_failed_positions(self, account, album_id, positions):
        self.calls.append(('write_failed_positions', (account, album_id)))
        self.writes.append(('write_failed_positions', (account, album_id)))
        self._maybe_raise('write_failed_positions')
        self._failed[(account, album_id)] = copy.deepcopy(positions)
        return True

    def read_metadata(self, account, album_id):
        self.calls.append(('read_metadata', (account, album_id)))
        self._maybe_raise('read_metadata')
        return copy.deepcopy(self._metadata.get((account, album_id), {}))

    def write_metadata(self, account, album_id, metadata):
        self.calls.append(('write_metadata', (account, album_id)))
        self.writes.append(('write_metadata', (account, album_id)))
        self._maybe_raise('write_metadata')
        self._metadata[(account, album_id)] = copy.deepcopy(metadata)
        return True

    def is_available(self):
        self.calls.append(('is_available', ()))
        self._maybe_raise('is_available')
        return True


@pytest.fixture
def fake_storage():
    return FakeStorageAdapter()


@pytest.fixture
def mock_github_contents():
    """`responses`-based fake of the GitHub Contents API + get_branch.

    Exposes ``.scenario(name)`` to register one of: 'first_run', 'forbidden',
    'server_error', 'connection_error', 'success'.
    """
    import responses as responses_lib

    class GithubContentsMock:
        API_BASE = 'https://api.github.com'

        def __init__(self, rsps):
            self._rsps = rsps

        def scenario(self, name, repo='owner/repo', path='state-data/primary/album-1/posts.json',
                     branch='automation-state', content=None):
            url = f'{self.API_BASE}/repos/{repo}/contents/{path}'
            if name == 'first_run':
                self._rsps.add(responses_lib.GET, url, json={'message': 'Not Found'}, status=404)
            elif name == 'forbidden':
                self._rsps.add(responses_lib.GET, url, json={'message': 'Forbidden'}, status=403)
            elif name == 'server_error':
                self._rsps.add(responses_lib.GET, url, json={'message': 'Server Error'}, status=500)
            elif name == 'connection_error':
                self._rsps.add(
                    responses_lib.GET, url,
                    body=ConnectionError('connection reset'),
                )
            elif name == 'success':
                import base64
                payload = content if content is not None else []
                encoded = base64.b64encode(json.dumps(payload).encode()).decode()
                self._rsps.add(
                    responses_lib.GET, url,
                    json={'content': encoded, 'sha': 'abc123', 'encoding': 'base64'},
                    status=200,
                )
            else:
                raise ValueError(f'unknown scenario: {name}')

    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield GithubContentsMock(rsps)


@pytest.fixture
def graph_api():
    """`responses`-based canned Meta Graph API payloads for both domains."""
    import responses as responses_lib

    class GraphApiMock:
        def __init__(self, rsps):
            self._rsps = rsps

        def media_create_success(self, domain='graph.facebook.com', version='v23.0',
                                  account_id='acc', creation_id='177000000000001'):
            self._rsps.add(
                responses_lib.POST,
                f'https://{domain}/{version}/{account_id}/media',
                json={'id': creation_id},
                status=200,
            )

        def media_publish_success(self, domain='graph.facebook.com', version='v23.0',
                                   account_id='acc', media_id='177900000000002'):
            self._rsps.add(
                responses_lib.POST,
                f'https://{domain}/{version}/{account_id}/media_publish',
                json={'id': media_id},
                status=200,
            )

        def error_expired_token(self, domain='graph.facebook.com', version='v23.0',
                                 account_id='acc', endpoint='media'):
            self._rsps.add(
                responses_lib.POST,
                f'https://{domain}/{version}/{account_id}/{endpoint}',
                json={'error': {
                    'message': 'Error validating access token: Session has expired',
                    'type': 'OAuthException',
                    'code': 190,
                    'error_subcode': 463,
                    'fbtrace_id': 'ABCDEF123456',
                }},
                status=400,
            )

        def error_rate_limit(self, domain='graph.facebook.com', version='v23.0',
                              account_id='acc', endpoint='media'):
            self._rsps.add(
                responses_lib.POST,
                f'https://{domain}/{version}/{account_id}/{endpoint}',
                json={'error': {
                    'message': 'Application request limit reached',
                    'type': 'OAuthException',
                    'code': 4,
                }},
                status=400,
            )

        def refresh_token_success(self, new_token='IGAA-refreshed-token', expires_in=5183944):
            self._rsps.add(
                responses_lib.GET,
                'https://graph.instagram.com/refresh_access_token',
                json={'access_token': new_token, 'token_type': 'bearer', 'expires_in': expires_in},
                status=200,
            )

        def refresh_token_failure(self):
            self._rsps.add(
                responses_lib.GET,
                'https://graph.instagram.com/refresh_access_token',
                json={'error': {'message': 'Invalid OAuth access token', 'code': 190}},
                status=400,
            )

    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield GraphApiMock(rsps)


@pytest.fixture
def sample_photo():
    """Factory for photo_models.EnrichedPhoto with realistic defaults."""
    def _make(position=1, **overrides):
        defaults = dict(
            id=f'5388301{position:04d}',
            title=f'Sample Photo {position}',
            url=f'https://live.staticflickr.com/1/5388301{position:04d}_abc123_c.jpg',
            server='1',
            secret='abc123',
            date_taken='2025-01-15 08:00:00',
            album_position=position,
            description='A sample travel photo used for testing.',
            photo_page_url=f'https://www.flickr.com/photos/user/5388301{position:04d}',
            source_url=None,
            hashtags='#Travel #Photography',
            exif_data=None,
            exif_hints={'source_urls': [], 'phrases': [], 'keywords': []},
            location_data=None,
            selected_blog=None,
        )
        defaults.update(overrides)
        return EnrichedPhoto(**defaults)

    return _make


@pytest.fixture
def sample_album(sample_photo):
    """Factory for a list of EnrichedPhoto covering a small album (default 5)."""
    def _make(size=5):
        return [sample_photo(position=i) for i in range(1, size + 1)]

    return _make


@pytest.fixture
def sample_posts_json():
    """Realistic posts.json content, including a legacy retry_history entry."""
    return [
        {
            'position': 1,
            'photo_id': '5388301001',
            'instagram_post_id': '17912345678901234',
            'facebook_post_id': None,
            'threads_post_id': None,
            'threads_posted_at': None,
            'threads_caption': None,
            'threads_retry_count': 0,
            'generated_body': 'A quiet morning on the lakeshore.',
            'posted_at': '2025-01-15T08:12:03.123456',
            'title': 'Lake Geneva at Dawn',
            'status': 'posted',
            'retry_count': 0,
            'retry_history': [],
            'workflow_run_id': '12345678901',
            'account': 'primary',
            'created_at': '2025-01-15T08:12:00.000000',
            'last_update': '2025-01-15T08:12:03.123456',
            'flickr_url': 'https://flickr.com/photos/user/5388301001',
            'instagram_url': 'https://www.instagram.com/p/Cxxxxxxxxxx/',
            'caption_length': 412,
            'hashtags_count': 8,
            'is_dry_run': False,
        },
        {
            'position': 2,
            'flickr_photo_id': '5388309999',
            'status': 'failed',
            'retry_count': 2,
            'retry_history': [
                {
                    'timestamp': '2025-01-15T09:00:00',
                    'error_message': 'Instagram API Error 190: token expired',
                    'workflow_run_id': '12345678902',
                    'retry_count': 1,
                },
                {
                    'timestamp': '2025-01-15T10:00:00',
                    'error_message': 'Instagram API Error 190: token expired',
                    'workflow_run_id': '12345678903',
                    'retry_count': 2,
                },
            ],
            'account': 'primary',
        },
    ]


@pytest.fixture
def captured_emails(monkeypatch):
    """Patch smtplib.SMTP; yield the list of sent messages.

    Covers both current SMTP call sites (email_notifier.EmailNotifier and
    notification_system.CriticalFailureNotifier) by patching smtplib.SMTP
    globally, since as of WP2 there is not yet a single consolidated sender
    (that is WP4's job).
    """
    sent = []

    class FakeSMTP:
        """Supports both current call sites: email_notifier.py's
        sendmail()/quit() and notification_system.py's
        `with smtplib.SMTP(...) as server: ... server.send_message(msg)`.
        """

        def __init__(self, host, port):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            pass

        def sendmail(self, from_addr, to_addr, text):
            sent.append({
                'recipient': to_addr,
                'from': from_addr,
                'raw': text,
            })

        def send_message(self, msg):
            sent.append({
                'recipient': msg.get('To'),
                'from': msg.get('From'),
                'subject': msg.get('Subject'),
                'message': msg,
            })

        def quit(self):
            pass

    monkeypatch.setattr('smtplib.SMTP', FakeSMTP)
    return sent


@pytest.fixture
def account_env_reisememo(full_env):
    """SECONDARY_* env preset for reisememo.ch."""
    def _apply(**overrides):
        return full_env(
            SECONDARY_ACCOUNT_ID='reisememo',
            SECONDARY_ACCOUNT_NAME='Reisememo',
            SECONDARY_ENVIRONMENT_NAME='secondary-account',
            SECONDARY_ACCOUNT_LANGUAGE='de',
            SECONDARY_BRAND_SIGNATURE='Reisememo von einem einzigartigen Reiseerlebnis.',
            SECONDARY_BLOG_DOMAINS='reisememo.ch,travelmemo.com',
            **overrides,
        )

    return _apply
