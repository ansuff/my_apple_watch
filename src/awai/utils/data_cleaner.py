"""Data cleaning and aggregation utilities for Apple Watch health data."""

import re

import pandas as pd
from loguru import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Health record types that are relevant to workout-timing analysis.
RECORD_TYPES: list[str] = [
    "BodyMass",
    "ActiveEnergyBurned",
    "BasalEnergyBurned",
    "DistanceWalkingRunning",
    "StepCount",
    "AppleStandTime",
    "WalkingSpeed",
    "DistanceCycling",
    "HeartRateVariabilitySDNN",
    "RestingHeartRate",
    "WalkingHeartRateAverage",
    "VO2Max",
    "HeartRateRecoveryOneMinute",
    "PhysicalEffort",
    "SleepAnalysis",
]

#: Columns dropped during cleaning (metadata that is not useful for analysis).
COLUMNS_TO_DROP: list[str] = [
    "source_name",
    "source_version",
    "device",
    "creation_date",
    "end_date",
    "metadata_entry",
    "heart_rate_variability_metadata_list",
]

#: Record types whose daily values should be *summed* (rather than averaged).
DAILY_SUM_KEYS: list[str] = [
    "BasalEnergyBurned",
    "ActiveEnergyBurned",
    "DistanceWalkingRunning",
    "StepCount",
    "AppleStandTime",
    "DistanceCycling",
    "PhysicalEffort",
]

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def camel_to_snake(name: str) -> str:
    """Convert a camelCase or ``@camelCase`` column name to ``snake_case``.

    Args:
        name: The original column name (may start with ``@``).

    Returns:
        The snake_case equivalent.

    Examples:
        >>> camel_to_snake("startDate")
        'start_date'
        >>> camel_to_snake("@type")
        'type'
    """
    name = re.sub("@", "", name)
    name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return name


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename all DataFrame columns from camelCase / ``@camelCase`` to snake_case.

    Args:
        df: Input DataFrame.

    Returns:
        A copy of *df* with renamed columns.
    """
    df = df.copy()
    df.columns = [camel_to_snake(col) for col in df.columns]
    return df


# ---------------------------------------------------------------------------
# Records cleaning
# ---------------------------------------------------------------------------


def clean_records(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and transform the raw health records DataFrame.

    Steps performed:

    1. Rename columns to ``snake_case``.
    2. Parse ``start_date`` / ``end_date`` and compute ``duration``.
    3. Drop metadata columns (see :data:`COLUMNS_TO_DROP`).
    4. Add ``Day``, ``Date``, and ``Month`` helper columns from ``start_date``.
    5. Coerce ``value`` to :class:`float` (fill non-numeric rows with ``1.0``).
    6. Strip ``HKQuantityTypeIdentifier`` / ``HKCategoryTypeIdentifier`` prefixes
       from the ``type`` column.

    Args:
        df: Raw records DataFrame as produced by
            :func:`~awai.utils.xml_parser.extract_records`.

    Returns:
        Cleaned DataFrame ready for further analysis.
    """
    df = rename_columns(df)

    # Parse dates and compute duration before any columns are dropped.
    for col in ("start_date", "end_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    if "start_date" in df.columns and "end_date" in df.columns:
        df["duration"] = df["end_date"] - df["start_date"]

    # Drop metadata columns that are present in this export.
    existing_drops = [c for c in COLUMNS_TO_DROP if c in df.columns]
    df = df.drop(columns=existing_drops)

    # Add calendar helper columns derived from start_date.
    if "start_date" in df.columns:
        df["Day"] = df["start_date"].dt.strftime("%A")
        df["Date"] = df["start_date"].dt.strftime("%Y-%m-%d")
        df["Month"] = df["start_date"].dt.strftime("%B")

    # Coerce value to float; records that have no numeric value (e.g. presence
    # indicators such as SleepAnalysis) are assigned 1.0 so they count as one
    # occurrence and can still be summed/aggregated meaningfully.
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(1.0).astype(float)

    # Shorten Apple's verbose type identifiers.
    if "type" in df.columns:
        df["type"] = (
            df["type"]
            .str.replace("HKQuantityTypeIdentifier", "", regex=False)
            .str.replace("HKCategoryTypeIdentifier", "", regex=False)
        )

    # Reorder to a canonical column order; any extra columns go at the end.
    desired = ["type", "Date", "Day", "Month", "value", "unit", "duration"]
    available = [c for c in desired if c in df.columns]
    remaining = [c for c in df.columns if c not in desired]
    df = df[available + remaining]

    logger.info(f"Cleaned records: {len(df):,} rows, {len(df.columns)} columns")
    return df


# ---------------------------------------------------------------------------
# Filtering & aggregation
# ---------------------------------------------------------------------------


def filter_record_types(
    df: pd.DataFrame,
    record_types: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Split a cleaned records DataFrame into one sub-DataFrame per health type.

    Args:
        df: Cleaned records DataFrame (output of :func:`clean_records`).
        record_types: Types to extract.  Defaults to :data:`RECORD_TYPES`.

    Returns:
        A ``dict`` mapping each record type name to a filtered and renamed
        DataFrame where the ``value`` column is renamed to the type name.
    """
    if record_types is None:
        record_types = RECORD_TYPES

    result: dict[str, pd.DataFrame] = {}
    for rt in record_types:
        mask = df["type"].str.contains(rt, regex=False)
        subset = df.loc[mask].rename(columns={"value": rt}).sort_values("Date")
        result[rt] = subset

    logger.info(f"Filtered into {len(result)} record type groups")
    return result


def aggregate_daily(
    records_by_type: dict[str, pd.DataFrame],
    keys: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Aggregate per-type DataFrames to *daily* totals (sum).

    Args:
        records_by_type: Output of :func:`filter_record_types`.
        keys: Types to aggregate.  Defaults to :data:`DAILY_SUM_KEYS`.

    Returns:
        A ``dict`` mapping each type name to a daily-aggregated DataFrame.
    """
    if keys is None:
        keys = DAILY_SUM_KEYS

    daily: dict[str, pd.DataFrame] = {}
    for key in keys:
        if key not in records_by_type:
            logger.warning(f"Key '{key}' not found in records – skipping daily aggregation")
            continue
        df = records_by_type[key]
        daily[key] = (
            df.groupby("Date")
            .agg({key: "sum", "Day": lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]})
            .reset_index()
        )

    return daily


def aggregate_monthly(
    records_by_type: dict[str, pd.DataFrame],
    keys: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Aggregate per-type DataFrames to *monthly* totals (sum).

    Args:
        records_by_type: Output of :func:`filter_record_types`.
        keys: Types to aggregate.  Defaults to :data:`DAILY_SUM_KEYS`.

    Returns:
        A ``dict`` mapping each type name to a monthly-aggregated DataFrame.
    """
    if keys is None:
        keys = DAILY_SUM_KEYS

    monthly: dict[str, pd.DataFrame] = {}
    for key in keys:
        if key not in records_by_type:
            logger.warning(f"Key '{key}' not found in records – skipping monthly aggregation")
            continue
        df = records_by_type[key]
        monthly[key] = (
            df.groupby(df["Date"].str[:-3])
            .agg({key: "sum", "Month": lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]})
            .reset_index()
        )

    return monthly
