#!/usr/bin/env python3
"""
Gold Layer CLI - Main entry point for Gold layer operations.

Commands:
  --all: Build complete gold layer (unified + aggregates + quality)
  --unified: Create unified dataset only
  --aggregates: Generate aggregates only
  --quality: Generate quality reports only
  --stats: Show gold layer statistics
"""

import sys
import logging
import argparse

from .unifier import create_unified_dataset
from .aggregator import generate_all_aggregates
from .quality import generate_all_quality_reports
from .config import GOLD_UNIFIED_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def show_stats():
    """Show Gold layer statistics."""
    import pandas as pd
    from pathlib import Path

    print("\n" + "=" * 60)
    print(" GOLD LAYER STATISTICS")
    print("=" * 60)

    unified_path = f"{GOLD_UNIFIED_DIR}/all_tenders.parquet"

    if not Path(unified_path).exists():
        print("\n✗ Unified dataset not found.")
        print("  Run: python -m src.gold_layer.main --unified")
        return

    try:
        df = pd.read_parquet(unified_path)

        print(f"\n📊 Unified Dataset: {unified_path}")
        print(f"   Total records: {len(df):,}")
        print(f"   Date range: {df['publication_date'].min()} to {df['publication_date'].max()}")
        print(f"\n📍 Countries: {df['source_country'].nunique()}")
        print("\n   Top 10 countries:")
        for country, count in df['source_country'].value_counts().head(10).items():
            print(f"     {country}: {count:,}")

        print(f"\n📁 Sources:")
        for source, count in df['source'].value_counts().items():
            print(f"     {source}: {count:,}")

        print(f"\n📂 Categories:")
        for cat, count in df['procurement_category_standardized'].value_counts().head(5).items():
            if cat:
                print(f"     {cat}: {count:,}")

        print(f"\n⭐ Quality:")
        print(f"     Average completeness: {df['data_completeness_score'].mean():.2%}")
        print(f"     Valid dates: {(df['date_quality_flag'] == 'valid').sum():,}")
        print(f"     Future dates: {df['is_future_date'].sum():,}")

    except Exception as e:
        print(f"\n✗ Error loading statistics: {e}")

    print("=" * 60 + "\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Gold Layer - Unified procurement data processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build complete gold layer
  python -m src.gold_layer.main --all

  # Create unified dataset only
  python -m src.gold_layer.main --unified

  # Generate aggregates only (requires unified dataset)
  python -m src.gold_layer.main --aggregates

  # Show statistics
  python -m src.gold_layer.main --stats
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Build complete gold layer (unified + aggregates + quality)')
    parser.add_argument('--unified', action='store_true',
                        help='Create unified dataset only')
    parser.add_argument('--aggregates', action='store_true',
                        help='Generate aggregates only')
    parser.add_argument('--quality', action='store_true',
                        help='Generate quality reports only')
    parser.add_argument('--stats', action='store_true',
                        help='Show gold layer statistics')

    args = parser.parse_args()

    try:
        if args.stats:
            show_stats()

        elif args.all:
            logger.info("Building complete gold layer...")
            df = create_unified_dataset()
            aggregates = generate_all_aggregates()
            quality = generate_all_quality_reports()
            print(f"\n✓ Gold layer complete: {len(df):,} records")

        elif args.unified:
            logger.info("Creating unified dataset...")
            df = create_unified_dataset()
            print(f"\n✓ Unified dataset created: {len(df):,} records")

        elif args.aggregates:
            logger.info("Generating aggregates...")
            aggregates = generate_all_aggregates()
            print(f"\n✓ Generated {len(aggregates)} aggregate tables")

        elif args.quality:
            logger.info("Generating quality reports...")
            quality = generate_all_quality_reports()
            print(f"\n✓ Quality reports generated")

        else:
            parser.print_help()
            sys.exit(1)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
