"""Tests for shared time-series date-window utilities."""

from __future__ import annotations

import pytest

from uk_data.utils.timeseries import filter_observations_by_date_window


def test_filter_observations_by_date_window_inclusive_bounds() -> None:
    observations = [
        {"date": "2023-12-31", "value": 1.0},
        {"date": "2024-01-01", "value": 2.0},
        {"date": "2024-03-31", "value": 3.0},
        {"date": "2024-04-01", "value": 4.0},
    ]

    filtered = filter_observations_by_date_window(
        observations,
        start_date="2024-01-01",
        end_date="2024-03-31",
    )

    assert [obs["date"] for obs in filtered] == ["2024-01-01", "2024-03-31"]


@pytest.mark.parametrize("field", ["start_date", "end_date"])
def test_filter_observations_by_date_window_invalid_date(field: str) -> None:
    kwargs = {"start_date": "2024-01-01", "end_date": "2024-03-31"}
    kwargs[field] = "not-a-date"

    with pytest.raises(ValueError, match=field):
        filter_observations_by_date_window(
            [{"date": "2024-01-01", "value": 1.0}],
            **kwargs,
        )


def test_filter_observations_by_date_window_inverted_range_raises() -> None:
    with pytest.raises(ValueError, match=r"start_date.*end_date"):
        filter_observations_by_date_window(
            [{"date": "2024-01-01", "value": 1.0}],
            start_date="2024-04-01",
            end_date="2024-01-01",
        )
