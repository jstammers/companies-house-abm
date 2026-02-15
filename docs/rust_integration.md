# Rust Integration Plan

This document outlines the plan for migrating the ABM core to Rust for high-performance simulation at scale.

## Current State (Phase 1-2)

- Python implementation of agents, markets, and simulation
- Suitable for prototyping and small-scale experiments (~10K firms)
- Performance limitation: ~1 hour for 10K firms × 120 months

## Target State (Phase 3+)

- Rust core simulation engine
- Python bindings via PyO3/Maturin
- Target: 5M firms × 30M households × 120 months in ~10 hours (64 cores)

## Architecture

### Workspace Structure

```
rust/
├── Cargo.toml              # Workspace manifest
├── core/                   # Simulation engine library
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── agents/         # Agent structs and behaviours
│       ├── markets/        # Market clearing algorithms
│       ├── network/        # Graph structures (petgraph)
│       ├── scheduler.rs    # krabmaga integration
│       ├── state.rs        # EconomyState
│       └── config.rs       # Configuration
├── pyo3_bindings/          # Python bindings
│   ├── Cargo.toml
│   └── src/
│       └── lib.rs          # #[pymodule]
└── cli/                    # Optional Rust CLI
    ├── Cargo.toml
    └── src/
        └── main.rs
```

### Key Dependencies

```toml
[dependencies]
krabmaga = "0.3"           # ABM framework
petgraph = "0.6"           # Network graphs
rand = "0.8"
rand_distr = "0.4"
serde = { version = "1.0", features = ["derive"] }
pyo3 = { version = "0.20", features = ["extension-module"] }
arrow2 = "0.18"            # Zero-copy data transfer to Python
rayon = "1.8"              # Parallel iteration
```

## Agent Implementation in Rust

### Firm Agent Example

```rust
use krabmaga::engine::agent::Agent;
use krabmaga::engine::state::State;

#[derive(Clone)]
pub struct Firm {
    pub id: u64,
    pub company_number: String,
    pub sector: SICCode,
    pub region: NUTSRegion,
    pub capital: f64,
    pub debt: f64,
    pub equity: f64,
    pub inventory: f64,
    pub price: f64,
    pub wage: f64,
    pub production_plan: f64,
    pub employees: Vec<u64>,
    pub strategy: FirmStrategy,
    pub alive: bool,
}

impl Agent for Firm {
    fn step(&mut self, state: &mut dyn State) {
        let econ_state = state
            .as_any_mut()
            .downcast_mut::<EconomyState>()
            .unwrap();
        
        if !self.alive {
            return;
        }
        
        // 1. Update expectations
        self.update_expectations(econ_state);
        
        // 2. Plan production
        self.plan_production(econ_state);
        
        // 3. Set price and wage
        self.set_price(econ_state);
        self.set_wage(econ_state);
        
        // 4. Participate in markets
        econ_state.goods_market.post_supply(
            self.id,
            self.sector,
            self.price,
            self.inventory
        );
        
        // 5. Check survival
        if self.equity < 0.0 {
            self.alive = false;
        }
    }
}
```

## PyO3 Bindings

### Simulation Class

```rust
use pyo3::prelude::*;

#[pyclass]
pub struct Simulation {
    state: EconomyState,
}

#[pymethods]
impl Simulation {
    #[new]
    fn new(config_json: &str) -> PyResult<Self> {
        let config: SimConfig = serde_json::from_str(config_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid config: {}", e)
            ))?;
        Ok(Self {
            state: EconomyState::new(config),
        })
    }
    
    fn step(&mut self) -> PyResult<()> {
        self.state.step();
        Ok(())
    }
    
    fn run(&mut self, n_steps: u32) -> PyResult<()> {
        for _ in 0..n_steps {
            self.state.step();
        }
        Ok(())
    }
    
    fn get_macro_state(&self, py: Python) -> PyResult<PyObject> {
        // Return dict: {gdp, inflation, unemployment, ...}
        let dict = PyDict::new(py);
        dict.set_item("gdp", self.state.compute_gdp())?;
        dict.set_item("inflation", self.state.compute_inflation())?;
        dict.set_item("unemployment", self.state.compute_unemployment())?;
        Ok(dict.into())
    }
    
    fn get_firm_data(&self, py: Python) -> PyResult<PyObject> {
        // Return Arrow-compatible buffer for zero-copy to Polars
        // Implementation would use arrow2 to create RecordBatch
        todo!("Arrow integration")
    }
}

#[pymodule]
fn uk_econ_abm(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Simulation>()?;
    Ok(())
}
```

### Python Usage

```python
import uk_econ_abm  # Rust module compiled via Maturin
import polars as pl

# Configure simulation
config = {
    "n_firms": 100000,
    "n_households": 500000,
    "n_steps": 120,
    "random_seed": 42,
}

# Create and run simulation
sim = uk_econ_abm.Simulation(json.dumps(config))
sim.run(120)  # 120 months

# Get results
macro = sim.get_macro_state()
print(f"GDP: {macro['gdp']}")
print(f"Unemployment: {macro['unemployment']:.1%}")

# Get firm-level data (zero-copy via Arrow)
firm_data = sim.get_firm_data()
df = pl.from_arrow(firm_data)
print(df.head())
```

## Build System (Maturin)

### pyproject.toml Update

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
manifest-path = "rust/pyo3_bindings/Cargo.toml"
features = ["pyo3/extension-module"]
```

### CI Integration

GitHub Actions workflow:

```yaml
- name: Build Rust extension
  uses: PyO3/maturin-action@v1
  with:
    command: build
    args: --release --out dist

- name: Install wheel
  run: pip install dist/*.whl

- name: Test Rust extension
  run: pytest tests/test_rust_integration.py
```

## Migration Strategy

### Phase 1: Direct Translation

1. Port agent structs and behaviours 1:1 from Python to Rust
2. Implement markets and state management
3. Ensure numerical equivalence with Python version

### Phase 2: Optimization

1. Profile hot paths
2. Use `rayon` for parallel agent stepping
3. Optimize data layouts (struct-of-arrays vs. array-of-structs)
4. Consider SIMD for aggregate computations

### Phase 3: Scale-Up

1. Test with 100K agents
2. Test with 1M agents
3. Full 5M firms + 30M households

### Phase 4: Advanced Features

1. GPU acceleration for market clearing (optional)
2. Distributed simulation (MPI) for multi-node runs
3. Checkpointing and restart

## Performance Targets

| Scale | Python (est.) | Rust Target |
|---|---|---|
| 10K firms, 120 months | 1 hour | 1 minute |
| 100K firms, 120 months | 10 hours | 10 minutes |
| 1M firms, 120 months | 100 hours | 2 hours |
| 5M firms, 120 months | N/A (OOM) | 10 hours (64 cores) |

## Testing Strategy

### Validation Tests

Ensure Rust implementation matches Python:

```python
def test_numerical_equivalence():
    """Run same scenario in Python and Rust, compare outputs."""
    # Python
    py_sim = PythonSimulation(config)
    py_sim.run(10)
    py_gdp = py_sim.get_gdp()
    
    # Rust
    rust_sim = uk_econ_abm.Simulation(config)
    rust_sim.run(10)
    rust_gdp = rust_sim.get_macro_state()['gdp']
    
    # Should match within floating-point tolerance
    assert abs(py_gdp - rust_gdp) / py_gdp < 1e-6
```

### Benchmark Suite

```rust
#[bench]
fn bench_firm_step(b: &mut Bencher) {
    let mut state = EconomyState::new_test();
    b.iter(|| {
        for firm in &mut state.firms {
            firm.step(&mut state);
        }
    });
}

#[bench]
fn bench_market_clearing(b: &mut Bencher) {
    let mut state = EconomyState::new_test();
    b.iter(|| {
        state.goods_market.clear();
    });
}
```

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Rust learning curve | Start with simple agents; incremental complexity |
| PyO3 API breaking changes | Pin PyO3 version; test with multiple Python versions |
| Performance not meeting targets | Profile early; optimize incrementally; consider GPU |
| Numerical divergence from Python | Extensive validation tests; use deterministic RNG |
| Memory issues at scale | Test scaling incrementally; use memory profiling |

## Next Steps

1. **Set up Rust workspace** (cargo init)
2. **Implement minimal Firm agent** in Rust
3. **Create PyO3 bindings** for simple case
4. **Benchmark** against Python
5. **Iterate** based on performance/correctness

## References

- [krabmaga documentation](https://github.com/krABMaga/krABMaga)
- [PyO3 user guide](https://pyo3.rs/)
- [Maturin guide](https://www.maturin.rs/)
- [Arrow Rust implementation](https://docs.rs/arrow2/)
