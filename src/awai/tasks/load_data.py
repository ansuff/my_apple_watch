"""Task: load an Apple Watch XML export into a DuckDB database."""

from pathlib import Path

import duckdb
from loguru import logger

from awai.utils.xml_parser import (
    extract_activity_summaries,
    extract_records,
    extract_workouts,
    load_xml_export,
)


def load_to_duckdb(xml_path: Path, db_path: Path) -> None:
    """Parse the Apple Watch XML export and persist data into DuckDB.

    Three tables are created (if they do not already exist):

    * ``records``    – time-series health measurements.
    * ``workouts``   – individual workout sessions (flattened).
    * ``activities`` – daily activity-ring summaries.

    If all three tables are already present in *db_path* the function exits
    early without re-parsing the XML file.

    Args:
        xml_path: Path to the Apple Watch ``export.xml`` file.
        db_path:  Path where the DuckDB database will be created or opened.
    """
    xml_path = Path(xml_path)
    db_path = Path(db_path)

    con = duckdb.connect(str(db_path))
    try:
        already_loaded = (
            con.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'main' "
                "AND table_name IN ('records', 'workouts', 'activities')"
            ).fetchone()[0]
            >= 3
        )
        if already_loaded:
            logger.info("All tables already exist in DuckDB – skipping load.")
            return

        logger.info(f"Parsing XML export from {xml_path} …")
        health_data = load_xml_export(xml_path)

        records_df = extract_records(health_data)
        workout_df_flat = extract_workouts(health_data)
        activity_df = extract_activity_summaries(health_data)

        con.execute("CREATE TABLE records AS SELECT * FROM records_df")
        con.execute("CREATE TABLE workouts AS SELECT * FROM workout_df_flat")
        con.execute("CREATE TABLE activities AS SELECT * FROM activity_df")

        logger.info("Data successfully loaded into DuckDB.")
    finally:
        con.close()
