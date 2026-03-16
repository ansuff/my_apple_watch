"""CLI entry point for Apple Watch AI."""

from pathlib import Path

import fire
from loguru import logger

from awai.tasks.load_data import load_to_duckdb
from awai.tasks.prepare_data import prepare_records


class CLI:
    """Apple Watch AI command-line interface.

    Available commands::

        awai load     – parse export.xml and store data in DuckDB
        awai prepare  – clean, filter, and aggregate the stored data
    """

    def load(
        self,
        xml_path: str = "data/export.xml",
        db_path: str = "data/health_data.duckdb",
    ) -> None:
        """Parse an Apple Watch XML export and load it into a DuckDB database.

        Args:
            xml_path: Path to the Apple Watch ``export.xml`` file.
            db_path:  Path where the DuckDB database will be created.
        """
        load_to_duckdb(Path(xml_path), Path(db_path))
        logger.info("Load complete.")

    def prepare(
        self,
        db_path: str = "data/health_data.duckdb",
    ) -> None:
        """Run the data-preparation pipeline (clean, filter, aggregate).

        Args:
            db_path: Path to the DuckDB database created by the ``load`` command.
        """
        by_type, daily, monthly = prepare_records(Path(db_path))
        logger.info(
            f"Prepared {len(by_type)} record types, "
            f"{sum(len(v) for v in daily.values()):,} daily rows, "
            f"{sum(len(v) for v in monthly.values()):,} monthly rows."
        )


def main() -> None:
    """Fire-based CLI entry point."""
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
