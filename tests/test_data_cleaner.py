"""Tests for the data cleaning and aggregation utilities."""

import pandas as pd
import pytest

from awai.utils.data_cleaner import (
    DAILY_SUM_KEYS,
    RECORD_TYPES,
    aggregate_daily,
    aggregate_monthly,
    camel_to_snake,
    clean_records,
    filter_record_types,
    rename_columns,
)

# ---------------------------------------------------------------------------
# camel_to_snake
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_name, expected",
    [
        ("camelCase", "camel_case"),
        ("@type", "type"),
        ("startDate", "start_date"),
        ("VO2Max", "v_o2_max"),
        ("snake_case", "snake_case"),
        ("ActiveEnergyBurned", "active_energy_burned"),
    ],
)
def test_camel_to_snake(input_name: str, expected: str) -> None:
    assert camel_to_snake(input_name) == expected


# ---------------------------------------------------------------------------
# rename_columns
# ---------------------------------------------------------------------------


def test_rename_columns() -> None:
    df = pd.DataFrame(columns=["@type", "startDate", "endDate"])
    renamed = rename_columns(df)
    assert list(renamed.columns) == ["type", "start_date", "end_date"]


def test_rename_columns_does_not_mutate_original() -> None:
    df = pd.DataFrame(columns=["@type", "startDate"])
    rename_columns(df)
    assert "@type" in df.columns  # original is unchanged


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_raw_records(n: int = 5) -> pd.DataFrame:
    """Return a small synthetic raw-records DataFrame (mimics xmltodict output)."""
    rows = [
        {
            "@type": "HKQuantityTypeIdentifierActiveEnergyBurned",
            "startDate": "2024-01-01 08:00:00 +0000",
            "endDate": "2024-01-01 08:30:00 +0000",
            "creationDate": "2024-01-01 08:30:00 +0000",
            "value": str(i * 50),
            "unit": "kcal",
            "sourceName": "Apple Watch",
        }
        for i in range(1, n + 1)
    ]
    return pd.DataFrame(rows)


def _make_typed_records() -> dict[str, pd.DataFrame]:
    """Return a minimal per-type dict suitable for aggregation tests."""
    df = pd.DataFrame(
        {
            "ActiveEnergyBurned": [100.0, 200.0, 150.0],
            "Date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "Day": ["Monday", "Monday", "Tuesday"],
            "Month": ["January", "January", "January"],
        }
    )
    return {"ActiveEnergyBurned": df}


# ---------------------------------------------------------------------------
# clean_records
# ---------------------------------------------------------------------------


def test_clean_records_expected_columns() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    for col in ("type", "Date", "Day", "Month", "value", "unit", "duration"):
        assert col in cleaned.columns, f"Expected column '{col}' missing"


def test_clean_records_type_prefix_stripped() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    assert not cleaned["type"].str.startswith("HKQuantityTypeIdentifier").any()
    assert not cleaned["type"].str.startswith("HKCategoryTypeIdentifier").any()


def test_clean_records_value_is_float() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    assert pd.api.types.is_float_dtype(cleaned["value"])


def test_clean_records_duration_is_timedelta() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    assert pd.api.types.is_timedelta64_dtype(cleaned["duration"])


def test_clean_records_metadata_dropped() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    for col in ("source_name", "creation_date", "end_date"):
        assert col not in cleaned.columns


def test_clean_records_non_numeric_value_becomes_1() -> None:
    raw = _make_raw_records(1)
    raw.at[0, "value"] = "not-a-number"
    cleaned = clean_records(raw)
    assert cleaned["value"].iloc[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# filter_record_types
# ---------------------------------------------------------------------------


def test_filter_record_types_returns_dict() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    result = filter_record_types(cleaned, ["ActiveEnergyBurned"])
    assert isinstance(result, dict)
    assert "ActiveEnergyBurned" in result


def test_filter_record_types_renames_value_column() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    result = filter_record_types(cleaned, ["ActiveEnergyBurned"])
    assert "ActiveEnergyBurned" in result["ActiveEnergyBurned"].columns
    assert "value" not in result["ActiveEnergyBurned"].columns


def test_filter_record_types_all_defaults_present() -> None:
    raw = _make_raw_records()
    cleaned = clean_records(raw)
    result = filter_record_types(cleaned)
    assert set(result.keys()) == set(RECORD_TYPES)


# ---------------------------------------------------------------------------
# aggregate_daily
# ---------------------------------------------------------------------------


def test_aggregate_daily_sums_same_date() -> None:
    by_type = _make_typed_records()
    daily = aggregate_daily(by_type, keys=["ActiveEnergyBurned"])
    result = daily["ActiveEnergyBurned"]
    row_val = result.loc[result["Date"] == "2024-01-01", "ActiveEnergyBurned"]
    assert row_val.values[0] == pytest.approx(300.0)


def test_aggregate_daily_separate_dates() -> None:
    by_type = _make_typed_records()
    daily = aggregate_daily(by_type, keys=["ActiveEnergyBurned"])
    result = daily["ActiveEnergyBurned"]
    assert len(result) == 2  # two distinct dates


def test_aggregate_daily_missing_key_skipped(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    by_type: dict = {}
    with caplog.at_level(logging.WARNING):
        daily = aggregate_daily(by_type, keys=["ActiveEnergyBurned"])
    assert "ActiveEnergyBurned" not in daily


# ---------------------------------------------------------------------------
# aggregate_monthly
# ---------------------------------------------------------------------------


def test_aggregate_monthly_sums_full_month() -> None:
    by_type = _make_typed_records()
    monthly = aggregate_monthly(by_type, keys=["ActiveEnergyBurned"])
    result = monthly["ActiveEnergyBurned"]
    row_val = result.loc[result["Date"] == "2024-01", "ActiveEnergyBurned"]
    assert row_val.values[0] == pytest.approx(450.0)


def test_aggregate_monthly_one_row_per_month() -> None:
    by_type = _make_typed_records()
    monthly = aggregate_monthly(by_type, keys=["ActiveEnergyBurned"])
    result = monthly["ActiveEnergyBurned"]
    assert len(result) == 1
