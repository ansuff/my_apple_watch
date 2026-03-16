"""Utilities for parsing Apple Watch XML health data exports."""

from pathlib import Path

import pandas as pd
import xmltodict
from loguru import logger


def load_xml_export(xml_path: Path) -> dict:
    """Load an Apple Watch health export XML file and return the parsed dict.

    Args:
        xml_path: Path to the Apple Watch ``export.xml`` file.

    Returns:
        A nested dictionary produced by ``xmltodict.parse``.
    """
    xml_path = Path(xml_path)
    logger.info(f"Loading XML export from {xml_path}")
    with open(xml_path, "r", encoding="utf-8") as fh:
        return xmltodict.parse(fh.read())


def _ensure_list(value: dict | list) -> list:
    """Ensure *value* is a list, wrapping a single dict in one if necessary.

    ``xmltodict`` returns a ``dict`` (rather than a one-element ``list``) when
    there is only a single child element in the XML.  This helper normalises
    both cases so callers can always iterate over a list.
    """
    return value if isinstance(value, list) else [value]


def extract_records(health_data: dict) -> pd.DataFrame:
    """Extract health records from the parsed XML dictionary.

    Records contain time-series measurements such as heart rate, step count,
    active energy burned, and many other health metrics.

    Args:
        health_data: Parsed XML dictionary (returned by :func:`load_xml_export`).

    Returns:
        A :class:`~pandas.DataFrame` with one row per health record.
    """
    records_list = _ensure_list(health_data["HealthData"]["Record"])
    df = pd.DataFrame(records_list)
    logger.info(f"Extracted {len(df)} health records")
    return df


def extract_workouts(health_data: dict) -> pd.DataFrame:
    """Extract workout data from the parsed XML and flatten nested structures.

    Apple Watch workout entries can contain nested metadata which is flattened
    using :func:`pandas.json_normalize`.

    Args:
        health_data: Parsed XML dictionary (returned by :func:`load_xml_export`).

    Returns:
        A flat :class:`~pandas.DataFrame` with one row per workout.
    """
    workouts_list = _ensure_list(health_data["HealthData"]["Workout"])
    workout_df = pd.DataFrame(workouts_list)
    df = pd.json_normalize(workout_df.to_dict(orient="records"))
    logger.info(f"Extracted {len(df)} workouts")
    return df


def extract_activity_summaries(health_data: dict) -> pd.DataFrame:
    """Extract daily activity summaries (rings data) from the parsed XML.

    Activity summaries capture the three Apple Watch activity rings: active
    energy burned, exercise minutes, and stand hours – per calendar day.

    Args:
        health_data: Parsed XML dictionary (returned by :func:`load_xml_export`).

    Returns:
        A :class:`~pandas.DataFrame` with one row per day.
    """
    activity_list = _ensure_list(health_data["HealthData"]["ActivitySummary"])
    df = pd.DataFrame(activity_list)
    logger.info(f"Extracted {len(df)} activity summaries")
    return df
