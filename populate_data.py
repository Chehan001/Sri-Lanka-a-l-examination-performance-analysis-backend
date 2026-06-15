import os
import sys
import pandas as pd

# Add backend to path so we can import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pdf_parser import parse_al_report_pdf
from services.csv_cleaner import clean_dataframe
from services.csv_combiner import ensure_directories, update_master_csv
from services.database_service import init_db, save_dataframe_to_db

VALID_DATA_TYPES = ["yearly", "province", "district", "stream", "subject"]

def main():
    pdf_dir = r"c:\Users\chehan\Desktop\AL Performance Analysis\reports folders"
    
    # Initialize DB & Directories
    ensure_directories()
    init_db()
    
    print("Starting automatic import of official AL reports...")
    
    for filename in sorted(os.listdir(pdf_dir)):
        if filename.endswith(".pdf"):
            year = int(filename.split(".")[0])
            pdf_path = os.path.join(pdf_dir, filename)
            
            print(f"Importing {filename} for year {year}...")
            try:
                with open(pdf_path, "rb") as f:
                    content = f.read()
                
                extracted = parse_al_report_pdf(content, year)
                total_rows = 0
                
                for data_type in VALID_DATA_TYPES:
                    raw_df = extracted.get(data_type, pd.DataFrame())
                    if raw_df is None or raw_df.empty:
                        continue
                    
                    cleaned_df = clean_dataframe(data_type, raw_df, year)
                    processed_path = update_master_csv(data_type, cleaned_df, year)
                    rows_saved = save_dataframe_to_db(data_type, cleaned_df, year)
                    total_rows += rows_saved
                
                print(f"  Successfully imported year {year}: saved {total_rows} rows.")
            except Exception as e:
                print(f"  Error importing {filename}: {e}")

if __name__ == "__main__":
    main()
