"""Task: prepare cleaned health data for downstream analysis and ML."""

from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger

from awai.utils.data_cleaner import (
    aggregate_daily,
    aggregate_monthly,
    clean_records,
    filter_record_types,
)


def load_records_from_db(db_path: Path) -> pd.DataFrame:
    """Read the raw ``records`` table from a DuckDB database.

    Args:
        db_path: Path to the DuckDB database (created by :mod:`~awai.tasks.load_data`).

    Returns:
        Raw records :class:`~pandas.DataFrame` as stored in the database.
    """
    db_path = Path(db_path)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.query("SELECT * FROM records").to_df()
    finally:
        con.close()
    logger.info(f"Loaded {len(df):,} records from {db_path}")
    return df


def prepare_records(
    db_path: Path,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Run the full data-preparation pipeline for health records.

    Pipeline steps:

    1. Load raw records from DuckDB.
    2. Clean and normalise the DataFrame (:func:`~awai.utils.data_cleaner.clean_records`).
    3. Split into per-type DataFrames (:func:`~awai.utils.data_cleaner.filter_record_types`).
    4. Compute daily aggregations (:func:`~awai.utils.data_cleaner.aggregate_daily`).
    5. Compute monthly aggregations (:func:`~awai.utils.data_cleaner.aggregate_monthly`).

    Args:
        db_path: Path to the DuckDB database.

    Returns:
        A 3-tuple ``(records_by_type, daily, monthly)`` where each element is
        a ``dict`` mapping record-type names to :class:`~pandas.DataFrame` objects.
    """
    raw_df = load_records_from_db(db_path)
    cleaned = clean_records(raw_df)
    by_type = filter_record_types(cleaned)
    daily = aggregate_daily(by_type)
    monthly = aggregate_monthly(by_type)
    logger.info("Data preparation complete.")
    return by_type, daily, monthly
