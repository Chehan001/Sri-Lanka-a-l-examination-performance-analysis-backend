from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    CompareYearsResponse,
    DashboardSummary,
    DistrictAnalysisResponse,
    ProvinceAnalysisResponse,
    StreamAnalysisResponse,
    SubjectAnalysisResponse,
    YearAnalysisResponse,
)
from services.analyzer import (
    compare_years,
    get_dashboard_summary,
    get_district_analysis,
    get_province_analysis,
    get_stream_analysis,
    get_subject_analysis,
    get_year_analysis,
)

router = APIRouter(tags=["Analysis"])


@router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary():
    """Return high-level dashboard statistics from uploaded data."""
    try:
        return get_dashboard_summary()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error building dashboard summary: {exc}",
        ) from exc


@router.get("/year-analysis")
def year_analysis():
    """
    Return year-wise eligibility percentages and
    school vs all candidate comparison.
    """
    try:
        return get_year_analysis()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error building year analysis: {exc}",
        ) from exc


@router.get("/province-analysis", response_model=ProvinceAnalysisResponse)
def province_analysis(
    year: Optional[int] = Query(None, description="Filter by exam year"),
    candidate_type: Optional[str] = Query(
        None, description="Filter by candidate type (e.g. School, All)"
    ),
):
    """Return province rankings by eligible_percentage."""
    try:
        return get_province_analysis(year=year, candidate_type=candidate_type)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error building province analysis: {exc}",
        ) from exc


@router.get("/district-analysis", response_model=DistrictAnalysisResponse)
def district_analysis(
    year: Optional[int] = Query(None, description="Filter by exam year"),
    candidate_type: Optional[str] = Query(
        None, description="Filter by candidate type (e.g. School, All)"
    ),
):
    """Return district rankings by eligible_percentage."""
    try:
        return get_district_analysis(year=year, candidate_type=candidate_type)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error building district analysis: {exc}",
        ) from exc


@router.get("/stream-analysis", response_model=StreamAnalysisResponse)
def stream_analysis(
    year: Optional[int] = Query(None, description="Filter by exam year"),
    candidate_type: Optional[str] = Query(
        None, description="Filter by candidate type (e.g. School, All)"
    ),
):
    """Return stream rankings by eligible_percentage."""
    try:
        return get_stream_analysis(year=year, candidate_type=candidate_type)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error building stream analysis: {exc}",
        ) from exc


@router.get("/subject-analysis", response_model=SubjectAnalysisResponse)
def subject_analysis(
    year: Optional[int] = Query(None, description="Filter by exam year"),
):
    """
    Return subject pass percentage rankings and
    grade distribution (A, B, C, S, fail).
    """
    try:
        return get_subject_analysis(year=year)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error building subject analysis: {exc}",
        ) from exc


@router.get("/compare-years", response_model=CompareYearsResponse)
def compare_years_endpoint(
    year1: int = Query(..., description="First year to compare (e.g. 2024)"),
    year2: int = Query(..., description="Second year to compare (e.g. 2025)"),
):
    """
    Compare eligibility, pass rates, province, stream, and subject
    performance between two years.
    """
    if year1 < 2020 or year1 > 2025 or year2 < 2020 or year2 > 2025:
        raise HTTPException(
            status_code=400,
            detail="Years must be between 2020 and 2025.",
        )

    if year1 == year2:
        raise HTTPException(
            status_code=400,
            detail="year1 and year2 must be different.",
        )

    try:
        return compare_years(year1, year2)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing years: {exc}",
        ) from exc
