import io
import zipfile

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.schemas import VALID_DATA_TYPES
from services.csv_cleaner import MASTER_FILENAMES
from services.csv_combiner import PROCESSED_DIR, get_processed_csv_path, load_master_csv

router = APIRouter(tags=["Export"])


@router.get("/export/{data_type}")
def export_csv(data_type: str):
    """
    Export cleaned CSV data.

    data_type can be: yearly, province, district, stream, subject, or all.
    - Single type: returns a CSV file download
    - 'all': returns a ZIP containing all master CSV files
    """
    data_type = data_type.strip().lower()

    if data_type == "all":
        return _export_all_as_zip()

    if data_type not in VALID_DATA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type '{data_type}'. "
            f"Must be one of: {VALID_DATA_TYPES + ['all']}",
        )

    file_path = get_processed_csv_path(data_type)
    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"No processed data found for '{data_type}'. Upload CSV files first.",
        )

    df = load_master_csv(data_type)
    filename = MASTER_FILENAMES[data_type]

    return _dataframe_to_csv_response(df, filename)


def _dataframe_to_csv_response(df: pd.DataFrame, filename: str) -> StreamingResponse:
    """Convert a DataFrame to a downloadable CSV StreamingResponse."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_all_as_zip() -> StreamingResponse:
    """Bundle all master CSV files into a single ZIP download."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files_added = 0
        for data_type, filename in MASTER_FILENAMES.items():
            path = get_processed_csv_path(data_type)
            if path is not None:
                df = load_master_csv(data_type)
                csv_content = df.to_csv(index=False)
                zip_file.writestr(filename, csv_content)
                files_added += 1

    if files_added == 0:
        raise HTTPException(
            status_code=404,
            detail="No processed data found. Upload CSV files first.",
        )

    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="al_performance_data.zip"'
        },
    )
