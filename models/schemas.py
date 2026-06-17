
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Allowed data types when uploading or exporting CSV files
VALID_DATA_TYPES = ["yearly", "province", "district", "stream", "subject"]


class UploadResponse(BaseModel):
    """Response returned after a successful CSV upload."""

    message: str
    year: int
    data_type: str
    raw_file: str
    processed_file: str
    rows_saved: int


class PdfCategoryResult(BaseModel):
    """Per-category result after parsing a PDF report."""

    data_type: str
    rows_saved: int
    processed_file: str


class PdfUploadResponse(BaseModel):
    """Response returned after a successful PDF upload and extraction."""

    message: str
    year: int
    raw_file: str
    categories: List[PdfCategoryResult]
    total_rows_saved: int


class DashboardSummary(BaseModel):
    """High-level summary shown on the dashboard."""

    total_years_uploaded: int
    latest_year: Optional[int] = None
    latest_year_total_candidates: Optional[int] = None
    latest_year_eligibility_percentage: Optional[float] = None
    best_province: Optional[str] = None
    weakest_province: Optional[str] = None
    best_district: Optional[str] = None
    weakest_district: Optional[str] = None
    best_stream: Optional[str] = None
    best_subject: Optional[str] = None
    lowest_subject: Optional[str] = None


class YearAnalysisResponse(BaseModel):
    """Year-wise eligibility trends and school vs all comparison."""

    year_wise_eligibility: List[Dict[str, Any]]
    school_vs_all_comparison: List[Dict[str, Any]]


class RankingItem(BaseModel):
    """Generic ranking row used by province, district, and stream analysis."""

    rank: int
    name: str
    year: int
    candidate_type: str
    eligible_percentage: float
    no_sat: Optional[int] = None
    eligible_no: Optional[int] = None


class ProvinceAnalysisResponse(BaseModel):
    rankings: List[RankingItem]


class DistrictAnalysisResponse(BaseModel):
    rankings: List[RankingItem]


class StreamAnalysisResponse(BaseModel):
    rankings: List[RankingItem]


class SubjectGradeDistribution(BaseModel):
    """Grade breakdown for a single subject."""

    subject: str
    year: int
    a_percentage: float
    b_percentage: float
    c_percentage: float
    s_percentage: float
    fail_percentage: float


class SubjectRankingItem(BaseModel):
    rank: int
    subject: str
    year: int
    pass_percentage: float
    no_sat: Optional[int] = None
    grade_distribution: SubjectGradeDistribution


class SubjectAnalysisResponse(BaseModel):
    subject_rankings: List[SubjectRankingItem]


class CompareYearsResponse(BaseModel):
    """Comparison between two academic years."""

    year1: Dict[str, Any]
    year2: Dict[str, Any]
    provinceComparison: List[Dict[str, Any]]
    streamComparison: List[Dict[str, Any]]
    subjectComparison: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    detail: str
