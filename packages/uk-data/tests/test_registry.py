"""Tests for manifest-driven concept registry wiring."""

from __future__ import annotations

from uk_data.adapters.ons_manifest import ONS_CONCEPT_MAP, ONS_SERIES_MANIFEST
from uk_data.registry import CONCEPT_REGISTRY


def test_registry_contains_manifest_defined_ons_concepts() -> None:
    for concept, series_id in ONS_CONCEPT_MAP.items():
        assert CONCEPT_REGISTRY[concept]["ons"] == series_id


def test_registry_and_ons_manifest_have_no_missing_or_duplicate_ons_concepts() -> None:
    manifest_concepts = {entry.concept for entry in ONS_SERIES_MANIFEST.values()}
    registry_concepts = {
        concept for concept, mapping in CONCEPT_REGISTRY.items() if mapping.get("ons") is not None
    }
    assert registry_concepts == manifest_concepts
