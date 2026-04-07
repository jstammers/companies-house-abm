/*!
# `_rust_abm` — Rust-backed ABM simulation core

This module exposes a compiled Rust implementation of the Companies House
agent-based model to Python via [PyO3](https://pyo3.rs).

The Rust core uses [krABMaga](https://github.com/krABMaga/krABMaga) (krabmaga) as
the ABM scheduling framework.  All agent logic and market-clearing algorithms
are implemented in Rust, matching the behaviour of the pure-Python
`companies_house_abm.abm` module exactly.

## Quick start

```python
from companies_house_abm import _rust_abm

records = _rust_abm.run_simulation(
    n_firms=100,
    n_households=500,
    n_banks=10,
    periods=50,
    seed=42,
)
for r in records:
    print(r.period, r.gdp, r.inflation, r.unemployment_rate)
```
*/

mod agents;
mod config;
mod markets;
mod state;

use config::Config;
use krabmaga::engine::schedule::Schedule;
use krabmaga::engine::state::State;
use pyo3::prelude::*;
use state::EconomyState;

// ─────────────────────────────────────────────────────────────────────────────
// Python-visible period record
// ─────────────────────────────────────────────────────────────────────────────

/// Aggregate statistics for a single simulation period.
///
/// All fields are read-only from Python.
#[pyclass(get_all)]
#[derive(Clone, Debug)]
pub struct PyPeriodRecord {
    pub period: u64,
    pub gdp: f64,
    pub inflation: f64,
    pub unemployment_rate: f64,
    pub average_wage: f64,
    pub policy_rate: f64,
    pub government_deficit: f64,
    pub government_debt: f64,
    pub total_lending: f64,
    pub firm_bankruptcies: usize,
    pub total_employment: usize,
}

#[pymethods]
impl PyPeriodRecord {
    fn __repr__(&self) -> String {
        format!(
            "PyPeriodRecord(period={}, gdp={:.2}, inflation={:.4}, unemployment_rate={:.4})",
            self.period, self.gdp, self.inflation, self.unemployment_rate
        )
    }

    /// Convert to a plain Python dict for easy interop with pandas / polars.
    fn to_dict(&self) -> std::collections::HashMap<String, f64> {
        let mut m = std::collections::HashMap::new();
        m.insert("period".to_string(), self.period as f64);
        m.insert("gdp".to_string(), self.gdp);
        m.insert("inflation".to_string(), self.inflation);
        m.insert("unemployment_rate".to_string(), self.unemployment_rate);
        m.insert("average_wage".to_string(), self.average_wage);
        m.insert("policy_rate".to_string(), self.policy_rate);
        m.insert("government_deficit".to_string(), self.government_deficit);
        m.insert("government_debt".to_string(), self.government_debt);
        m.insert("total_lending".to_string(), self.total_lending);
        m.insert(
            "firm_bankruptcies".to_string(),
            self.firm_bankruptcies as f64,
        );
        m.insert("total_employment".to_string(), self.total_employment as f64);
        m
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main simulation entry point
// ─────────────────────────────────────────────────────────────────────────────

/// Run a full economy simulation and return per-period aggregate statistics.
///
/// This function runs the complete krABMaga-scheduled simulation loop in Rust,
/// with no Python overhead during execution.
///
/// Args:
///     n_firms: Number of firm agents to create.
///     n_households: Number of household agents to create.
///     n_banks: Number of bank agents to create.
///     periods: Number of simulation periods to run.
///     seed: Random seed for reproducibility.
///
/// Returns:
///     A list of :class:`PyPeriodRecord` objects, one per period.
#[pyfunction]
#[pyo3(signature = (n_firms=100, n_households=500, n_banks=10, periods=50, seed=42))]
fn run_simulation(
    n_firms: usize,
    n_households: usize,
    n_banks: usize,
    periods: usize,
    seed: u64,
) -> PyResult<Vec<PyPeriodRecord>> {
    let config = Config::default();
    let mut state = EconomyState::new(n_firms, n_households, n_banks, seed, config);
    let mut schedule = Schedule::new();

    // Initialise agent schedule (calls EconomyState::init)
    state.init(&mut schedule);

    // Run the simulation for the requested number of periods
    for _ in 0..periods {
        schedule.step(&mut state);
    }

    // Convert internal records to Python-visible structs
    let py_records: Vec<PyPeriodRecord> = state
        .records
        .into_iter()
        .map(|r| PyPeriodRecord {
            period: r.period,
            gdp: r.gdp,
            inflation: r.inflation,
            unemployment_rate: r.unemployment_rate,
            average_wage: r.average_wage,
            policy_rate: r.policy_rate,
            government_deficit: r.government_deficit,
            government_debt: r.government_debt,
            total_lending: r.total_lending,
            firm_bankruptcies: r.firm_bankruptcies,
            total_employment: r.total_employment,
        })
        .collect();

    Ok(py_records)
}

// ─────────────────────────────────────────────────────────────────────────────
// Module definition
// ─────────────────────────────────────────────────────────────────────────────

/// Rust-backed ABM simulation core for Companies House data.
#[pymodule]
fn _rust_abm(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPeriodRecord>()?;
    m.add_function(wrap_pyfunction!(run_simulation, m)?)?;
    Ok(())
}
