#!/usr/bin/env python3
"""
run_benchmark.py — Full ABM performance comparison: Python vs Rust.

Usage::

    # Basic run (10 periods, 3 reps)
    uv run --group abm python scripts/run_benchmark.py

    # Extended run
    uv run --group abm python scripts/run_benchmark.py --periods 20 --reps 5

    # Save results and generate report
    uv run --group abm python scripts/run_benchmark.py --output results.json

The script produces:
  - A formatted console table showing timing for each backend and scenario
  - Speedup ratios between backends
  - A JSON file with complete timing data

Requirements:
  - The Rust extension must be built first:
      ./scripts/build_rust_abm.sh
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from project root without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tests.test_abm_performance import (
    BENCH_PERIODS,
    N_REPS,
    SCENARIOS,
    print_table,
    run_benchmarks,
    save_results,
)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run ABM Python vs Rust performance benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--periods", type=int, default=BENCH_PERIODS)
    parser.add_argument("--reps", type=int, default=N_REPS)
    parser.add_argument("--no-rust", action="store_true", help="Skip Rust backend")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "benchmark_results.json",
    )
    args = parser.parse_args()

    print(f"ABM Performance Benchmark: {args.periods} periods x {args.reps} reps")
    print(f"Scenarios: {len(SCENARIOS)} scaling points")

    rust_available = False
    if not args.no_rust:
        try:
            import companies_house_abm._rust_abm  # noqa: F401  # type: ignore[import]

            rust_available = True
            print("Rust extension: AVAILABLE")
        except ImportError:
            print(
                "Rust extension: NOT AVAILABLE (run ./scripts/build_rust_abm.sh first)"
            )

    print()

    results = run_benchmarks(
        periods=args.periods,
        n_reps=args.reps,
        include_rust=rust_available,
    )
    print_table(results)
    save_results(results, args.output)
    print()
    print("To visualise results:")
    print(f"  cat {args.output} | python3 -m json.tool")
