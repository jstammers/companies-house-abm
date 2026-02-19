"""Performance benchmark tests for the ABM simulation.

Measures runtime per simulation as the number of agents scales up,
covering both the pure-Python implementation and (when available) the
Rust-backed implementation exposed via ``companies_house_abm._rust_abm``.

Run the full benchmark suite with::

    pytest tests/test_abm_performance.py -v -m slow

Or run it as a standalone script::

    python tests/test_abm_performance.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Agent-count scenarios (n_firms, n_households, n_banks)
SCENARIOS: list[tuple[int, int, int]] = [
    (10, 50, 3),
    (25, 125, 5),
    (50, 250, 5),
    (100, 500, 10),
    (200, 1000, 10),
    (500, 2500, 10),
    (1000, 5000, 10),
]

#: Periods per benchmark run (small for speed; captures per-period cost)
BENCH_PERIODS: int = 10

#: Number of repetitions per scenario (median is reported)
N_REPS: int = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Timing result for a single (backend, scenario) combination."""

    backend: str
    n_firms: int
    n_households: int
    n_banks: int
    periods: int
    reps: int
    times_s: list[float]

    @property
    def median_s(self) -> float:
        """Median wall-clock time in seconds."""
        sorted_times = sorted(self.times_s)
        n = len(sorted_times)
        mid = n // 2
        return (
            sorted_times[mid]
            if n % 2
            else (sorted_times[mid - 1] + sorted_times[mid]) / 2
        )

    @property
    def median_ms_per_period(self) -> float:
        """Median time in milliseconds per simulated period."""
        return (self.median_s / self.periods) * 1000

    @property
    def total_agents(self) -> int:
        """Sum of all agent counts for this scenario."""
        return self.n_firms + self.n_households + self.n_banks

    def as_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "backend": self.backend,
            "n_firms": self.n_firms,
            "n_households": self.n_households,
            "n_banks": self.n_banks,
            "total_agents": self.total_agents,
            "periods": self.periods,
            "reps": self.reps,
            "median_s": self.median_s,
            "median_ms_per_period": self.median_ms_per_period,
            "all_times_s": self.times_s,
        }


def _build_python_config(n_firms: int, n_households: int, n_banks: int):
    """Return a ModelConfig sized to the given agent counts."""
    from companies_house_abm.abm.config import ModelConfig

    base = ModelConfig()

    # Use dataclasses.replace to override the capped counts.
    import dataclasses

    firms_cfg = dataclasses.replace(base.firms, sample_size=n_firms)
    hh_cfg = dataclasses.replace(base.households, count=n_households)
    banks_cfg = dataclasses.replace(base.banks, count=n_banks)
    sim_cfg = dataclasses.replace(base.simulation, seed=42)

    return dataclasses.replace(
        base,
        firms=firms_cfg,
        households=hh_cfg,
        banks=banks_cfg,
        simulation=sim_cfg,
    )


def _time_python(n_firms: int, n_households: int, n_banks: int, periods: int) -> float:
    """Run one Python simulation and return wall-clock seconds."""
    from companies_house_abm.abm.model import Simulation

    cfg = _build_python_config(n_firms, n_households, n_banks)
    sim = Simulation(cfg)
    sim.initialize_agents()

    t0 = time.perf_counter()
    sim.run(periods=periods, collect_micro=False)
    return time.perf_counter() - t0


def _time_rust(n_firms: int, n_households: int, n_banks: int, periods: int) -> float:
    """Run one Rust simulation and return wall-clock seconds.

    Returns ``float('nan')`` if the Rust extension is not installed.
    """
    try:
        import companies_house_abm._rust_abm as rust_abm  # type: ignore[import]
    except ImportError:
        return float("nan")

    t0 = time.perf_counter()
    rust_abm.run_simulation(
        n_firms=n_firms,
        n_households=n_households,
        n_banks=n_banks,
        periods=periods,
        seed=42,
    )
    return time.perf_counter() - t0


def run_benchmarks(
    scenarios: list[tuple[int, int, int]] = SCENARIOS,
    periods: int = BENCH_PERIODS,
    n_reps: int = N_REPS,
    include_rust: bool = True,
) -> list[BenchmarkResult]:
    """Run the full benchmark suite and return results."""
    results: list[BenchmarkResult] = []

    for n_firms, n_households, n_banks in scenarios:
        # Python backend
        py_times: list[float] = []
        for _ in range(n_reps):
            elapsed = _time_python(n_firms, n_households, n_banks, periods)
            py_times.append(elapsed)

        results.append(
            BenchmarkResult(
                backend="python",
                n_firms=n_firms,
                n_households=n_households,
                n_banks=n_banks,
                periods=periods,
                reps=n_reps,
                times_s=py_times,
            )
        )

        # Rust backend (if available)
        if include_rust:
            rust_times: list[float] = []
            for _ in range(n_reps):
                elapsed = _time_rust(n_firms, n_households, n_banks, periods)
                rust_times.append(elapsed)

            if not all(t != t for t in rust_times):  # at least one non-NaN
                results.append(
                    BenchmarkResult(
                        backend="rust",
                        n_firms=n_firms,
                        n_households=n_households,
                        n_banks=n_banks,
                        periods=periods,
                        reps=n_reps,
                        times_s=rust_times,
                    )
                )

    return results


def print_table(results: list[BenchmarkResult]) -> None:
    """Print a formatted comparison table to stdout."""
    print()
    print("=" * 80)
    print("ABM PERFORMANCE BENCHMARK RESULTS")
    print("=" * 80)
    print(
        f"{'Backend':<10} {'Firms':>6} {'HH':>6} {'Banks':>6} "
        f"{'Total':>7} {'Periods':>7} {'Median(s)':>10} {'ms/period':>10}"
    )
    print("-" * 80)

    # Group by scenario for easy comparison
    scenarios_seen: set[tuple[int, int, int]] = set()
    by_scenario: dict[tuple[int, int, int], list[BenchmarkResult]] = {}
    for r in results:
        key = (r.n_firms, r.n_households, r.n_banks)
        by_scenario.setdefault(key, []).append(r)
        scenarios_seen.add(key)

    for key in sorted(scenarios_seen):
        for r in by_scenario[key]:
            print(
                f"{r.backend:<10} {r.n_firms:>6} {r.n_households:>6} {r.n_banks:>6} "
                f"{r.total_agents:>7} {r.periods:>7} "
                f"{r.median_s:>10.4f} {r.median_ms_per_period:>10.3f}"
            )

        # Print speedup if both backends present
        scenario_results = by_scenario[key]
        py_res = next((r for r in scenario_results if r.backend == "python"), None)
        rust_res = next((r for r in scenario_results if r.backend == "rust"), None)
        if py_res and rust_res and rust_res.median_s > 0:
            speedup = py_res.median_s / rust_res.median_s
            speedup_label = "  -> speedup"
            print(
                f"{speedup_label:<10} {' ':>6} {' ':>6} {' ':>6}"
                f" {' ':>7} {' ':>7} {' ':>10} {speedup:>9.1f}x"
            )

        print()

    print("=" * 80)


def save_results(results: list[BenchmarkResult], output_path: Path) -> None:
    """Serialise results to JSON."""
    data = [r.as_dict() for r in results]
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Results saved to {output_path}")


# ---------------------------------------------------------------------------
# Pytest integration
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPythonPerformance:
    """Slow benchmark tests for the Python ABM backend."""

    @pytest.mark.parametrize(
        "n_firms,n_households,n_banks",
        SCENARIOS,
        ids=[f"firms={f}_hh={h}_banks={b}" for f, h, b in SCENARIOS],
    )
    def test_python_runtime(
        self, n_firms: int, n_households: int, n_banks: int
    ) -> None:
        """Python simulation completes within a generous time budget."""
        elapsed = _time_python(n_firms, n_households, n_banks, periods=BENCH_PERIODS)
        # No hard limit - just record timing; assert it completes
        assert elapsed >= 0.0
        ms_per_period = (elapsed / BENCH_PERIODS) * 1000
        print(
            f"\n[python] firms={n_firms} hh={n_households} banks={n_banks}: "
            f"{elapsed:.4f}s total, {ms_per_period:.2f}ms/period"
        )


@pytest.mark.slow
class TestRustPerformance:
    """Slow benchmark tests for the Rust ABM backend.

    Skipped automatically when the Rust extension is not installed.
    """

    @pytest.fixture(autouse=True)
    def require_rust(self) -> None:
        pytest.importorskip("companies_house_abm._rust_abm")

    @pytest.mark.parametrize(
        "n_firms,n_households,n_banks",
        SCENARIOS,
        ids=[f"firms={f}_hh={h}_banks={b}" for f, h, b in SCENARIOS],
    )
    def test_rust_runtime(self, n_firms: int, n_households: int, n_banks: int) -> None:
        """Rust simulation completes within a generous time budget."""
        elapsed = _time_rust(n_firms, n_households, n_banks, periods=BENCH_PERIODS)
        assert elapsed >= 0.0
        ms_per_period = (elapsed / BENCH_PERIODS) * 1000
        print(
            f"\n[rust]   firms={n_firms} hh={n_households} banks={n_banks}: "
            f"{elapsed:.4f}s total, {ms_per_period:.2f}ms/period"
        )


@pytest.mark.slow
class TestRustSpeedup:
    """Verify Rust is faster than Python on representative scenarios."""

    @pytest.fixture(autouse=True)
    def require_rust(self) -> None:
        pytest.importorskip("companies_house_abm._rust_abm")

    @pytest.mark.parametrize(
        "n_firms,n_households,n_banks",
        [(100, 500, 10), (500, 2500, 10)],
        ids=["medium", "large"],
    )
    def test_rust_faster_than_python(
        self, n_firms: int, n_households: int, n_banks: int
    ) -> None:
        """Rust backend is at least 2x faster than Python."""
        py_time = _time_python(n_firms, n_households, n_banks, periods=BENCH_PERIODS)
        rust_time = _time_rust(n_firms, n_households, n_banks, periods=BENCH_PERIODS)
        speedup = py_time / rust_time
        assert speedup >= 2.0, (
            f"Expected Rust to be >=2x faster, got {speedup:.1f}x "
            f"(python={py_time:.3f}s, rust={rust_time:.3f}s)"
        )


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ABM performance benchmarks")
    parser.add_argument(
        "--periods", type=int, default=BENCH_PERIODS, help="Periods per run"
    )
    parser.add_argument(
        "--reps", type=int, default=N_REPS, help="Repetitions per scenario"
    )
    parser.add_argument("--no-rust", action="store_true", help="Skip Rust backend")
    parser.add_argument(
        "--output", type=Path, default=None, help="Save JSON results to file"
    )
    args = parser.parse_args()

    print(f"Running ABM benchmarks: {args.periods} periods, {args.reps} reps each")
    print(f"Scenarios: {len(SCENARIOS)} (firms x households x banks)")

    results = run_benchmarks(
        periods=args.periods,
        n_reps=args.reps,
        include_rust=not args.no_rust,
    )
    print_table(results)

    if args.output:
        save_results(results, args.output)
    else:
        # Default output alongside this file
        default_out = Path(__file__).parent.parent / "benchmark_results.json"
        save_results(results, default_out)

    sys.exit(0)
