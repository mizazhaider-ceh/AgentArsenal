---
name: testing-strategies
description: "Use when building a test strategy for a Python project: choosing what to test at each level of the test pyramid, writing pytest unit tests with fixtures and parametrize, mocking external services, measuring coverage, writing integration and end-to-end tests, fixing flaky tests, running tests in CI, or reviewing whether a codebase is under-tested. Use when the task mentions pytest, test coverage, unit tests, integration tests, mocking, TDD, or flaky tests."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [code-reviewer, python-cli-tooling]
tools:
  - name: pytest
    version: 8.3
  - name: Python
    version: 3.12
  - name: coverage.py
    version: 7.6
---
Testing is how a codebase stays changeable: tests catch regressions before
users do and document what the code is supposed to do. This skill covers a
practical testing strategy for Python projects with pytest 8.3: the test
pyramid, unit test technique (fixtures, parametrize, mocking), integration
and end-to-end tests, coverage, flaky test triage, and CI wiring. Scope is
strategy and technique; load and performance testing belong to
performance-tuning.

## Quick Workflow

1. Map the pyramid: many fast unit tests, fewer integration tests, a
   handful of end-to-end tests.
2. Write the first failing test before the fix (TDD for bug fixes at
   minimum).
3. Use fixtures for setup, parametrize for input matrices, mocks for
   boundaries.
4. Keep unit tests hermetic: no network, no filesystem outside tmp_path,
   no wall-clock sleeps.
5. Measure coverage and raise it on changed lines, not as a vanity
   number.
6. Quarantine and fix flaky tests immediately; a flaky suite trains
   everyone to ignore red builds.
7. Run the full suite in CI on every pull request, with the same command
   developers run locally.
8. Review test quality in code review: one behavior per test, clear
   names, no logic in tests.

## 1. The test pyramid

```text
        /\
       /  \   E2E: a few journeys (slow, brittle, high value)
      /----\
     /      \  Integration: components wired together
    /--------\
   /          \ Unit: many, fast, isolated (the base)
```

Budget rule of thumb: unit tests run in milliseconds and number in the
hundreds; integration tests in seconds and number in the dozens; E2E
tests in minutes and number under twenty. When the pyramid inverts
(everything is E2E), the suite is slow, flaky, and nobody runs it.

```bash
# Project layout that mirrors the pyramid
mkdir -p tests/unit tests/integration tests/e2e
touch tests/__init__.py tests/unit/__init__.py

# Mark slow tiers so developers can run the fast base by default
# pytest.ini:
# [pytest]
# markers =
#     integration: integration tests
#     e2e: end-to-end tests
```

```bash
pytest tests/unit -q            # fast feedback loop
pytest -m "not e2e" -q         # everything but the slow tier
```

## 2. Unit tests with pytest: fixtures and parametrize

```python
# tests/unit/test_pricing.py
import pytest
from shop.pricing import total_for

@pytest.fixture
def cart():
    return [{"sku": "book", "price": 12.0, "qty": 2}]

def test_empty_cart_totals_zero(cart):
    assert total_for([], tax_rate=0.2) == 0.0

@pytest.mark.parametrize("qty,price,expected", [
    (1, 10.0, 12.0),     # with 20% tax
    (3, 5.0, 18.0),
    (0, 99.0, 0.0),      # zero quantity edge
])
def test_total_for_cases(qty, price, expected):
    items = [{"sku": "x", "price": price, "qty": qty}]
    assert total_for(items, tax_rate=0.2) == pytest.approx(expected)

def test_negative_price_rejected():
    with pytest.raises(ValueError, match="price"):
        total_for([{"sku": "x", "price": -1.0, "qty": 1}], tax_rate=0.2)
```

Fixture rules: fixtures build state, tests assert behavior; one assert
focus per test (multiple asserts on the same behavior are fine); name
tests `test_<unit>_<scenario>_<expected>`.

```bash
pytest tests/unit/test_pricing.py -v
pytest tests/unit/test_pricing.py -k "negative or zero" -v
```

## 3. Mocking at the boundaries

Mock I/O (HTTP, databases, filesystems, clocks), never business logic.
Mocking the thing you are testing proves nothing.

```python
# tests/unit/test_notifier.py
from unittest.mock import Mock, patch
from shop.notifier import send_receipt

def test_send_receipt_posts_to_webhook():
    fake_http = Mock()
    fake_http.post.return_value.status_code = 200
    with patch("shop.notifier.http_client", fake_http):
        send_receipt("izaz@example.com", 42)
    fake_http.post.assert_called_once()
    url, payload = fake_http.post.call_args.args
    assert url.endswith("/receipts")
    assert payload["order_id"] == 42

def test_retry_on_transient_failure():
    from requests import ConnectionError
    fake_http = Mock()
    fake_http.post.side_effect = [ConnectionError(), Mock(status_code=200)]
    with patch("shop.notifier.http_client", fake_http):
        send_receipt("izaz@example.com", 42)   # must retry, not crash
    assert fake_http.post.call_count == 2
```

Use `tmp_path` for files and `freezegun`-style time control (or inject a
clock) instead of real sleeps:

```python
def test_report_writes_csv(tmp_path):
    from shop.report import write_csv
    out = tmp_path / "report.csv"
    write_csv([{"a": 1}], out)
    assert out.read_text().splitlines()[0] == "a"
```

## 4. Integration tests

Test components wired together with real dependencies, but still local:
SQLite instead of Postgres where the dialect allows, testcontainers or a
local Redis for the real thing.

```python
# tests/integration/test_checkout.py
import pytest
from shop.app import create_app

@pytest.fixture
def client():
    app = create_app({"DATABASE_URL": "sqlite:///:memory:"})
    return app.test_client()

def test_checkout_creates_order_and_charges(client):
    r = client.post("/v1/orders", json={"item": "book", "qty": 1},
                    headers={"Idempotency-Key": "test-1"})
    assert r.status_code == 201
    order_id = r.get_json()["data"]["id"]
    r2 = client.get(f"/v1/orders/{order_id}")
    assert r2.status_code == 200
```

```bash
pytest -m integration -q
```

Keep integration tests independent: each test builds its own data and
cleans up (transactions rolled back, tmp dirs, unique key prefixes).

## 5. Coverage that means something

```bash
# Run with branch coverage, fail under the gate
pytest --cov=shop --cov-branch --cov-report=term-missing \
  --cov-fail-under=85 tests/unit

# HTML report to find the untested lines
pytest --cov=shop --cov-report=html tests/
python3 -m http.server 8000 --directory htmlcov &
```

Coverage rules: enforce the gate on new/changed lines in CI rather than
chasing 100 percent globally; uncovered lines should be a conscious
choice (defensive branches, platform code), marked with
`# pragma: no cover` and a reason. Coverage measures what ran, not what
was asserted; pair it with review.

## 6. Flaky test triage

```bash
# Find the flake: run the suspect test 50 times
pytest tests/unit/test_cache.py -q --count=50 2>/dev/null \
  || pip list 2>/dev/null | grep -i repeat
# (pytest-repeat plugin: pytest --count=50)

# Run tests in random order to catch inter-test coupling
pytest -p no:randomly tests/ -q   # or install pytest-randomly and watch
```

Common flake causes and fixes: wall-clock sleeps (replace with polling
loops with timeouts), shared global state (fresh fixtures per test),
unordered collections in assertions (sort first), timezones (pin
TZ=UTC in CI), parallel test workers sharing ports or files (unique
resources per worker). Policy: a flaky test is quarantined (marked
`xfail(strict=False)` with a ticket) the same day it is found, fixed
within the sprint, never left red.

## 7. CI wiring

```yaml
# .github/workflows/tests.yml (excerpt)
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m "not e2e" --cov=shop --cov-fail-under=85 -q
      - run: pytest -m e2e -q   # nightly or on main, not every PR
```

CI rules: the exact same `pytest` command developers run locally; fail
the build on warnings that matter (`-W error` for deprecation warnings
in your own code); cache dependencies; split E2E to a scheduled run if
it exceeds a few minutes.

## 8. What good tests look like (review checklist)

- Name says what is tested and what is expected.
- Arrange/Act/Assert structure, visually separated.
- No `time.sleep`, no network, no hardcoded `/tmp` paths.
- Assertions on behavior, not implementation (do not assert private
  method call counts unless the contract is the call).
- Test data is minimal and meaningful, not a 200-line fixture for a
  one-line assertion.
- Each bug fix ships with a regression test that fails without the fix;
  verify by stashing the fix and watching it fail.

## Edge cases

- Testing code that calls `sys.exit` or `os._exit`: use
  `pytest.raises(SystemExit)`; for `os._exit` you must subprocess.
- Datetime-dependent logic: inject a clock function; never assert on
  `datetime.now()` directly.
- Randomness: seed it (`random.seed(0)`) or assert on properties, not
  exact values.
- Tests that pass alone but fail together: shared module-level state;
  run with `-p randomly` to find the coupling, then isolate fixtures.
- Database migrations in tests: test against the migrated schema from
  scratch at least once; migration drift is a classic integration-only
  failure.
- External APIs in E2E: record and replay (VCR-style cassettes) for PR
  runs; hit the real API only in scheduled runs with a sandbox key.

## Escalation

- Suite takes 30 minutes: profile it (`pytest --durations=20`), split
  tiers, parallelize with pytest-xdist (`-n auto`), and move slow tests
  down the pyramid or to nightly.
- Coverage gate blocks a legitimate PR: check whether the uncovered
  lines are defensive; add targeted tests or document the exclusion,
  do not lower the gate silently.
- Cannot reproduce a CI-only failure: run the exact CI container image
  locally, print the environment (`pip freeze`, env vars), and bisect
  the test file with `--lf` (last failed) plus `-x`.
- Flaky E2E nobody owns: assign an owner per E2E journey; unowned tests
  rot.

## Detection and defender view

For engineering teams, the defender view is quality misuse: tests that
lie. Watch for:

```bash
# Tests with no assertions (they pass by existing)
grep -rL "assert" tests/unit --include='test_*.py'

# Tests disabled via skip markers (tech debt hiding)
grep -rn "pytest.mark.skip" tests/ | wc -l

# Coverage exclusions growing unchecked
grep -rn "pragma: no cover" src/ | wc -l
```

Misuse signals: a suite that is green but the product is broken (mocks
asserting on mocks), coverage at 95 percent with zero integration tests,
and E2E tests that hit production. Defensive practice: mutation testing
on critical modules (mutmut or cosmic-ray) to check tests actually kill
bugs, and a dashboard tracking flake rate per test so rot is visible.

## Key references

- pytest 8.3 documentation: https://docs.pytest.org/en/stable/
- coverage.py 7.6 docs: https://coverage.readthedocs.io/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
- Google Testing Blog (test sizes): https://testing.googleblog.com/
- Martin Fowler on the test pyramid:
  https://martinfowler.com/articles/practical-test-pyramid.html
- CWE-754 (Improper Check for Unusual Conditions): untested edge cases.
