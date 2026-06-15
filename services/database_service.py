import os
from typing import List, Optional

import pandas as pd
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Path to the SQLite database file (in the backend root folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# SQLAlchemy table models – one table per CSV category
# ---------------------------------------------------------------------------

class YearlyMaster(Base):
    __tablename__ = "yearly_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    candidate_type = Column(String, nullable=False)
    no_sat = Column(Integer)
    eligible_no = Column(Integer)
    eligible_percentage = Column(Float)
    three_a_no = Column(Integer)
    three_a_percentage = Column(Float)
    failed_all_no = Column(Integer)
    failed_all_percentage = Column(Float)


class ProvinceMaster(Base):
    __tablename__ = "province_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    candidate_type = Column(String, nullable=False)
    province = Column(String, nullable=False)
    no_sat = Column(Integer)
    eligible_no = Column(Integer)
    eligible_percentage = Column(Float)
    three_a_no = Column(Integer)
    three_a_percentage = Column(Float)
    failed_all_no = Column(Integer)
    failed_all_percentage = Column(Float)


class DistrictMaster(Base):
    __tablename__ = "district_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    candidate_type = Column(String, nullable=False)
    district = Column(String, nullable=False)
    no_sat = Column(Integer)
    eligible_no = Column(Integer)
    eligible_percentage = Column(Float)


class StreamMaster(Base):
    __tablename__ = "stream_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    candidate_type = Column(String, nullable=False)
    stream = Column(String, nullable=False)
    no_sat = Column(Integer)
    eligible_no = Column(Integer)
    eligible_percentage = Column(Float)
    three_a_no = Column(Integer)
    three_a_percentage = Column(Float)
    failed_all_no = Column(Integer)
    failed_all_percentage = Column(Float)


class SubjectMaster(Base):
    __tablename__ = "subject_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    subject_no = Column(Integer)
    subject = Column(String, nullable=False)
    no_sat = Column(Integer)
    a_no = Column(Integer)
    a_percentage = Column(Float)
    b_no = Column(Integer)
    b_percentage = Column(Float)
    c_no = Column(Integer)
    c_percentage = Column(Float)
    s_no = Column(Integer)
    s_percentage = Column(Float)
    pass_no = Column(Integer)
    pass_percentage = Column(Float)
    fail_no = Column(Integer)
    fail_percentage = Column(Float)


# Map data_type string to SQLAlchemy model class
TABLE_MAP = {
    "yearly": YearlyMaster,
    "province": ProvinceMaster,
    "district": DistrictMaster,
    "stream": StreamMaster,
    "subject": SubjectMaster,
}


def init_db() -> None:
    """Create all database tables if they do not exist yet."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _delete_year_rows(db: Session, model, year: int) -> None:
    """Remove existing rows for a given year before inserting fresh data."""
    db.query(model).filter(model.year == year).delete()
    db.commit()


def save_dataframe_to_db(data_type: str, df: pd.DataFrame, year: int) -> int:
    """
    Save a cleaned DataFrame into the correct table.
    Replaces any existing data for the same year in that table.
    Returns the number of rows saved.
    """
    model = TABLE_MAP.get(data_type)
    if model is None:
        raise ValueError(f"Unknown data_type: {data_type}")

    db = SessionLocal()
    try:
        # Replace old data for this year to avoid duplicates on re-upload
        _delete_year_rows(db, model, year)

        records = df.to_dict(orient="records")
        for record in records:
            # Ensure year is set even if missing from the CSV
            record["year"] = year
            db.add(model(**record))

        db.commit()
        return len(records)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_table_as_dataframe(data_type: str) -> pd.DataFrame:
    """Load an entire table into a pandas DataFrame."""
    table_name = f"{data_type}_master"
    with engine.connect() as conn:
        try:
            return pd.read_sql(text(f"SELECT * FROM {table_name}"), conn)
        except Exception:
            return pd.DataFrame()


def get_distinct_years() -> List[int]:
    """Return sorted list of years found in the yearly_master table."""
    df = load_table_as_dataframe("yearly")
    if df.empty or "year" not in df.columns:
        return []
    return sorted(df["year"].dropna().unique().astype(int).tolist())


def get_latest_year() -> Optional[int]:
    """Return the most recent year in the database, or None."""
    years = get_distinct_years()
    return years[-1] if years else None
