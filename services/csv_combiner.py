import os
from typing import Optional

import pandas as pd

from services.csv_cleaner import MASTER_FILENAMES

# Base paths for raw and processed data folders
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_CSV_DIR = os.path.join(BASE_DIR, "data", "raw_csv")
RAW_PDF_DIR = os.path.join(BASE_DIR, "data", "raw_pdf")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")


def ensure_directories() -> None:
    """Create data folders if they do not exist."""
    os.makedirs(RAW_CSV_DIR, exist_ok=True)
    os.makedirs(RAW_PDF_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)


def get_master_path(data_type: str) -> str:
    """Return the full path to a master CSV file."""
    filename = MASTER_FILENAMES[data_type]
    return os.path.join(PROCESSED_DIR, filename)


def save_raw_csv(file_content: bytes, data_type: str, year: int, original_filename: str) -> str:
    """
    Save the original uploaded file to data/raw_csv/.
    Returns the saved file path.
    """
    ensure_directories()
    safe_name = os.path.basename(original_filename).replace(" ", "_")
    saved_name = f"{data_type}_{year}_{safe_name}"
    file_path = os.path.join(RAW_CSV_DIR, saved_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path


def save_raw_pdf(file_content: bytes, year: int, original_filename: str) -> str:
    """Save the original uploaded PDF to data/raw_pdf/."""
    ensure_directories()
    safe_name = os.path.basename(original_filename).replace(" ", "_")
    saved_name = f"al_report_{year}_{safe_name}"
    file_path = os.path.join(RAW_PDF_DIR, saved_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path


def update_master_csv(data_type: str, cleaned_df: pd.DataFrame, year: int) -> str:
    """
    Merge cleaned data into the master CSV for this data type.
    Rows for the same year are replaced (so re-uploading updates data).
    Returns the master file path.
    """
    ensure_directories()
    master_path = get_master_path(data_type)

    if os.path.exists(master_path):
        existing_df = pd.read_csv(master_path)
        # Remove old rows for this year, then append new ones
        existing_df = existing_df[existing_df["year"] != year]
        combined_df = pd.concat([existing_df, cleaned_df], ignore_index=True)
    else:
        combined_df = cleaned_df

    # Sort by year for easier reading
    combined_df = combined_df.sort_values("year").reset_index(drop=True)
    combined_df.to_csv(master_path, index=False)

    return master_path


def get_processed_csv_path(data_type: str) -> Optional[str]:
    """Return path to master CSV if it exists, else None."""
    master_path = get_master_path(data_type)
    return master_path if os.path.exists(master_path) else None


def load_master_csv(data_type: str) -> pd.DataFrame:
    """Load a master CSV file, or return empty DataFrame if missing."""
    path = get_processed_csv_path(data_type)
    if path is None:
        return pd.DataFrame()
    return pd.read_csv(path)
