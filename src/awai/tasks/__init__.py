"""Task modules for data loading and preparation."""

from awai.tasks.load_data import load_to_duckdb
from awai.tasks.prepare_data import prepare_records

__all__ = ["load_to_duckdb", "prepare_records"]
