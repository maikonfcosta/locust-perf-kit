"""Tests validating SLO evaluation, failure injection, and gate blockage."""

import pytest

from locust_perf_kit.gate.runner import RouteMetric, RunSummary, run_profile
from locust_perf_kit.gate.validator import SloThresholds, evaluate_slo
from locust_perf_kit.mock_server.server import MockConduitServer


@pytest.fixture(scope="module")
def mock_server():
    server = MockConduitServer(port=8089)
    server.start()
    yield server
    server.stop()


def test_slo_evaluation_pass(mock_server, tmp_path):
    mock_server.set_latency(0.0)
    summary = run_profile(profile_name="smoke", host="http://127.0.0.1:8089", output_dir=tmp_path)
    verdict = evaluate_slo(summary)

    assert verdict.passed is True
    assert len(verdict.violations) == 0
    assert "[PASS] SMOKE Profile" in verdict.summary_markdown
    assert "**ALL SLO CRITERIA MET**" in verdict.summary_markdown


def test_slo_evaluation_failure_injection_proves_gate_blocks(mock_server, tmp_path):
    """Failure injection proof: inject 350ms artificial latency on server to prove the gate blocks."""
    mock_server.set_latency(350.0)
    try:
        summary = run_profile(
            profile_name="smoke", host="http://127.0.0.1:8089", output_dir=tmp_path
        )
        # Custom strict read threshold: 300ms
        thresholds = SloThresholds(max_read_p95_ms=300.0, max_aggregate_p95_ms=320.0)
        verdict = evaluate_slo(summary, thresholds=thresholds)

        # Proves the gate blocks!
        assert verdict.passed is False, "Expected gate to FAIL when latency is injected"
        assert len(verdict.violations) > 0
        assert "[FAIL] SMOKE Profile" in verdict.summary_markdown
        assert "exceeds" in verdict.violations[0]
    finally:
        mock_server.set_latency(0.0)


def test_slo_evaluation_error_rate_violation():
    dummy_summary = RunSummary(
        profile="smoke",
        total_requests=100,
        total_failures=5,
        error_rate_pct=5.0,
        p95_ms=50.0,
        p99_ms=80.0,
        rps=20.0,
        routes=[
            RouteMetric(
                name="[GET] /api/tags",
                method="GET",
                num_requests=100,
                num_failures=5,
                median_response_time=30.0,
                avg_response_time=35.0,
                p95_response_time=50.0,
                p99_response_time=80.0,
            )
        ],
    )
    verdict = evaluate_slo(dummy_summary)
    assert verdict.passed is False
    assert any("Error rate 5.0%" in v for v in verdict.violations)
