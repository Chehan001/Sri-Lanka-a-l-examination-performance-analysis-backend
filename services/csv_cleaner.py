import re
from typing import Dict, List, Optional, Union

import pandas as pd

# Expected columns for each data type (used for validation)
EXPECTED_COLUMNS: Dict[str, List[str]] = {
    "yearly": [
        "year",
        "candidate_type",
        "no_sat",
        "eligible_no",
        "eligible_percentage",
        "three_a_no",
        "three_a_percentage",
        "failed_all_no",
        "failed_all_percentage",
    ],
    "province": [
        "year",
        "candidate_type",
        "province",
        "no_sat",
        "eligible_no",
        "eligible_percentage",
        "three_a_no",
        "three_a_percentage",
        "failed_all_no",
        "failed_all_percentage",
    ],
    "district": [
        "year",
        "candidate_type",
        "district",
        "no_sat",
        "eligible_no",
        "eligible_percentage",
    ],
    "stream": [
        "year",
        "candidate_type",
        "stream",
        "no_sat",
        "eligible_no",
        "eligible_percentage",
        "three_a_no",
        "three_a_percentage",
        "failed_all_no",
        "failed_all_percentage",
    ],
    "subject": [
        "year",
        "subject_no",
        "subject",
        "no_sat",
        "a_no",
        "a_percentage",
        "b_no",
        "b_percentage",
        "c_no",
        "c_percentage",
        "s_no",
        "s_percentage",
        "pass_no",
        "pass_percentage",
        "fail_no",
        "fail_percentage",
    ],
}

# Master file names inside data/processed/
MASTER_FILENAMES = {
    "yearly": "yearly_master.csv",
    "province": "province_master.csv",
    "district": "district_master.csv",
    "stream": "stream_master.csv",
    "subject": "subject_master.csv",
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Convert column names to lowercase and replace spaces with underscores."""
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "_").replace("%", "percentage")
        for col in df.columns
    ]
    return df


def clean_numeric_value(value) -> Optional[Union[float, int]]:
    """
    Clean a single cell value:
    - Remove commas (e.g. '12,345' -> 12345)
    - Remove percentage signs (e.g. '45.6%' -> 45.6)
    - Return None for empty or invalid values
    """
    if pd.isna(value):
        return None

    text = str(value).strip()
    if text == "" or text.lower() in ("nan", "none", "-"):
        return None

    # Remove commas and percentage signs
    text = text.replace(",", "").replace("%", "").strip()

    # Some PDF exports use brackets or extra symbols
    text = re.sub(r"[^\d.\-]", "", text)

    if text == "" or text == "-":
        return None

    try:
        number = float(text)
        # Return int when the value is a whole number (for counts like no_sat)
        if number == int(number) and "." not in str(value).replace(",", ""):
            return int(number)
        return round(number, 4)
    except ValueError:
        return None


def clean_dataframe(data_type: str, df: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Clean a raw uploaded DataFrame:
    1. Normalize column names
    2. Validate required columns exist
    3. Clean numeric columns
    4. Set the year column
    """
    if data_type not in EXPECTED_COLUMNS:
        raise ValueError(
            f"Invalid data_type '{data_type}'. "
            f"Must be one of: {list(EXPECTED_COLUMNS.keys())}"
        )

    df = normalize_column_names(df)

    expected = EXPECTED_COLUMNS[data_type]
    missing = [col for col in expected if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns for '{data_type}': {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Keep only expected columns (in order)
    df = df[expected].copy()

    # Always set year from the upload form (overrides CSV if present)
    df["year"] = year

    # Text columns that should stay as strings
    text_columns = {"candidate_type", "province", "district", "stream", "subject"}

    for col in df.columns:
        if col in text_columns:
            df[col] = df[col].astype(str).str.strip()
        else:
            df[col] = df[col].apply(clean_numeric_value)

    # Drop completely empty rows
    df = df.dropna(how="all")
    df = df.reset_index(drop=True)

    return df
