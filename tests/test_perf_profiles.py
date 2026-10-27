"""Performance profiles test suite."""

from pathlib import Path

import pytest

from locust_perf_kit.gate.runner import run_profile
from locust_perf_kit.mock_server.server import MockConduitServer


@pytest.fixture(scope="module")
def mock_server():
    server = MockConduitServer(port=8089)
    server.start()
    yield server
    server.stop()


def test_smoke_profile_execution(mock_server, tmp_path):
    summary = run_profile(profile_name="smoke", host="http://127.0.0.1:8089", output_dir=tmp_path)

    assert summary.total_requests > 10, f"Expected >10 requests, got {summary.total_requests}"
    assert summary.total_failures == 0, f"Expected 0 failures, got {summary.total_failures}"
    assert summary.error_rate_pct == 0.0
    assert summary.p95_ms < 150.0, f"Expected p95 < 150ms, got {summary.p95_ms}ms"

    # Verify HTML and CSV artifacts were created
    assert Path(tmp_path / "report_smoke.html").exists()
    assert Path(tmp_path / "locust_smoke_stats.csv").exists()

    # Verify routes breakdown
    route_names = [r.name for r in summary.routes]
    assert "[GET] /api/tags" in route_names
    assert "[GET] /api/articles" in route_names


def test_profile_metrics_structure(mock_server, tmp_path):
    summary = run_profile(profile_name="smoke", host="http://127.0.0.1:8089", output_dir=tmp_path)

    assert summary.profile == "smoke"
    assert summary.p99_ms >= 0.0
    for route in summary.routes:
        assert route.num_requests > 0
        assert route.p95_response_time >= 0.0
