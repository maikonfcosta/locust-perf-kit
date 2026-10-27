"""Profile definitions, execution runner, and result parser for Locust tests."""

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadProfile:
    name: str
    users: int
    spawn_rate: int
    run_time: str


PROFILES = {
    "smoke": LoadProfile(name="smoke", users=5, spawn_rate=2, run_time="10s"),
    "load": LoadProfile(name="load", users=50, spawn_rate=5, run_time="30s"),
    "spike": LoadProfile(name="spike", users=100, spawn_rate=25, run_time="20s"),
    "stress": LoadProfile(name="stress", users=200, spawn_rate=10, run_time="45s"),
}


@dataclass
class RouteMetric:
    name: str
    method: str
    num_requests: int
    num_failures: int
    median_response_time: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float


@dataclass
class RunSummary:
    profile: str
    total_requests: int
    total_failures: int
    error_rate_pct: float
    p95_ms: float
    p99_ms: float
    rps: float
    routes: list[RouteMetric]


def run_profile(
    profile_name: str,
    host: str = "http://127.0.0.1:8089",
    output_dir: Path | str = "test-results",
) -> RunSummary:
    profile = PROFILES.get(profile_name)
    if not profile:
        raise ValueError(f"Unknown profile: {profile_name}. Available: {list(PROFILES.keys())}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    csv_prefix = out_path / f"locust_{profile.name}"

    cmd = [
        "uv",
        "run",
        "locust",
        "--headless",
        "-u",
        str(profile.users),
        "-r",
        str(profile.spawn_rate),
        "--run-time",
        profile.run_time,
        "--host",
        host,
        "--csv",
        str(csv_prefix),
        "--html",
        str(out_path / f"report_{profile.name}.html"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Locust run failed with code {result.returncode}:\n{result.stderr}")

    return parse_locust_csv(csv_prefix)


def parse_locust_csv(csv_prefix: Path) -> RunSummary:
    stats_file = Path(f"{csv_prefix}_stats.csv")
    if not stats_file.exists():
        raise FileNotFoundError(f"Locust stats file not found at: {stats_file}")

    total_requests = 0
    total_failures = 0
    p95 = 0.0
    p99 = 0.0
    routes: list[RouteMetric] = []

    with open(stats_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "")
            method = row.get("Type", "")
            reqs = int(row.get("Request Count", 0))
            fails = int(row.get("Failure Count", 0))
            med = float(row.get("50%", 0.0))
            avg = float(row.get("Average Response Time", 0.0))
            p95_val = float(row.get("95%", 0.0))
            p99_val = float(row.get("99%", 0.0))

            if name == "Aggregated":
                total_requests = reqs
                total_failures = fails
                p95 = p95_val
                p99 = p99_val
            else:
                routes.append(
                    RouteMetric(
                        name=name,
                        method=method,
                        num_requests=reqs,
                        num_failures=fails,
                        median_response_time=med,
                        avg_response_time=avg,
                        p95_response_time=p95_val,
                        p99_response_time=p99_val,
                    )
                )

    error_rate = (total_failures / total_requests * 100.0) if total_requests > 0 else 0.0
    rps = float(total_requests)  # Approximate aggregate / duration

    return RunSummary(
        profile=csv_prefix.stem.replace("locust_", ""),
        total_requests=total_requests,
        total_failures=total_failures,
        error_rate_pct=round(error_rate, 2),
        p95_ms=round(p95, 2),
        p99_ms=round(p99, 2),
        rps=round(rps, 2),
        routes=routes,
    )
