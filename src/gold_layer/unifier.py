"""
Gold Layer Unifier - Merge Silver sources into unified dataset.

Combines OCP, TED, and BASE Portugal data with:
- Category standardization
- Derived fields (year, month, quality scores)
- Quality flags
- Partitioned storage
"""

import logging
import glob
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import (
    CATEGORY_STANDARDIZATION_MAP,
    PARTITION_COLS,
    COMPRESSION,
    DEFAULT_SILVER_DIR,
    GOLD_UNIFIED_DIR,
    REQUIRED_FIELDS,
    IMPORTANT_FIELDS,
    MIN_VALID_DATE,
    MAX_VALID_DATE,
)

logger = logging.getLogger(__name__)


def load_silver_source(source_name: str, silver_dir: str = DEFAULT_SILVER_DIR) -> pd.DataFrame:
    """
    Load all parquet files from a Silver source.

    Args:
        source_name: Name of source ('open_contracting_partnership', 'ted', 'base_portugal', 'henrique_monteiro')
        silver_dir: Base directory for Silver data

    Returns:
        Combined DataFrame with all records from the source
    """
    pattern = f"{silver_dir}/{source_name}/**/*.parquet"
    files = glob.glob(pattern, recursive=True)

    # Filter out non-data files (processing state, quality reports)
    files = [f for f in files if 'processing_state' not in f and 'quality' not in f]

    if not files:
        logger.warning(f"No parquet files found for source: {source_name}")
        return pd.DataFrame()

    logger.info(f"Loading {len(files)} files from {source_name}...")

    dfs = []
    for file in files:
        try:
            df = pd.read_parquet(file)
            dfs.append(df)
        except Exception as e:
            logger.warning(f"Failed to read {file}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(combined):,} records from {source_name}")

    return combined


def standardize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize procurement categories to English.

    Args:
        df: DataFrame with 'procurement_category' column

    Returns:
        DataFrame with added 'procurement_category_original' and
        'procurement_category_standardized' columns
    """
    # Preserve original
    df['procurement_category_original'] = df['procurement_category'].copy()

    # Standardize
    df['procurement_category_standardized'] = df['procurement_category'].map(
        CATEGORY_STANDARDIZATION_MAP
    ).fillna('')

    # Log unmapped categories
    unmapped = df[
        (df['procurement_category'] != '') &
        (df['procurement_category_standardized'] == '')
    ]['procurement_category'].unique()

    if len(unmapped) > 0:
        logger.warning(f"Found {len(unmapped)} unmapped categories: {list(unmapped)[:10]}")

    return df


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived fields for analytics.

    Args:
        df: DataFrame with Silver schema

    Returns:
        DataFrame with additional derived fields
    """
    # Convert publication_date to datetime for extraction
    df['publication_date_dt'] = pd.to_datetime(df['publication_date'], errors='coerce')

    # Extract year, month, quarter
    df['year'] = df['publication_date_dt'].dt.year.fillna(0).astype(int)
    df['month'] = df['publication_date_dt'].dt.month.fillna(0).astype(int)
    df['quarter'] = df['publication_date_dt'].dt.quarter.fillna(0).astype(int)

    # Date quality flags
    today = pd.Timestamp.today().normalize()
    min_date = pd.Timestamp(MIN_VALID_DATE)
    max_date = pd.Timestamp(MAX_VALID_DATE)

    def get_date_quality_flag(date_val):
        if pd.isna(date_val):
            return 'missing'
        elif date_val > max_date:
            return 'future'
        elif date_val < min_date:
            return 'past'
        else:
            return 'valid'

    df['date_quality_flag'] = df['publication_date_dt'].apply(get_date_quality_flag)
    df['is_future_date'] = df['publication_date_dt'] > today

    # Value flags
    df['has_value'] = df['tender_value_amount'] > 0
    df['has_award'] = df['award_amount'] > 0

    # Data completeness score (0-1)
    df['data_completeness_score'] = df.apply(calculate_completeness_score, axis=1)

    # Drop temporary datetime column
    df = df.drop(columns=['publication_date_dt'])

    return df


def calculate_completeness_score(row: pd.Series) -> float:
    """
    Calculate data completeness score for a record.

    Score based on:
    - Required fields (weight=1.0)
    - Important fields (weight=0.5)

    Args:
        row: DataFrame row

    Returns:
        Completeness score between 0 and 1
    """
    total_weight = 0.0
    filled_weight = 0.0

    # Check required fields (weight=1.0)
    for field in REQUIRED_FIELDS:
        total_weight += 1.0
        if row.get(field) and row[field] != '' and not pd.isna(row[field]):
            filled_weight += 1.0

    # Check important fields (weight=0.5)
    for field in IMPORTANT_FIELDS:
        total_weight += 0.5
        if row.get(field) and row[field] != '' and not pd.isna(row[field]):
            if isinstance(row[field], (int, float)):
                if row[field] > 0:
                    filled_weight += 0.5
            else:
                filled_weight += 0.5

    return filled_weight / total_weight if total_weight > 0 else 0.0


def create_unified_dataset(
    silver_dir: str = DEFAULT_SILVER_DIR,
    output_path: str = None,
    partition: bool = True
) -> pd.DataFrame:
    """
    Create unified Gold dataset from all Silver sources.

    Args:
        silver_dir: Base directory for Silver data
        output_path: Output path for unified parquet (default: GOLD_UNIFIED_DIR/all_tenders.parquet)
        partition: Whether to partition output by country/year/month

    Returns:
        Unified DataFrame
    """
    logger.info("=" * 60)
    logger.info("GOLD LAYER - UNIFIED DATASET CREATION")
    logger.info("=" * 60)

    # Load all sources
    logger.info("\n1. Loading Silver sources...")

    ocp_df = load_silver_source('open_contracting_partnership', silver_dir)
    ted_df = load_silver_source('ted', silver_dir)
    portugal_df = load_silver_source('base_portugal', silver_dir)
    hm_df = load_silver_source('henrique_monteiro', silver_dir)

    # Add source tags
    logger.info("\n2. Adding source tags...")
    ocp_df['source'] = 'ocp'
    ted_df['source'] = 'ted'
    portugal_df['source'] = 'base_portugal'
    hm_df['source'] = 'henrique_monteiro'

    # Combine all sources
    logger.info("\n3. Combining sources...")
    all_dfs = [df for df in [ocp_df, ted_df, portugal_df, hm_df] if not df.empty]

    if not all_dfs:
        logger.error("No data found in any Silver source!")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Combined: {len(combined):,} records")

    # Standardize categories
    logger.info("\n4. Standardizing categories...")
    before_std = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M before standardize: {before_std}")
    combined = standardize_categories(combined)
    after_std = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M after standardize: {after_std}")

    # Add derived fields
    logger.info("\n5. Adding derived fields...")
    before_derived = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M before derived: {before_derived}")
    combined = add_derived_fields(combined)
    after_derived = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M after derived: {after_derived}")

    # Deduplicate by OCID + source_publication_id
    logger.info("\n6. Deduplicating...")
    before_dedup_hm = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M before dedup: {before_dedup_hm}")
    pre_dedup = len(combined)
    combined = combined.drop_duplicates(
        subset=['ocid', 'source_publication_id'],
        keep='first'
    )
    after_dedup_hm = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M after dedup: {after_dedup_hm}")
    duplicates = pre_dedup - len(combined)
    logger.info(f"Removed {duplicates:,} duplicates ({len(combined):,} unique records)")

    # Write output
    if output_path is None:
        output_path = f"{GOLD_UNIFIED_DIR}/all_tenders.parquet"

    Path(GOLD_UNIFIED_DIR).mkdir(parents=True, exist_ok=True)

    logger.info(f"\n7. Writing to {output_path}...")
    before_write_hm = len(combined[combined['source'] == 'henrique_monteiro'])
    logger.info(f"   H&M before write: {before_write_hm}")
    logger.info(f"   Total records to write: {len(combined):,}")
    
    # Convert datetime columns to ISO strings for consistent Parquet schema
    # This prevents PyArrow type errors when mixing Timestamp and string
    date_columns = [
        'publication_date', 'deadline_date', 'award_date',
        'contract_start_date', 'contract_end_date', 'extraction_date'
    ]
    for col in date_columns:
        if col in combined.columns:
            # Convert to datetime first (handles mixed types), then to ISO string
            combined[col] = pd.to_datetime(combined[col], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # Drop the temporary datetime column used for derived fields
    if 'publication_date_dt' in combined.columns:
        combined = combined.drop(columns=['publication_date_dt'])

    # Write as single file to avoid schema inconsistencies
    # Note: Partitioning disabled due to PyArrow type incompatibility across partitions
    combined.to_parquet(
        output_path,
        compression=COMPRESSION,
        index=False
    )
    logger.info(f"Wrote unified dataset to {output_path} (~{len(combined):,} records)")

    # Summary statistics
    logger.info("\n" + "=" * 60)
    logger.info("UNIFIED DATASET SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total records: {len(combined):,}")
    logger.info(f"Date range: {combined['publication_date'].min()} to {combined['publication_date'].max()}")
    logger.info(f"\nSources:")
    logger.info(combined['source'].value_counts().to_string())
    logger.info(f"\nCountries: {combined['source_country'].nunique()}")
    logger.info(f"\nTop 10 countries:")
    logger.info(combined['source_country'].value_counts().head(10).to_string())
    logger.info(f"\nStandardized categories:")
    logger.info(combined['procurement_category_standardized'].value_counts().to_string())
    logger.info(f"\nDate quality:")
    logger.info(combined['date_quality_flag'].value_counts().to_string())
    logger.info(f"\nAverage completeness score: {combined['data_completeness_score'].mean():.2%}")
    logger.info("=" * 60)

    return combined


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create unified dataset
    df = create_unified_dataset()
    print(f"\n✓ Created unified dataset with {len(df):,} records")
