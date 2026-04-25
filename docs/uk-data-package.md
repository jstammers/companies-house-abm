# UK Data Package

The `uk-data` package (`packages/uk-data/src/uk_data/`) provides a canonical
interface over multiple UK public data sources.

It standardizes source-specific responses into shared model types:

- `TimeSeries`
- `Entity`
- `Event`

The package is intended to be used directly by downstream applications and by
other workspace packages such as `companies-house-abm`.

## Package Layout

```
packages/uk-data/
├── src/uk_data/
│   ├── __init__.py
│   ├── client.py            # UKDataClient facade
│   ├── registry.py          # Canonical concept registry
│   ├── cli.py               # ukd Typer CLI
│   ├── _http.py             # Shared urllib helpers + caching/retry
│   ├── api/                 # Companies House API client modules
│   ├── adapters/            # Source adapters
│   ├── models/              # Canonical data models
│   └── storage/             # Raw/canonical storage utilities
└── tests/
```

## Source Adapters

`uk-data` currently includes adapters for:

- Office for National Statistics (`ons`)
- Bank of England (`boe`)
- HMRC (`hmrc`)
- Companies House (`companies_house`)
- Land Registry (`land_registry`)
- EPC (`epc`)

## API and Module References

- Companies House API client reference: `uk-data-api.md`
- Full package reference: `uk-data-reference.md`
