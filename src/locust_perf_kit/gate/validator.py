"""SLO gate validator, failure injection verification, and GitHub step summary generator."""

from dataclasses import dataclass
from pathlib import Path

from locust_perf_kit.gate.runner import RunSummary


@dataclass
class SloThresholds:
    max_error_rate_pct: float = 1.0
    max_read_p95_ms: float = 300.0
    max_write_p95_ms: float = 600.0
    max_aggregate_p95_ms: float = 400.0


@dataclass
class GateVerdict:
    passed: bool
    violations: list[str]
    summary_markdown: str


def evaluate_slo(summary: RunSummary, thresholds: SloThresholds | None = None) -> GateVerdict:
    if thresholds is None:
        thresholds = SloThresholds()

    violations: list[str] = []

    # Check error rate
    if summary.error_rate_pct > thresholds.max_error_rate_pct:
        violations.append(
            f"Error rate {summary.error_rate_pct}% exceeds limit of {thresholds.max_error_rate_pct}%"
        )

    # Check aggregate p95
    if summary.p95_ms > thresholds.max_aggregate_p95_ms:
        violations.append(
            f"Aggregate p95 {summary.p95_ms}ms exceeds threshold of {thresholds.max_aggregate_p95_ms}ms"
        )

    # Check per-route p95
    for route in summary.routes:
        limit = (
            thresholds.max_write_p95_ms
            if route.method.upper() == "POST"
            else thresholds.max_read_p95_ms
        )
        if route.p95_response_time > limit:
            violations.append(
                f"Route '{route.name}' p95 {route.p95_response_time}ms exceeds limit of {limit}ms"
            )

    passed = len(violations) == 0
    markdown = generate_summary_markdown(summary, thresholds, passed, violations)

    return GateVerdict(passed=passed, violations=violations, summary_markdown=markdown)


def generate_summary_markdown(
    summary: RunSummary,
    thresholds: SloThresholds,
    passed: bool,
    violations: list[str],
) -> str:
    status_icon = "PASS" if passed else "FAIL"
    status_msg = (
        "**ALL SLO CRITERIA MET**"
        if passed
        else f"**GATE VIOLATED ({len(violations)} issues)**"
    )

    md = [
        f"## Performance Test Gate: [{status_icon}] {summary.profile.upper()} Profile",
        f"- **Verdict:** {status_msg}",
        f"- **Total Requests:** {summary.total_requests}",
        f"- **Error Rate:** {summary.error_rate_pct}% (Max: {thresholds.max_error_rate_pct}%)",
        f"- **Aggregate p95:** {summary.p95_ms}ms (Max: {thresholds.max_aggregate_p95_ms}ms)",
        f"- **Aggregate p99:** {summary.p99_ms}ms",
        "",
        "### Route Latency Breakdown",
        "| Method | Endpoint | Requests | Failures | Med (p50) | p95 | Limit | Status |",
        "|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for route in summary.routes:
        limit = (
            thresholds.max_write_p95_ms
            if route.method.upper() == "POST"
            else thresholds.max_read_p95_ms
        )
        route_ok = route.p95_response_time <= limit and route.num_failures == 0
        tag = "PASS" if route_ok else "FAIL"
        md.append(
            f"| `{route.method}` | `{route.name}` | {route.num_requests} | {route.num_failures} | "
            f"{route.median_response_time}ms | {route.p95_response_time}ms | {limit}ms | {tag} |"
        )

    if violations:
        md.append("")
        md.append("### Violations")
        for v in violations:
            md.append(f"- ❌ {v}")

    return "\n".join(md)


def write_step_summary(verdict: GateVerdict, destination: Path | str | None = None) -> None:
    if destination is None:
        import os

        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            destination = Path(summary_file)
        else:
            destination = Path("test-results/summary.md")

    dest_path = Path(destination)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(verdict.summary_markdown)
