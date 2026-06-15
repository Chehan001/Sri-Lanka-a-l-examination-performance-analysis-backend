from typing import Any, Dict, List, Optional

import pandas as pd

from services.database_service import get_distinct_years, get_latest_year, load_table_as_dataframe


def _safe_float(value) -> Optional[float]:
    """Convert a value to float, returning None if not possible."""
    if pd.isna(value):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    """Convert a value to int, returning None if not possible."""
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _filter_by_year_and_type(
    df: pd.DataFrame, year: Optional[int], candidate_type: Optional[str]
) -> pd.DataFrame:
    """Apply optional year and candidate_type filters."""
    if df.empty:
        return df

    result = df.copy()
    if year is not None:
        result = result[result["year"] == year]
    if candidate_type is not None:
        result = result[
            result["candidate_type"].str.lower() == candidate_type.lower()
        ]
    return result


def get_dashboard_summary() -> Dict[str, Any]:
    """Build the dashboard summary from all available data."""
    yearly_df = load_table_as_dataframe("yearly")
    province_df = load_table_as_dataframe("province")
    district_df = load_table_as_dataframe("district")
    stream_df = load_table_as_dataframe("stream")
    subject_df = load_table_as_dataframe("subject")

    years = get_distinct_years()
    latest_year = get_latest_year()

    summary: Dict[str, Any] = {
        "total_years_uploaded": len(years),
        "latest_year": latest_year,
        "latest_year_total_candidates": None,
        "latest_year_eligibility_percentage": None,
        "best_province": None,
        "weakest_province": None,
        "best_district": None,
        "weakest_district": None,
        "best_stream": None,
        "best_subject": None,
        "lowest_subject": None,
    }

    if latest_year is None:
        return summary

    # Latest year stats from yearly_master (prefer 'All' candidate type)
    year_data = yearly_df[yearly_df["year"] == latest_year]
    if not year_data.empty:
        all_row = year_data[
            year_data["candidate_type"].str.lower().isin(["all", "all candidates"])
        ]
        row = all_row.iloc[0] if not all_row.empty else year_data.iloc[0]
        summary["latest_year_total_candidates"] = _safe_int(row.get("no_sat"))
        summary["latest_year_eligibility_percentage"] = _safe_float(
            row.get("eligible_percentage")
        )

    # Province best / weakest for latest year
    prov = _filter_by_year_and_type(province_df, latest_year, None)
    if not prov.empty and "eligible_percentage" in prov.columns:
        prov = prov.dropna(subset=["eligible_percentage"])
        if not prov.empty:
            best = prov.loc[prov["eligible_percentage"].idxmax()]
            worst = prov.loc[prov["eligible_percentage"].idxmin()]
            summary["best_province"] = str(best["province"])
            summary["weakest_province"] = str(worst["province"])

    # District best / weakest for latest year
    dist = _filter_by_year_and_type(district_df, latest_year, None)
    if not dist.empty and "eligible_percentage" in dist.columns:
        dist = dist.dropna(subset=["eligible_percentage"])
        if not dist.empty:
            best = dist.loc[dist["eligible_percentage"].idxmax()]
            worst = dist.loc[dist["eligible_percentage"].idxmin()]
            summary["best_district"] = str(best["district"])
            summary["weakest_district"] = str(worst["district"])

    # Best stream for latest year
    strm = _filter_by_year_and_type(stream_df, latest_year, None)
    if not strm.empty and "eligible_percentage" in strm.columns:
        strm = strm.dropna(subset=["eligible_percentage"])
        if not strm.empty:
            best = strm.loc[strm["eligible_percentage"].idxmax()]
            summary["best_stream"] = str(best["stream"])

    # Best and lowest subject by pass percentage for latest year
    subj = subject_df[subject_df["year"] == latest_year] if not subject_df.empty else subject_df
    if not subj.empty and "pass_percentage" in subj.columns:
        subj = subj.dropna(subset=["pass_percentage"])
        if not subj.empty:
            best = subj.loc[subj["pass_percentage"].idxmax()]
            worst = subj.loc[subj["pass_percentage"].idxmin()]
            summary["best_subject"] = str(best["subject"])
            summary["lowest_subject"] = str(worst["subject"])

    return summary


def get_year_analysis() -> List[Dict[str, Any]]:
    """
    Return raw year-wise candidate records.
    """
    yearly_df = load_table_as_dataframe("yearly")
    if yearly_df.empty:
        return []
    return yearly_df.to_dict(orient="records")


def get_province_analysis(
    year: Optional[int] = None, candidate_type: Optional[str] = None
) -> Dict[str, Any]:
    """Return province rankings sorted by eligible_percentage (descending)."""
    df = load_table_as_dataframe("province")
    df = _filter_by_year_and_type(df, year, candidate_type)

    if df.empty:
        return {"rankings": []}

    df = df.dropna(subset=["eligible_percentage"])
    df = df.sort_values("eligible_percentage", ascending=False).reset_index(drop=True)

    rankings = []
    for idx, row in df.iterrows():
        rankings.append(
            {
                "rank": idx + 1,
                "name": str(row["province"]),
                "year": int(row["year"]),
                "candidate_type": str(row["candidate_type"]),
                "eligible_percentage": _safe_float(row["eligible_percentage"]),
                "no_sat": _safe_int(row.get("no_sat")),
                "eligible_no": _safe_int(row.get("eligible_no")),
            }
        )

    return {"rankings": rankings}


def get_district_analysis(
    year: Optional[int] = None, candidate_type: Optional[str] = None
) -> Dict[str, Any]:
    """Return district rankings sorted by eligible_percentage (descending)."""
    df = load_table_as_dataframe("district")
    df = _filter_by_year_and_type(df, year, candidate_type)

    if df.empty:
        return {"rankings": []}

    df = df.dropna(subset=["eligible_percentage"])
    df = df.sort_values("eligible_percentage", ascending=False).reset_index(drop=True)

    rankings = []
    for idx, row in df.iterrows():
        rankings.append(
            {
                "rank": idx + 1,
                "name": str(row["district"]),
                "year": int(row["year"]),
                "candidate_type": str(row["candidate_type"]),
                "eligible_percentage": _safe_float(row["eligible_percentage"]),
                "no_sat": _safe_int(row.get("no_sat")),
                "eligible_no": _safe_int(row.get("eligible_no")),
            }
        )

    return {"rankings": rankings}


def get_stream_analysis(
    year: Optional[int] = None, candidate_type: Optional[str] = None
) -> Dict[str, Any]:
    """Return stream rankings sorted by eligible_percentage (descending)."""
    df = load_table_as_dataframe("stream")
    df = _filter_by_year_and_type(df, year, candidate_type)

    if df.empty:
        return {"rankings": []}

    df = df.dropna(subset=["eligible_percentage"])
    df = df.sort_values("eligible_percentage", ascending=False).reset_index(drop=True)

    rankings = []
    for idx, row in df.iterrows():
        rankings.append(
            {
                "rank": idx + 1,
                "name": str(row["stream"]),
                "year": int(row["year"]),
                "candidate_type": str(row["candidate_type"]),
                "eligible_percentage": _safe_float(row["eligible_percentage"]),
                "no_sat": _safe_int(row.get("no_sat")),
                "eligible_no": _safe_int(row.get("eligible_no")),
            }
        )

    return {"rankings": rankings}


def get_subject_analysis(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Return subject pass percentage rankings and
    grade distribution (A, B, C, S, fail) for each subject.
    """
    df = load_table_as_dataframe("subject")

    if year is not None:
        df = df[df["year"] == year]

    if df.empty:
        return {"subject_rankings": []}

    df = df.dropna(subset=["pass_percentage"])
    df = df.sort_values("pass_percentage", ascending=False).reset_index(drop=True)

    rankings = []
    for idx, row in df.iterrows():
        grade_distribution = {
            "subject": str(row["subject"]),
            "year": int(row["year"]),
            "a_percentage": _safe_float(row.get("a_percentage")) or 0.0,
            "b_percentage": _safe_float(row.get("b_percentage")) or 0.0,
            "c_percentage": _safe_float(row.get("c_percentage")) or 0.0,
            "s_percentage": _safe_float(row.get("s_percentage")) or 0.0,
            "fail_percentage": _safe_float(row.get("fail_percentage")) or 0.0,
        }
        rankings.append(
            {
                "rank": idx + 1,
                "subject": str(row["subject"]),
                "year": int(row["year"]),
                "pass_percentage": _safe_float(row["pass_percentage"]),
                "no_sat": _safe_int(row.get("no_sat")),
                "grade_distribution": grade_distribution,
            }
        )

    return {"subject_rankings": rankings}


def _yearly_eligibility_for_year(yearly_df: pd.DataFrame, year: int) -> Optional[float]:
    """Get eligibility percentage for a specific year (prefers 'All' type)."""
    rows = yearly_df[yearly_df["year"] == year]
    if rows.empty:
        return None
    all_row = rows[rows["candidate_type"].str.lower().isin(["all", "all candidates"])]
    row = all_row.iloc[0] if not all_row.empty else rows.iloc[0]
    return _safe_float(row.get("eligible_percentage"))


def _avg_pass_percentage(subject_df: pd.DataFrame, year: int) -> Optional[float]:
    """Average pass percentage across all subjects for a year."""
    rows = subject_df[subject_df["year"] == year]
    if rows.empty or "pass_percentage" not in rows.columns:
        return None
    return _safe_float(rows["pass_percentage"].mean())


def compare_years(year1: int, year2: int) -> Dict[str, Any]:
    """Compare performance metrics between two years, formatted for CompareYears.jsx."""
    yearly_df = load_table_as_dataframe("yearly")
    province_df = load_table_as_dataframe("province")
    stream_df = load_table_as_dataframe("stream")
    subject_df = load_table_as_dataframe("subject")

    # Find year1 metrics from yearly_df (preferring candidate_type = "School")
    y1_rows = yearly_df[(yearly_df["year"] == year1) & (yearly_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    if y1_rows.empty and not yearly_df.empty:
        y1_rows = yearly_df[yearly_df["year"] == year1]
    
    if not y1_rows.empty:
        y1_row = y1_rows.iloc[0]
        y1_data = {
            "year": year1,
            "no_sat": _safe_int(y1_row.get("no_sat")) or 0,
            "eligible_no": _safe_int(y1_row.get("eligible_no")) or 0,
            "eligible_percentage": _safe_float(y1_row.get("eligible_percentage")) or 0.0,
            "failed_all_percentage": _safe_float(y1_row.get("failed_all_percentage")) or 0.0,
        }
    else:
        y1_data = {
            "year": year1,
            "no_sat": 0,
            "eligible_no": 0,
            "eligible_percentage": 0.0,
            "failed_all_percentage": 0.0,
        }

    # Find year2 metrics from yearly_df (preferring candidate_type = "School")
    y2_rows = yearly_df[(yearly_df["year"] == year2) & (yearly_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    if y2_rows.empty and not yearly_df.empty:
        y2_rows = yearly_df[yearly_df["year"] == year2]
        
    if not y2_rows.empty:
        y2_row = y2_rows.iloc[0]
        y2_data = {
            "year": year2,
            "no_sat": _safe_int(y2_row.get("no_sat")) or 0,
            "eligible_no": _safe_int(y2_row.get("eligible_no")) or 0,
            "eligible_percentage": _safe_float(y2_row.get("eligible_percentage")) or 0.0,
            "failed_all_percentage": _safe_float(y2_row.get("failed_all_percentage")) or 0.0,
        }
    else:
        y2_data = {
            "year": year2,
            "no_sat": 0,
            "eligible_no": 0,
            "eligible_percentage": 0.0,
            "failed_all_percentage": 0.0,
        }

    # Calculate top province for both years (School candidate type)
    prov_df_y1 = province_df[(province_df["year"] == year1) & (province_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    top_prov_y1 = str(prov_df_y1.sort_values("eligible_percentage", ascending=False).iloc[0]["province"]) if not prov_df_y1.empty else "N/A"
    prov_df_y2 = province_df[(province_df["year"] == year2) & (province_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    top_prov_y2 = str(prov_df_y2.sort_values("eligible_percentage", ascending=False).iloc[0]["province"]) if not prov_df_y2.empty else "N/A"
    
    y1_data["top_province"] = top_prov_y1
    y2_data["top_province"] = top_prov_y2

    # Calculate top stream for both years (School candidate type)
    strm_df_y1 = stream_df[(stream_df["year"] == year1) & (stream_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    top_strm_y1 = str(strm_df_y1.sort_values("eligible_percentage", ascending=False).iloc[0]["stream"]) if not strm_df_y1.empty else "N/A"
    strm_df_y2 = stream_df[(stream_df["year"] == year2) & (stream_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    top_strm_y2 = str(strm_df_y2.sort_values("eligible_percentage", ascending=False).iloc[0]["stream"]) if not strm_df_y2.empty else "N/A"

    y1_data["top_stream"] = top_strm_y1
    y2_data["top_stream"] = top_strm_y2

    # Province comparison list
    prov1_data = province_df[(province_df["year"] == year1) & (province_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    prov2_data = province_df[(province_df["year"] == year2) & (province_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    
    prov1_dict = prov1_data.set_index("province")["eligible_percentage"].to_dict() if not prov1_data.empty else {}
    prov2_dict = prov2_data.set_index("province")["eligible_percentage"].to_dict() if not prov2_data.empty else {}
    
    province_comparison = []
    all_provinces = sorted(list(set(prov1_dict.keys()) | set(prov2_dict.keys())))
    for prov in all_provinces:
        p1 = _safe_float(prov1_dict.get(prov))
        p2 = _safe_float(prov2_dict.get(prov))
        diff = _safe_float(p2 - p1) if p1 is not None and p2 is not None else None
        province_comparison.append({
            "province_name": prov,
            f"pct_{year1}": p1,
            f"pct_{year2}": p2,
            "diff": diff
        })

    # Stream comparison list
    strm1_data = stream_df[(stream_df["year"] == year1) & (stream_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    strm2_data = stream_df[(stream_df["year"] == year2) & (stream_df["candidate_type"].str.lower().isin(["school", "school candidates"]))]
    
    strm1_dict = strm1_data.set_index("stream")["eligible_percentage"].to_dict() if not strm1_data.empty else {}
    strm2_dict = strm2_data.set_index("stream")["eligible_percentage"].to_dict() if not strm2_data.empty else {}
    
    stream_comparison = []
    all_streams = sorted(list(set(strm1_dict.keys()) | set(strm2_dict.keys())))
    for stream in all_streams:
        s1 = _safe_float(strm1_dict.get(stream))
        s2 = _safe_float(strm2_dict.get(stream))
        diff = _safe_float(s2 - s1) if s1 is not None and s2 is not None else None
        stream_comparison.append({
            "stream_name": stream,
            f"pct_{year1}": s1,
            f"pct_{year2}": s2,
            "diff": diff
        })

    # Subject comparison list
    subj1_data = subject_df[subject_df["year"] == year1]
    subj2_data = subject_df[subject_df["year"] == year2]
    
    subj1_dict = subj1_data.set_index("subject")["pass_percentage"].to_dict() if not subj1_data.empty else {}
    subj2_dict = subj2_data.set_index("subject")["pass_percentage"].to_dict() if not subj2_data.empty else {}
    
    subject_comparison = []
    all_subjects = sorted(list(set(subj1_dict.keys()) | set(subj2_dict.keys())))
    for subj in all_subjects:
        sb1 = _safe_float(subj1_dict.get(subj))
        sb2 = _safe_float(subj2_dict.get(subj))
        diff = _safe_float(sb2 - sb1) if sb1 is not None and sb2 is not None else None
        subject_comparison.append({
            "subject_name": subj,
            f"pass_{year1}": sb1,
            f"pass_{year2}": sb2,
            "diff": diff
        })

    return {
        "year1": y1_data,
        "year2": y2_data,
        "provinceComparison": province_comparison,
        "streamComparison": stream_comparison,
        "subjectComparison": subject_comparison
    }
