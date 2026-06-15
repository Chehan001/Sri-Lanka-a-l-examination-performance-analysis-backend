from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pdfplumber

from services.csv_cleaner import EXPECTED_COLUMNS

# Province names ordered longest-first for reliable matching
PROVINCES = [
    "North Western",
    "North Central",
    "Sabaragamuwa",
    "Western",
    "Southern",
    "Northern",
    "Eastern",
    "Central",
    "Uva",
]

NUMBER_RE = re.compile(r"[\d,]+")
PERCENT_RE = re.compile(r"[\d.]+")

PROVINCE_ROW_RE = re.compile(
    r"^(\d+)\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)"
    r"(?:\s+([\d,]+)\s+([\d.]+))?\s+([\d,]+)\s+([\d.]+)$"
)

STREAM_ROW_RE = re.compile(
    r"^(\d+)\.\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)"
    r"(?:\s+([\d,]+)\s+([\d.]+))?\s+([\d,]+)\s+([\d.]+)?$"
)

DISTRICT_ROW_RE = re.compile(
    r"^(\d+)\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)$"
)

SUBJECT_ROW_RE = re.compile(
    r"^(\d+)\s+(\d+[A-Z]?)\s+(.+?)\s+([\d,]+)\s+"
    r"([\d,]+)\s+([\d.]+)\s+"
    r"([\d,]+)\s+([\d.]+)\s+"
    r"([\d,]+)\s+([\d.]+)\s+"
    r"([\d,]+)\s+([\d.]+)\s+"
    r"([\d,]+)\s+([\d.]+)\s+"
    r"([\d,]+)\s+([\d.]+)$"
)


def _to_int(value: str) -> int:
    return int(value.replace(",", ""))


def _to_subject_no(value: str) -> int:
    """Convert subject codes like '25A' to a stable integer."""
    digits = re.match(r"(\d+)", value)
    if not digits:
        raise ValueError(f"Invalid subject number: {value}")
    base = int(digits.group(1))
    suffix = value[len(digits.group(1)) :].strip().upper()
    if not suffix:
        return base
    # Encode letter suffix: A=1, B=2, ... for subjects like 25A, 25B, 25C
    return base * 10 + (ord(suffix[0]) - ord("A") + 1)


def _to_float(value: str) -> float:
    return float(value.replace(",", ""))


def _last_int(line: str) -> Optional[int]:
    matches = NUMBER_RE.findall(line)
    if not matches:
        return None
    return _to_int(matches[-1])


def _last_float(line: str) -> Optional[float]:
    matches = PERCENT_RE.findall(line.replace(",", ""))
    if not matches:
        return None
    return float(matches[-1])


def _extract_pages_text(pdf_bytes: bytes) -> List[str]:
    pages: List[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages


def _find_page(
    pages: List[str],
    *markers: str,
    must_contain: Optional[str] = None,
    exclude_if: Optional[str] = None,
) -> Optional[str]:
    """Return the best matching page, skipping table-of-contents pages."""
    best_text: Optional[str] = None
    best_score = -1

    for text in pages:
        lower = text.lower()
        if exclude_if and exclude_if.lower() in lower:
            continue
        if not all(marker.lower() in lower for marker in markers):
            continue
        if must_contain and must_contain.lower() not in lower:
            continue

        # Prefer pages with more numeric data rows over index/list pages.
        score = sum(1 for line in text.splitlines() if NUMBER_RE.search(line))
        if score > best_score:
            best_score = score
            best_text = text

    return best_text


def _section_after(text: str, start_marker: str, end_markers: List[str]) -> str:
    lower = text.lower()
    start = lower.find(start_marker.lower())
    if start == -1:
        return ""
    section = text[start:]
    end_positions = []
    for marker in end_markers:
        pos = section.lower().find(marker.lower(), len(start_marker))
        if pos > 0:
            end_positions.append(pos)
    if end_positions:
        section = section[: min(end_positions)]
    return section


def _parse_yearly_block(section: str, year: int, candidate_type: str) -> Optional[Dict[str, Any]]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    metrics: Dict[str, Any] = {
        "year": year,
        "candidate_type": candidate_type,
    }
    state = "start"

    for line in lines:
        lower = line.lower()
        if lower.startswith("number sat"):
            metrics["no_sat"] = _last_int(line)
            state = "after_no_sat"
        elif lower.startswith("no.") or lower.startswith("no "):
            value = _last_int(line)
            if state in ("start", "after_no_sat", "after_eligible_label"):
                metrics["eligible_no"] = value
                state = "after_eligible_no"
            elif state == "after_three_a_label":
                metrics["three_a_no"] = value
                state = "after_three_a_no"
            elif state == "after_failed_label":
                metrics["failed_all_no"] = value
                state = "after_failed_no"
        elif "eligible for university" in lower:
            state = "after_eligible_label"
        elif "obtained 3" in lower:
            state = "after_three_a_label"
        elif "failed in all" in lower:
            state = "after_failed_label"
        elif line.startswith("%"):
            value = _last_float(line)
            if state in ("after_eligible_label", "after_eligible_no"):
                metrics["eligible_percentage"] = value
                state = "after_eligible_pct"
            elif state in ("after_three_a_label", "after_three_a_no"):
                metrics["three_a_percentage"] = value
                state = "after_three_a_pct"
            elif state in ("after_failed_label", "after_failed_no"):
                metrics["failed_all_percentage"] = value
                state = "after_failed_pct"

    required = {"no_sat", "eligible_no", "eligible_percentage"}
    if not required.issubset(metrics):
        return None
    return metrics


def _parse_yearly(pages: List[str], year: int) -> pd.DataFrame:
    page = _find_page(
        pages,
        "performance of school candidates by year",
        must_contain="Number Sat",
        exclude_if="List of Tables",
    )
    if not page:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["yearly"])

    school_section = _section_after(
        page,
        "Performance of School Candidates by Year",
        ["Performance of All Candidates by Year", "Table 2", "Table 3"],
    )
    all_section = _section_after(
        page,
        "Performance of All Candidates by Year",
        ["Table 3", "Performance of Candidates - All Island"],
    )

    rows = []
    school_row = _parse_yearly_block(school_section, year, "School")
    if school_row:
        rows.append(school_row)
    all_row = _parse_yearly_block(all_section, year, "All")
    if all_row:
        rows.append(all_row)

    if not rows:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["yearly"])

    df = pd.DataFrame(rows)
    for col in EXPECTED_COLUMNS["yearly"]:
        if col not in df.columns:
            df[col] = None
    return df[EXPECTED_COLUMNS["yearly"]]


RANK_DATA_RE = re.compile(
    r"^(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)"
    r"(?:\s+([\d,]+)\s+([\d.]+))?\s+([\d,]+)\s+([\d.]+)$"
)

RANK_ONLY_RE = re.compile(r"^(\d+)$")

STREAM_NAME_RE = re.compile(r"^(\d+)\.\s+(.+)$")

NAME_DATA_RE = re.compile(
    r"^(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)"
    r"(?:\s+([\d,]+)\s+([\d.]+))?\s+([\d,]+)\s+([\d.]+)$"
)

DATA_ONLY_RE = re.compile(
    r"^([\d,]+)\s+([\d,]+)\s+([\d.]+)"
    r"(?:\s+([\d,]+)\s+([\d.]+))?\s+([\d,]+)\s+([\d.]+)$"
)


def _build_ranked_row(
    name: str,
    groups: Tuple[str, ...],
    name_key: str,
) -> Dict[str, Any]:
    return {
        name_key: name.strip(),
        "no_sat": _to_int(groups[0]),
        "eligible_no": _to_int(groups[1]),
        "eligible_percentage": _to_float(groups[2]),
        "three_a_no": _to_int(groups[3]) if groups[3] else None,
        "three_a_percentage": _to_float(groups[4]) if groups[4] else None,
        "failed_all_no": _to_int(groups[5]) if groups[5] else None,
        "failed_all_percentage": _to_float(groups[6]) if groups[6] else None,
    }


def _parse_province_or_stream_rows(
    section: str, row_type: str
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    name_key = "stream" if row_type == "stream" else "province"
    lines = [line.strip() for line in section.splitlines() if line.strip()]

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        lower = line.lower()

        if lower.startswith("all island") or lower.startswith("total"):
            idx += 1
            continue

        # Standard single-line province/stream row
        pattern = STREAM_ROW_RE if row_type == "stream" else PROVINCE_ROW_RE
        match = pattern.match(line)
        if match:
            groups = match.groups()
            rows.append(
                _build_ranked_row(groups[1], groups[2:], name_key)
            )
            idx += 1
            continue

        # Stream name split across two lines: "1. Bio Science" + numbers
        stream_match = STREAM_NAME_RE.match(line)
        if row_type == "stream" and stream_match and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            data_match = DATA_ONLY_RE.match(next_line)
            if data_match:
                rows.append(
                    _build_ranked_row(
                        stream_match.group(2), data_match.groups(), name_key
                    )
                )
                idx += 2
                continue

        # Province rank + numbers, province name on next line (2023 format)
        rank_data = RANK_DATA_RE.match(line)
        if row_type == "province" and rank_data and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if NAME_DATA_RE.match(next_line) is None and not next_line[0].isdigit():
                rows.append(
                    _build_ranked_row(next_line, rank_data.groups()[1:], name_key)
                )
                idx += 2
                continue

        # Province rank only, "Province numbers..." on next line
        rank_only = RANK_ONLY_RE.match(line)
        if row_type == "province" and rank_only and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            name_data = NAME_DATA_RE.match(next_line)
            if name_data:
                rows.append(
                    _build_ranked_row(
                        name_data.group(1), name_data.groups()[1:], name_key
                    )
                )
                idx += 2
                continue

        idx += 1

    return rows


def _parse_province(pages: List[str], year: int) -> pd.DataFrame:
    page = _find_page(
        pages,
        "performance of school candidates by province",
        must_contain="Province No. Sat",
        exclude_if="List of Tables",
    )
    if not page:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["province"])

    school_section = _section_after(
        page,
        "Performance of School Candidates by Province",
        ["Performance of All Candidates by Province", "Table 5", "Table 6"],
    )
    all_section = _section_after(
        page,
        "Performance of All Candidates by Province",
        ["Table 6", "Performance of School Candidates by Subject Stream"],
    )

    rows: List[Dict[str, Any]] = []
    for candidate_type, section in [("School", school_section), ("All", all_section)]:
        for item in _parse_province_or_stream_rows(section, "province"):
            rows.append(
                {
                    "year": year,
                    "candidate_type": candidate_type,
                    **item,
                }
            )

    if not rows:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["province"])
    return pd.DataFrame(rows)[EXPECTED_COLUMNS["province"]]


def _parse_stream(pages: List[str], year: int) -> pd.DataFrame:
    page = _find_page(
        pages,
        "performance of school candidates by subject stream",
        must_contain="Bio Science",
        exclude_if="List of Tables",
    )
    if not page:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["stream"])

    school_section = _section_after(
        page,
        "Performance of School Candidates by Subject Stream",
        ["Performance of All Candidates by Subject", "Table 7", "Table 8"],
    )
    all_section = _section_after(
        page,
        "Performance of All Candidates by Subject",
        ["Table 8", "Figure 5"],
    )

    rows: List[Dict[str, Any]] = []
    for candidate_type, section in [("School", school_section), ("All", all_section)]:
        for item in _parse_province_or_stream_rows(section, "stream"):
            rows.append(
                {
                    "year": year,
                    "candidate_type": candidate_type,
                    **item,
                }
            )

    if not rows:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["stream"])
    return pd.DataFrame(rows)[EXPECTED_COLUMNS["stream"]]


def _parse_district(pages: List[str], year: int) -> pd.DataFrame:
    school_page = _find_page(
        pages,
        "performance of school candidates by district",
        must_contain="District No. Sat",
        exclude_if="List of Tables",
    )
    all_page = _find_page(
        pages,
        "performance of all candidates by district",
        must_contain="District No. Sat",
        exclude_if="List of Tables",
    )

    rows: List[Dict[str, Any]] = []
    for candidate_type, page in [("School", school_page), ("All", all_page)]:
        if not page:
            continue
        for line in page.splitlines():
            line = line.strip()
            if line.lower().startswith("all island"):
                continue
            match = DISTRICT_ROW_RE.match(line)
            if not match:
                continue
            rows.append(
                {
                    "year": year,
                    "candidate_type": candidate_type,
                    "district": match.group(2).strip(),
                    "no_sat": _to_int(match.group(3)),
                    "eligible_no": _to_int(match.group(4)),
                    "eligible_percentage": _to_float(match.group(5)),
                }
            )

    if not rows:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["district"])
    return pd.DataFrame(rows)[EXPECTED_COLUMNS["district"]]


def _parse_subject(pages: List[str], year: int) -> pd.DataFrame:
    page = _find_page(
        pages,
        "results by grades in each subject",
        must_contain="Subject No. Sat",
        exclude_if="List of Tables",
    )
    if not page:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["subject"])

    rows: List[Dict[str, Any]] = []
    for line in page.splitlines():
        line = line.strip()
        match = SUBJECT_ROW_RE.match(line)
        if not match:
            continue
        rows.append(
            {
                "year": year,
                "subject_no": _to_subject_no(match.group(2)),
                "subject": match.group(3).strip(),
                "no_sat": _to_int(match.group(4)),
                "a_no": _to_int(match.group(5)),
                "a_percentage": _to_float(match.group(6)),
                "b_no": _to_int(match.group(7)),
                "b_percentage": _to_float(match.group(8)),
                "c_no": _to_int(match.group(9)),
                "c_percentage": _to_float(match.group(10)),
                "s_no": _to_int(match.group(11)),
                "s_percentage": _to_float(match.group(12)),
                "pass_no": _to_int(match.group(13)),
                "pass_percentage": _to_float(match.group(14)),
                "fail_no": _to_int(match.group(15)),
                "fail_percentage": _to_float(match.group(16)),
            }
        )

    if not rows:
        return pd.DataFrame(columns=EXPECTED_COLUMNS["subject"])
    return pd.DataFrame(rows)[EXPECTED_COLUMNS["subject"]]


def parse_al_report_pdf(pdf_bytes: bytes, year: int) -> Dict[str, pd.DataFrame]:
    """
    Parse an official A/L results PDF and return categorized DataFrames.

    Returns a dict keyed by data_type with DataFrames matching master CSV schemas.
    """
    pages = _extract_pages_text(pdf_bytes)

    results = {
        "yearly": _parse_yearly(pages, year),
        "province": _parse_province(pages, year),
        "district": _parse_district(pages, year),
        "stream": _parse_stream(pages, year),
        "subject": _parse_subject(pages, year),
    }
    return results


def summarize_extraction(results: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    """Return row counts per category for API responses."""
    return {key: len(df) for key, df in results.items()}
