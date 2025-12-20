"""
Gold Layer Quality Reports.

Generate quality reports for:
- Deduplication statistics
- Coverage/completeness analysis
- Data validation results
"""

import logging
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

from .config import GOLD_QUALITY_DIR, GOLD_UNIFIED_DIR

logger = logging.getLogger(__name__)


def generate_deduplication_report(df: pd.DataFrame) -> dict:
    """Generate deduplication statistics."""
    report = {
        'total_records': len(df),
        'unique_ocids': df['ocid'].nunique(),
        'duplicate_ocids': len(df) - df['ocid'].nunique(),
        'deduplication_rate': 1 - (df['ocid'].nunique() / len(df)) if len(df) > 0 else 0,
    }
    return report


def generate_coverage_report(df: pd.DataFrame) -> dict:
    """Generate field completeness/coverage report."""
    report = {
        'total_records': len(df),
        'field_completeness': {},
    }

    # Calculate completeness for each field
    for col in df.columns:
        if col.startswith('_'):  # Skip internal columns
            continue

        non_null = df[col].notna().sum()
        non_empty = 0

        # Handle different column types safely
        try:
            if df[col].dtype == 'object':
                # Check if column contains lists by testing a sample
                sample_val = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None
                if isinstance(sample_val, list):
                    # For list columns, count non-empty lists
                    non_empty = df[col].apply(lambda x: isinstance(x, list) and len(x) > 0).sum()
                else:
                    # Try string comparison, fallback to non_null if it fails
                    try:
                        non_empty = (df[col] != '').sum()
                    except (ValueError, TypeError):
                        non_empty = non_null
            else:
                non_empty = non_null
        except (ValueError, TypeError, IndexError):
            # If any error, use non_null count
            non_empty = non_null

        report['field_completeness'][col] = {
            'non_null': int(non_null),
            'non_empty': int(non_empty),
            'completeness_pct': round((non_empty / len(df)) * 100, 2) if len(df) > 0 else 0
        }

    return report


def generate_validation_report(df: pd.DataFrame) -> dict:
    """Generate data validation report."""
    report = {
        'total_records': len(df),
        'quality_flags': df['date_quality_flag'].value_counts().to_dict(),
        'avg_completeness_score': round(df['data_completeness_score'].mean(), 4),
        'completeness_distribution': {
            'excellent (>0.9)': len(df[df['data_completeness_score'] > 0.9]),
            'good (0.7-0.9)': len(df[(df['data_completeness_score'] >= 0.7) & (df['data_completeness_score'] <= 0.9)]),
            'fair (0.5-0.7)': len(df[(df['data_completeness_score'] >= 0.5) & (df['data_completeness_score'] < 0.7)]),
            'poor (<0.5)': len(df[df['data_completeness_score'] < 0.5]),
        },
        'records_with_value': int((df['has_value']).sum()),
        'records_with_award': int((df['has_award']).sum()),
        'future_dates': int((df['is_future_date']).sum()),
    }
    return report


def generate_all_quality_reports(unified_path: str = None) -> dict:
    """
    Generate all quality reports.

    Args:
        unified_path: Path to unified dataset

    Returns:
        Dictionary with all quality reports
    """
    logger.info("=" * 60)
    logger.info("GOLD LAYER - QUALITY REPORT GENERATION")
    logger.info("=" * 60)

    # Load dataset
    if unified_path is None:
        unified_path = f"{GOLD_UNIFIED_DIR}/all_tenders.parquet"

    logger.info(f"Loading dataset from {unified_path}...")
    df = pd.read_parquet(unified_path)
    logger.info(f"Loaded {len(df):,} records")

    # Generate reports
    logger.info("\n1. Deduplication Report...")
    dedup_report = generate_deduplication_report(df)

    logger.info("2. Coverage Report...")
    coverage_report = generate_coverage_report(df)

    logger.info("3. Validation Report...")
    validation_report = generate_validation_report(df)

    # Combine all reports
    full_report = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'dataset_path': unified_path,
        'deduplication': dedup_report,
        'coverage': coverage_report,
        'validation': validation_report,
    }

    # Write to file
    Path(GOLD_QUALITY_DIR).mkdir(parents=True, exist_ok=True)
    output_path = f"{GOLD_QUALITY_DIR}/quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_path, 'w') as f:
        json.dump(full_report, f, indent=2)

    logger.info(f"\n✓ Quality report saved to {output_path}")
    logger.info("=" * 60)

    return full_report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    generate_all_quality_reports()
