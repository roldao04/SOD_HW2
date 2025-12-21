"""
Main entry point for Henrique & Monteiro data processing

Transforms partner data to Silver layer format.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.processing.henrique_monteiro.transformer import HenriqueMonteiroTransformer
from src.processing.henrique_monteiro.parquet_writer import HenriqueMonteiroParquetWriter
from src.processing.henrique_monteiro import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main processing pipeline"""
    logger.info("=" * 60)
    logger.info(f"Processing {config.SOURCE_DISPLAY_NAME}")
    logger.info("=" * 60)
    
    try:
        # Transform
        transformer = HenriqueMonteiroTransformer()
        silver_df = transformer.transform()
        
        if silver_df.empty:
            logger.error("❌ No data produced by transformer")
            return False
        
        # Write to Silver layer
        writer = HenriqueMonteiroParquetWriter()
        stats = writer.write_silver_layer(silver_df)
        
        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Processing Complete")
        logger.info("=" * 60)
        logger.info(f"Source: {config.SOURCE_DISPLAY_NAME}")
        logger.info(f"Files written: {stats['files_written']}")
        logger.info(f"Records written: {stats['records_written']:,}")
        logger.info(f"Output location: {config.OUTPUT_BASE_PATH}")
        logger.info("")
        logger.info("Partitions:")
        for partition in stats['partitions']:
            logger.info(f"  {partition['country']}/{partition['year']}/{partition['month']:02d}: "
                       f"{partition['records']:,} records")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Verify: make stats")
        logger.info("  2. Generate Gold layer: make gold-layer")
        logger.info("  3. Upload to MinIO: make gold-upload")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
