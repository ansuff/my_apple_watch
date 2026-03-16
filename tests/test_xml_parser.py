"""Tests for the XML parsing utilities."""

import textwrap
from pathlib import Path

import pandas as pd
import pytest

from awai.utils.xml_parser import (
    extract_activity_summaries,
    extract_records,
    extract_workouts,
    load_xml_export,
)

# ---------------------------------------------------------------------------
# Minimal Apple Watch XML fixture
# ---------------------------------------------------------------------------

MINIMAL_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <HealthData locale="en_US">
      <Record type="HKQuantityTypeIdentifierActiveEnergyBurned"
              sourceName="Apple Watch"
              unit="kcal"
              creationDate="2024-01-01 08:30:00 +0000"
              startDate="2024-01-01 08:00:00 +0000"
              endDate="2024-01-01 08:30:00 +0000"
              value="250"/>
      <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
               duration="45.0" durationUnit="min"
               sourceName="Apple Watch"
               creationDate="2024-01-01 09:15:00 +0000"
               startDate="2024-01-01 08:30:00 +0000"
               endDate="2024-01-01 09:15:00 +0000"/>
      <ActivitySummary dateComponents="2024-01-01"
                       activeEnergyBurned="600" activeEnergyBurnedGoal="500"
                       activeEnergyBurnedUnit="kcal"
                       appleExerciseTime="30" appleExerciseTimeGoal="30"
                       appleStandHours="12" appleStandHoursGoal="12"/>
    </HealthData>
""")


@pytest.fixture()
def xml_file(tmp_path: Path) -> Path:
    """Write the minimal XML snippet to a temporary file."""
    p = tmp_path / "export.xml"
    p.write_text(MINIMAL_XML, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_load_xml_export_returns_dict(xml_file: Path) -> None:
    data = load_xml_export(xml_file)
    assert isinstance(data, dict)
    assert "HealthData" in data


def test_extract_records_returns_dataframe(xml_file: Path) -> None:
    data = load_xml_export(xml_file)
    df = extract_records(data)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "@type" in df.columns


def test_extract_records_value(xml_file: Path) -> None:
    data = load_xml_export(xml_file)
    df = extract_records(data)
    assert df["@value"].iloc[0] == "250"


def test_extract_workouts_returns_dataframe(xml_file: Path) -> None:
    data = load_xml_export(xml_file)
    df = extract_workouts(data)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1


def test_extract_activity_summaries_returns_dataframe(xml_file: Path) -> None:
    data = load_xml_export(xml_file)
    df = extract_activity_summaries(data)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1


def test_extract_activity_summaries_columns(xml_file: Path) -> None:
    data = load_xml_export(xml_file)
    df = extract_activity_summaries(data)
    assert "@dateComponents" in df.columns
