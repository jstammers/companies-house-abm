"""Unit tests for UKDataClient — list_sources, get_series, list_entities, list_events."""  # noqa: E501

from __future__ import annotations

import numpy as np
import pytest

from uk_data import EntityTypeInfo, EventTypeInfo, SourceInfo, UKDataClient


class TestUKDataClientListSources:
    def test_returns_list_of_source_info(self) -> None:
        client = UKDataClient()
        sources = client.list_sources()
        assert isinstance(sources, list)
        assert all(isinstance(s, SourceInfo) for s in sources)

    def test_all_registered_adapters_present(self) -> None:
        client = UKDataClient()
        names = {s.name for s in client.list_sources()}
        expected = {
            "ons",
            "boe",
            "hmrc",
            "land_registry",
            "companies_house",
            "epc",
        }
        assert names == expected

    def test_source_info_has_correct_structure(self) -> None:
        client = UKDataClient()
        for src in client.list_sources():
            assert isinstance(src.name, str)
            assert isinstance(src.series, list)
            assert all(isinstance(sid, str) for sid in src.series)

    def test_ons_source_has_series(self) -> None:
        client = UKDataClient()
        ons = next(s for s in client.list_sources() if s.name == "ons")
        assert len(ons.series) > 0
        assert "ABMI" in ons.series

    def test_boe_source_has_series(self) -> None:
        client = UKDataClient()
        boe = next(s for s in client.list_sources() if s.name == "boe")
        assert "IUMABEDR" in boe.series

    def test_hmrc_source_has_series(self) -> None:
        client = UKDataClient()
        hmrc = next(s for s in client.list_sources() if s.name == "hmrc")
        assert "corporation_tax_2024" in hmrc.series

    def test_land_registry_source_has_series(self) -> None:
        client = UKDataClient()
        lr = next(s for s in client.list_sources() if s.name == "land_registry")
        assert "uk_hpi_average" in lr.series

    def test_event_only_adapters_have_no_series(self) -> None:
        """companies_house and epc are event-only; their series list is empty."""
        client = UKDataClient()
        sources_by_name = {s.name: s for s in client.list_sources()}
        assert sources_by_name["companies_house"].series == []
        assert sources_by_name["epc"].series == []

    def test_list_sources_consistent_with_adapters_dict(self) -> None:
        """list_sources() must exactly mirror the adapters registered in __init__."""
        client = UKDataClient()
        source_names = [s.name for s in client.list_sources()]
        assert source_names == list(client.adapters.keys())

    def test_source_info_repr_contains_name(self) -> None:
        src = SourceInfo(name="test_source", series=["A", "B"])
        assert "test_source" in repr(src)


class TestUKDataClientGetSeries:
    def test_unknown_concept_raises_value_error(self) -> None:
        client = UKDataClient()
        with pytest.raises(ValueError, match="Unknown concept"):
            client.get_series("nonexistent_concept_xyz")

    def test_known_concept_wrong_source_raises(self) -> None:
        client = UKDataClient()
        # gdp is available via ons, not hmrc
        with pytest.raises(ValueError):
            client.get_series("gdp", source="hmrc")

    def test_get_series_forwards_start_and_end_dates(self) -> None:
        client = UKDataClient()
        calls: list[dict[str, object]] = []

        class _ResolverStub:
            def resolve_series(self, concept: str, **kwargs: object) -> object:
                calls.append({"concept": concept, **kwargs})
                return object()

        client.resolver = _ResolverStub()  # type: ignore[assignment]

        client.get_series(
            "gdp",
            source="ons",
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        assert calls == [
            {
                "concept": "gdp",
                "source": "ons",
                "limit": 20,
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
            }
        ]

    def test_get_series_limit_only_behavior_unchanged(self) -> None:
        client = UKDataClient()
        calls: list[dict[str, object]] = []

        class _ResolverStub:
            def resolve_series(self, concept: str, **kwargs: object) -> object:
                calls.append({"concept": concept, **kwargs})
                return object()

        client.resolver = _ResolverStub()  # type: ignore[assignment]

        client.get_series("gdp", source="ons", limit=7)

        assert calls == [{"concept": "gdp", "source": "ons", "limit": 7}]

    def test_get_series_window_and_limit_together_forwarded(self) -> None:
        client = UKDataClient()
        calls: list[dict[str, object]] = []

        class _ResolverStub:
            def resolve_series(self, concept: str, **kwargs: object) -> object:
                calls.append({"concept": concept, **kwargs})
                return object()

        client.resolver = _ResolverStub()  # type: ignore[assignment]

        client.get_series(
            "gdp",
            source="ons",
            start_date="2024-01-01",
            end_date="2024-03-31",
            limit=3,
        )

        assert calls == [
            {
                "concept": "gdp",
                "source": "ons",
                "limit": 3,
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
            }
        ]


class TestCliGetSeriesCommand:
    def test_get_series_cmd_forwards_start_and_end_dates(self, monkeypatch) -> None:
        from uk_data import cli

        class _ClientStub:
            def __init__(self) -> None:
                self.captured: dict[str, object] = {}

            def get_series(self, concept: str, **kwargs: object):
                self.captured = {"concept": concept, **kwargs}
                return type(
                    "_TS",
                    (),
                    {
                        "source": "ons",
                        "series_id": concept,
                        "latest_value": 1.0,
                        "timestamps": np.array([np.datetime64("2024-01-01")]),
                        "values": np.array([1.0]),
                    },
                )()

        stub = _ClientStub()
        monkeypatch.setattr(cli, "UKDataClient", lambda: stub)

        cli.get_series_cmd(
            concept="gdp",
            source="ons",
            limit=5,
            start_date="2024-01-01",
            end_date="2024-03-31",
            data_path=None,
            output="json",
        )

        assert stub.captured == {
            "concept": "gdp",
            "source": "ons",
            "limit": 5,
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
        }

    def test_get_series_cmd_limit_only_unchanged(self, monkeypatch) -> None:
        from uk_data import cli

        class _ClientStub:
            def __init__(self) -> None:
                self.captured: dict[str, object] = {}

            def get_series(self, concept: str, **kwargs: object):
                self.captured = {"concept": concept, **kwargs}
                return type(
                    "_TS",
                    (),
                    {
                        "source": "ons",
                        "series_id": concept,
                        "latest_value": 1.0,
                        "timestamps": np.array([np.datetime64("2024-01-01")]),
                        "values": np.array([1.0]),
                    },
                )()

        stub = _ClientStub()
        monkeypatch.setattr(cli, "UKDataClient", lambda: stub)

        cli.get_series_cmd(
            concept="gdp",
            source="ons",
            limit=7,
            data_path=None,
            output="json",
        )

        assert stub.captured == {"concept": "gdp", "source": "ons", "limit": 7}


class TestUKDataClientListEntities:
    def test_returns_list_of_entity_type_info(self) -> None:
        client = UKDataClient()
        entities = client.list_entities()
        assert isinstance(entities, list)
        assert all(isinstance(e, EntityTypeInfo) for e in entities)

    def test_only_companies_house_has_entities(self) -> None:
        """Of the six registered adapters only companies_house exposes entities."""
        client = UKDataClient()
        sources = {e.source for e in client.list_entities()}
        assert sources == {"companies_house"}

    def test_companies_house_entity_types(self) -> None:
        client = UKDataClient()
        ch = next(e for e in client.list_entities() if e.source == "companies_house")
        assert "company" in ch.entity_types

    def test_entity_type_info_structure(self) -> None:
        client = UKDataClient()
        for info in client.list_entities():
            assert isinstance(info.source, str) and info.source
            assert isinstance(info.entity_types, list)
            assert all(isinstance(t, str) for t in info.entity_types)
            assert len(info.entity_types) > 0

    def test_entity_type_info_repr_contains_source(self) -> None:
        info = EntityTypeInfo(source="companies_house", entity_types=["company"])
        assert "companies_house" in repr(info)

    def test_no_entity_type_info_for_series_only_adapters(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_entities()}
        for series_only in ("ons", "boe", "hmrc"):
            assert series_only not in sources


class TestUKDataClientListEvents:
    def test_returns_list_of_event_type_info(self) -> None:
        client = UKDataClient()
        events = client.list_events()
        assert isinstance(events, list)
        assert all(isinstance(e, EventTypeInfo) for e in events)

    def test_expected_sources_present(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_events()}
        assert {"companies_house", "land_registry", "epc"} == sources

    def test_companies_house_event_types(self) -> None:
        client = UKDataClient()
        ch = next(e for e in client.list_events() if e.source == "companies_house")
        assert "filing" in ch.event_types

    def test_land_registry_event_types(self) -> None:
        client = UKDataClient()
        lr = next(e for e in client.list_events() if e.source == "land_registry")
        assert "property_transaction" in lr.event_types

    def test_epc_event_types(self) -> None:
        client = UKDataClient()
        epc = next(e for e in client.list_events() if e.source == "epc")
        assert "epc_lodgement" in epc.event_types

    def test_event_type_info_structure(self) -> None:
        client = UKDataClient()
        for info in client.list_events():
            assert isinstance(info.source, str) and info.source
            assert isinstance(info.event_types, list)
            assert all(isinstance(t, str) for t in info.event_types)
            assert len(info.event_types) > 0

    def test_event_type_info_repr_contains_source(self) -> None:
        info = EventTypeInfo(
            source="land_registry", event_types=["property_transaction"]
        )
        assert "land_registry" in repr(info)

    def test_no_event_type_info_for_series_only_adapters(self) -> None:
        client = UKDataClient()
        sources = {e.source for e in client.list_events()}
        for series_only in ("ons", "boe", "hmrc"):
            assert series_only not in sources
