# Apple Watch Fitness AI

A data-science project that predicts optimal workout timing from Apple Watch health data.

## Goals

- **Phase 1** – Predict the best *time of day* for a workout (heart rate, sleep, activity data).
- **Phase 2** – Predict the best *type* of workout.
- **Phase 3** – Predict the best *day of the week* for a workout.

## Project structure

```
AppleWatchAI/
├── src/awai/
│   ├── entrypoint.py        # CLI entry point (fire-based)
│   ├── utils/
│   │   ├── xml_parser.py    # Parse Apple Watch XML exports
│   │   └── data_cleaner.py  # Cleaning, filtering & aggregation helpers
│   ├── models/
│   │   └── schemas.py       # Pandera validation schemas
│   └── tasks/
│       ├── load_data.py     # XML → DuckDB load task
│       └── prepare_data.py  # Full clean/filter/aggregate pipeline
├── notebooks/exploratory/   # Jupytext-managed EDA notebooks
├── tests/                   # pytest test suite
├── data/                    # Apple Watch export files (git-ignored)
└── settings.toml            # Default configuration (Dynaconf)
```

## Setup

### Prerequisites

- Python 3.11 or later
- [Poetry](https://python-poetry.org/) (install via `pip install poetry` or `brew install poetry`)

### macOS quick-start

```sh
./init_setup.sh   # installs Homebrew & Poetry if missing
poetry install    # installs all Python dependencies
```

### Other platforms

```sh
pip install poetry
poetry install
```

## Usage

Export your Apple Health data from the iPhone Health app (*Profile → Export All Health Data*) and place the resulting `export.xml` inside a `data/` folder at the project root.

### Load the XML export into DuckDB

```sh
poetry run awai load --xml_path=data/export.xml --db_path=data/health_data.duckdb
```

### Run the data-preparation pipeline

```sh
poetry run awai prepare --db_path=data/health_data.duckdb
```

### Explore interactively

The `notebooks/exploratory/EDA.py` notebook contains the original exploratory analysis.  
To convert it to a Jupyter notebook and open it:

```sh
poetry run jupytext --sync notebooks/exploratory/EDA.py
poetry run jupyter lab notebooks/exploratory/EDA.ipynb
```

## Running tests

```sh
poetry run pytest
```

## Configuration

Default settings live in `settings.toml`.  Override any value with an environment variable prefixed with `DYNACONF_`, e.g.:

```sh
export DYNACONF_DATA_DIR=/path/to/my/data
```

## Contributing

1. Install dev dependencies: `poetry install`
2. Install pre-commit hooks: `poetry run pre-commit install`
3. Run the test suite: `poetry run pytest`
