"""Pandera schemas for validating Apple Watch health data DataFrames."""

import pandera as pa
from pandera import Column, DataFrameSchema

#: Schema for the cleaned health records DataFrame produced by
#: :func:`~awai.utils.data_cleaner.clean_records`.
RecordsSchema = DataFrameSchema(
    {
        "type": Column(str, nullable=False),
        "Date": Column(
            str,
            pa.Check.str_matches(r"^\d{4}-\d{2}-\d{2}$"),
            nullable=False,
        ),
        "Day": Column(str, nullable=False),
        "Month": Column(str, nullable=False),
        "value": Column(float, pa.Check.ge(0), nullable=False),
        "unit": Column(str, nullable=True),
    },
    coerce=True,
)
