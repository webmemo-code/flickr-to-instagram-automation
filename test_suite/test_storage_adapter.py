"""WP3 scaffold — GitFileStorageAdapter behavior.

Spec: docs/refactor/03-state-layer-spec.md. Uses the mock_github_contents
fixture (responses-based Contents API fake) — no live GitHub calls.
"""

import pytest

WP3 = pytest.mark.xfail(reason="WP3 not implemented", strict=False)


class TestErrorTaxonomy:
    @WP3
    def test_missing_file_reported_as_absent_not_error(self):
        """Contents API 404 for a state file (or missing branch on first run)
        is surfaced as a typed 'absent' outcome (e.g. StateFileNotFound or
        documented sentinel) — distinguishable from failures WITHOUT string-
        matching '404' in the message."""
        pytest.fail("scaffold: implement per docstring")

    @WP3
    def test_denied_and_server_errors_raise(self):
        """401/403, 5xx, rate-limit, connection errors, and JSON parse errors
        raise (propagate as failures) — they are never converted into an
        empty-state result at the adapter level."""
        pytest.fail("scaffold: implement per docstring")


class TestAvailabilityCaching:
    @WP3
    def test_is_available_cached_per_process(self):
        """N consecutive reads/writes trigger exactly ONE get_branch call —
        the availability check is cached for the adapter instance lifetime
        (one instance per run), not re-issued per operation."""
        pytest.fail("scaffold: implement per docstring")


class TestBootstrap:
    @WP3
    def test_branch_autocreation_on_first_run(self):
        """REGRESSION: when the automation-state branch does not exist, the
        adapter still creates it (current behavior) and subsequent reads
        report 'absent' rather than raising."""
        pytest.fail("scaffold: implement per docstring")


class TestWrites:
    @WP3
    def test_write_failure_is_never_swallowed(self):
        """A failed write (e.g. stale sha from a concurrent update, or 5xx)
        raises — it cannot be reported as success to StateManager."""
        pytest.fail("scaffold: implement per docstring")
