"""
Gold Layer Aggregator - Generate pre-computed aggregate tables.

Creates optimized aggregate tables for:
- Country-level summaries
- Monthly trends
- Category analysis
- Top buyers and suppliers
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import (
    GOLD_AGGREGATES_DIR,
    GOLD_UNIFIED_DIR,
    AGGREGATE_TABLES,
    TOP_N_BUYERS,
    TOP_N_SUPPLIERS,
    COMPRESSION,
)

logger = logging.getLogger(__name__)


def load_unified_dataset(path: str = None) -> pd.DataFrame:
    """Load the unified Gold dataset."""
    if path is None:
        path = f"{GOLD_UNIFIED_DIR}/all_tenders.parquet"

    logger.info(f"Loading unified dataset from {path}...")
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df):,} records")
    return df


def generate_country_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate per-country summary statistics.

    Returns:
        DataFrame with columns:
        - source_country
        - total_records
        - total_value_sum
        - avg_value
        - median_value
        - num_buyers
        - num_suppliers
        - date_range_start
        - date_range_end
    """
    logger.info("Generating country summary...")

    # Group by country
    summary = df.groupby('source_country').agg({
        'ocid': 'count',
        'tender_value_amount': ['sum', 'mean', 'median'],
        'buyer_name': 'nunique',
        'supplier_names': lambda x: len(set([s for sublist in x for s in (sublist if isinstance(sublist, list) else [])])),
        'publication_date': ['min', 'max'],
    }).reset_index()

    # Flatten column names
    summary.columns = [
        'source_country',
        'total_records',
        'total_value_sum',
        'avg_value',
        'median_value',
        'num_buyers',
        'num_suppliers',
        'date_range_start',
        'date_range_end',
    ]

    # Sort by total records descending
    summary = summary.sort_values('total_records', ascending=False)

    logger.info(f"Created summary for {len(summary)} countries")
    return summary


def generate_monthly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate monthly time-series trends.

    Returns:
        DataFrame with columns:
        - year
        - month
        - total_records
        - total_value
        - avg_value
        - num_countries
        - num_buyers
    """
    logger.info("Generating monthly trends...")

    # Group by year, month
    trends = df[df['year'] > 0].groupby(['year', 'month']).agg({
        'ocid': 'count',
        'tender_value_amount': ['sum', 'mean'],
        'source_country': 'nunique',
        'buyer_name': 'nunique',
    }).reset_index()

    # Flatten column names
    trends.columns = [
        'year',
        'month',
        'total_records',
        'total_value',
        'avg_value',
        'num_countries',
        'num_buyers',
    ]

    # Sort by year, month
    trends = trends.sort_values(['year', 'month'])

    logger.info(f"Created trends for {len(trends)} month periods")
    return trends


def generate_category_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate procurement category breakdown by country.

    Returns:
        DataFrame with columns:
        - source_country
        - procurement_category_standardized
        - total_records
        - total_value
        - avg_value
    """
    logger.info("Generating category analysis...")

    # Group by country and category
    analysis = df.groupby(['source_country', 'procurement_category_standardized']).agg({
        'ocid': 'count',
        'tender_value_amount': ['sum', 'mean'],
    }).reset_index()

    # Flatten column names
    analysis.columns = [
        'source_country',
        'procurement_category_standardized',
        'total_records',
        'total_value',
        'avg_value',
    ]

    # Sort by country, then records
    analysis = analysis.sort_values(['source_country', 'total_records'], ascending=[True, False])

    logger.info(f"Created analysis for {len(analysis)} country-category combinations")
    return analysis


def generate_top_buyers(df: pd.DataFrame, top_n: int = TOP_N_BUYERS) -> pd.DataFrame:
    """
    Generate top buyers by transaction count.

    Args:
        df: Unified dataset
        top_n: Number of top buyers to return

    Returns:
        DataFrame with columns:
        - buyer_name
        - source_country
        - total_records
        - total_value
        - avg_value
    """
    logger.info(f"Generating top {top_n} buyers...")

    # Filter out empty buyer names
    df_filtered = df[df['buyer_name'] != ''].copy()

    # Group by buyer and country
    buyers = df_filtered.groupby(['buyer_name', 'source_country']).agg({
        'ocid': 'count',
        'tender_value_amount': ['sum', 'mean'],
    }).reset_index()

    # Flatten column names
    buyers.columns = [
        'buyer_name',
        'source_country',
        'total_records',
        'total_value',
        'avg_value',
    ]

    # Sort by total records and take top N
    buyers = buyers.sort_values('total_records', ascending=False).head(top_n)

    logger.info(f"Created top {len(buyers)} buyers list")
    return buyers


def generate_top_suppliers(df: pd.DataFrame, top_n: int = TOP_N_SUPPLIERS) -> pd.DataFrame:
    """
    Generate top suppliers by transaction count.

    Args:
        df: Unified dataset
        top_n: Number of top suppliers to return

    Returns:
        DataFrame with columns:
        - supplier_name
        - source_country
        - total_records
        - total_value
        - avg_value
    """
    logger.info(f"Generating top {top_n} suppliers...")

    # Explode supplier_names (convert list to rows)
    df_exploded = df.explode('supplier_names')
    df_filtered = df_exploded[df_exploded['supplier_names'] != ''].copy()

    # Group by supplier and country
    suppliers = df_filtered.groupby(['supplier_names', 'source_country']).agg({
        'ocid': 'count',
        'tender_value_amount': ['sum', 'mean'],
    }).reset_index()

    # Flatten column names
    suppliers.columns = [
        'supplier_name',
        'source_country',
        'total_records',
        'total_value',
        'avg_value',
    ]

    # Sort by total records and take top N
    suppliers = suppliers.sort_values('total_records', ascending=False).head(top_n)

    logger.info(f"Created top {len(suppliers)} suppliers list")
    return suppliers


def generate_all_aggregates(unified_path: str = None) -> dict:
    """
    Generate all aggregate tables.

    Args:
        unified_path: Path to unified dataset (default: GOLD_UNIFIED_DIR/all_tenders.parquet)

    Returns:
        Dictionary mapping table name to DataFrame
    """
    logger.info("=" * 60)
    logger.info("GOLD LAYER - AGGREGATE GENERATION")
    logger.info("=" * 60)

    # Load unified dataset
    df = load_unified_dataset(unified_path)

    # Create output directory
    Path(GOLD_AGGREGATES_DIR).mkdir(parents=True, exist_ok=True)

    aggregates = {}

    # Generate each aggregate
    logger.info("\n1. Country Summary...")
    aggregates['country_summary'] = generate_country_summary(df)

    logger.info("\n2. Monthly Trends...")
    aggregates['monthly_trends'] = generate_monthly_trends(df)

    logger.info("\n3. Category Analysis...")
    aggregates['category_analysis'] = generate_category_analysis(df)

    logger.info("\n4. Top Buyers...")
    aggregates['top_buyers'] = generate_top_buyers(df)

    logger.info("\n5. Top Suppliers...")
    aggregates['top_suppliers'] = generate_top_suppliers(df)

    # Write all aggregates to files
    logger.info("\nWriting aggregate tables...")
    for name, agg_df in aggregates.items():
        config = AGGREGATE_TABLES[name]
        output_path = f"{GOLD_AGGREGATES_DIR}/{config['filename']}"

        agg_df.to_parquet(output_path, compression=COMPRESSION, index=False)
        logger.info(f"  ✓ {output_path} ({len(agg_df):,} rows)")

    logger.info("\n" + "=" * 60)
    logger.info("AGGREGATE GENERATION COMPLETE")
    logger.info("=" * 60)

    return aggregates


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Generate all aggregates
    aggs = generate_all_aggregates()
    print(f"\n✓ Generated {len(aggs)} aggregate tables")
