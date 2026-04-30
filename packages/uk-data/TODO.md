# TOOD
- [ ] Fix ONSAdapter.get_observation to work with both single and multiple data points
- [ ] Refactor Adapter classes to store raw data, using `extract` method to extract data, `save` to save a dataset and `load` to load it.
- [ ] Refactor CompaniesHouseAdapter to load account filings using `stream-read-xbrl`, and use REST API for other datasets
- [ ] Refactor LandRegistryAdapter to load HPI index and price paid data
- [ ] Migrate get_series, get_entity, get_event functionality into Transformer classes, to create TimeSeries, Enity, Event objects from raw/transformed data
- [ ] Refactor fetch_x functions into workflow module
- [ ] Refactor historical adapter into workflow within companies_house_abm