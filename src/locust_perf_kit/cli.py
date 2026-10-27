"""CLI entry point to run perf profiles and enforce SLO gates in CI."""

import argparse
import sys

from locust_perf_kit.gate.runner import run_profile
from locust_perf_kit.gate.validator import SloThresholds, evaluate_slo, write_step_summary
from locust_perf_kit.mock_server.server import MockConduitServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Locust Performance Test Runner & SLO Gate")
    parser.add_argument("--profile", default="smoke", choices=["smoke", "load", "spike", "stress"])
    parser.add_argument("--host", default="http://127.0.0.1:8089")
    parser.add_argument("--with-mock", action="store_true", help="Start embedded mock Conduit server")
    parser.add_argument("--inject-latency-ms", type=float, default=0.0, help="Inject artificial latency in mock")
    parser.add_argument("--output-dir", default="test-results")

    args = parser.parse_args()

    mock = None
    if args.with_mock:
        mock = MockConduitServer(port=8089, latency_ms=args.inject_latency_ms)
        mock.start()
        print(f"Started mock Conduit server on port 8089 (latency: {args.inject_latency_ms}ms).")

    try:
        print(f"Running Locust profile: {args.profile} against {args.host}...")
        summary = run_profile(args.profile, host=args.host, output_dir=args.output_dir)

        thresholds = SloThresholds()
        verdict = evaluate_slo(summary, thresholds=thresholds)

        # Print Markdown to stdout
        print("\n" + verdict.summary_markdown + "\n")

        # Write to $GITHUB_STEP_SUMMARY if present
        write_step_summary(verdict)

        if not verdict.passed:
            print("❌ Gate failed: SLO thresholds violated.", file=sys.stderr)
            sys.exit(1)
        else:
            print("✅ Gate passed: All SLO criteria satisfied.")
            sys.exit(0)

    finally:
        if mock:
            mock.stop()
            print("Stopped mock Conduit server.")


if __name__ == "__main__":
    main()
