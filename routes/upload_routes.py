import io

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from models.schemas import (
    VALID_DATA_TYPES,
    PdfCategoryResult,
    PdfUploadResponse,
    UploadResponse,
)
from services.csv_cleaner import clean_dataframe
from services.csv_combiner import save_raw_csv, save_raw_pdf, update_master_csv
from services.database_service import save_dataframe_to_db
from services.pdf_parser import parse_al_report_pdf

router = APIRouter(tags=["Upload"])


@router.post("/upload-csv", response_model=UploadResponse)
async def upload_csv(
    year: int = Form(..., description="Exam year (e.g. 2024)"),
    data_type: str = Form(
        ..., description="One of: yearly, province, district, stream, subject"
    ),
    file: UploadFile = File(..., description="CSV file extracted from PDF report"),
):
    """
    Upload a CSV file for a specific year and data category.

    - Saves the original file to data/raw_csv/
    - Cleans numbers (removes commas and % signs)
    - Saves cleaned data to data/processed/ master CSV
    - Stores rows in the SQLite database
    """
    # Validate data_type
    data_type = data_type.strip().lower()
    if data_type not in VALID_DATA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type '{data_type}'. Must be one of: {VALID_DATA_TYPES}",
        )

    # Validate year range (G.C.E. A/L reports 2020–2025)
    if year < 2020 or year > 2025:
        raise HTTPException(
            status_code=400,
            detail="Year must be between 2020 and 2025.",
        )

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted.",
        )

    try:
        # Read uploaded file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Save original raw file
        raw_path = save_raw_csv(content, data_type, year, file.filename)

        # Parse CSV with pandas
        try:
            raw_df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read CSV file: {exc}",
            ) from exc

        # Clean the data
        try:
            cleaned_df = clean_dataframe(data_type, raw_df, year)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if cleaned_df.empty:
            raise HTTPException(
                status_code=400,
                detail="No valid data rows found in the uploaded CSV.",
            )

        # Update master processed CSV
        processed_path = update_master_csv(data_type, cleaned_df, year)

        # Save to SQLite database
        rows_saved = save_dataframe_to_db(data_type, cleaned_df, year)

        return UploadResponse(
            message="CSV uploaded and processed successfully.",
            year=year,
            data_type=data_type,
            raw_file=raw_path,
            processed_file=processed_path,
            rows_saved=rows_saved,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Server error while processing upload: {exc}",
        ) from exc


@router.post("/upload-pdf", response_model=PdfUploadResponse)
async def upload_pdf(
    year: int = Form(..., description="Exam year (e.g. 2024)"),
    file: UploadFile = File(..., description="Official G.C.E. A/L results PDF report"),
):
    """
    Upload an official A/L results PDF and automatically extract all categories.

    Parses yearly, province, district, stream, and subject tables from the report,
    then stores each category in the database and master CSV files.
    """
    if year < 2020 or year > 2025:
        raise HTTPException(
            status_code=400,
            detail="Year must be between 2020 and 2025.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        raw_path = save_raw_pdf(content, year, file.filename)

        try:
            extracted = parse_al_report_pdf(content, year)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not parse PDF report: {exc}",
            ) from exc

        categories: list[PdfCategoryResult] = []
        total_rows = 0

        for data_type in VALID_DATA_TYPES:
            raw_df = extracted.get(data_type, pd.DataFrame())
            if raw_df is None or raw_df.empty:
                continue

            cleaned_df = clean_dataframe(data_type, raw_df, year)
            processed_path = update_master_csv(data_type, cleaned_df, year)
            rows_saved = save_dataframe_to_db(data_type, cleaned_df, year)

            categories.append(
                PdfCategoryResult(
                    data_type=data_type,
                    rows_saved=rows_saved,
                    processed_file=processed_path,
                )
            )
            total_rows += rows_saved

        if not categories:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No recognizable tables were found in the PDF. "
                    "Please upload an official Department of Examinations A/L report."
                ),
            )

        return PdfUploadResponse(
            message=(
                f"PDF parsed successfully. Saved {total_rows} rows across "
                f"{len(categories)} categories for year {year}."
            ),
            year=year,
            raw_file=raw_path,
            categories=categories,
            total_rows_saved=total_rows,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Server error while processing PDF upload: {exc}",
        ) from exc
