# Configuration Directory

This directory contains configuration files for the agent-based model.

## Files

- **`model_parameters.yml`**: Main configuration file containing all model parameters including:
  - Simulation settings (periods, time steps, seeds)
  - Agent populations and initialization
  - Behavioral parameters
  - Market mechanisms
  - Policy rules
  - Network structure
  - Shocks and scenarios
  - Output configuration
  - Validation targets

## Usage

Load the configuration in Python:

```python
import yaml
from pathlib import Path

config_path = Path("config/model_parameters.yml")
with config_path.open() as f:
    config = yaml.safe_load(f)

# Access parameters
n_firms = config['agents']['firms']['sample_size']
markup = config['behavior']['firms']['price_markup']
```

Or pass the path directly to the model:

```python
from companies_house_abm.abm import UKEconomyModel

model = UKEconomyModel(config_path="config/model_parameters.yml")
```

## Customization

To customize parameters for different experiments:

1. Copy `model_parameters.yml` to a new file (e.g., `experiment1.yml`)
2. Modify the parameters as needed
3. Load the custom configuration:

```python
model = UKEconomyModel(config_path="config/experiment1.yml")
```

Alternatively, you can override specific parameters programmatically:

```python
import yaml

with open("config/model_parameters.yml") as f:
    config = yaml.safe_load(f)

# Override specific parameters
config['agents']['firms']['sample_size'] = 10000
config['simulation']['periods'] = 200

# Use the modified config
model = UKEconomyModel(config=config)
```
