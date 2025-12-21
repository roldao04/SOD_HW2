"""
Parquet writer for Henrique & Monteiro Silver layer

Writes transformed data to partitioned Parquet files.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import logging
from datetime import datetime
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


class HenriqueMonteiroParquetWriter:
    """Writes Silver layer data to Parquet with partitioning"""
    
    def __init__(self, output_path: str = None):
        self.output_path = output_path or config.OUTPUT_BASE_PATH
        
    def write_silver_layer(self, df: pd.DataFrame) -> dict:
        """
        Write Silver layer to partitioned Parquet files
        
        Partition structure: country/year/month/
        """
        if df.empty:
            logger.warning("No data to write")
            return {'files_written': 0, 'records_written': 0}
        
        logger.info(f"Writing {len(df):,} records to Silver layer...")
        
        # Ensure date column
        df['publication_date'] = pd.to_datetime(df['publication_date'], errors='coerce')
        
        # Add partition columns
        df['year'] = df['publication_date'].dt.year.fillna(2024).astype(int)
        df['month'] = df['publication_date'].dt.month.fillna(1).astype(int)
        df['country'] = df['source_country'].fillna('PT')
        
        stats = {
            'files_written': 0,
            'records_written': 0,
            'partitions': []
        }
        
        # Group by partition keys
        for (country, year, month), group in df.groupby(['country', 'year', 'month']):
            # Create partition directory
            partition_path = os.path.join(
                self.output_path,
                country.lower(),
                str(year),
                f"{month:02d}"
            )
            os.makedirs(partition_path, exist_ok=True)
            
            # Remove partition columns from data
            output_df = group.drop(columns=['year', 'month', 'country'])
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"tenders_{timestamp}.parquet"
            filepath = os.path.join(partition_path, filename)
            
            # Write Parquet
            output_df.to_parquet(
                filepath,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            stats['files_written'] += 1
            stats['records_written'] += len(output_df)
            stats['partitions'].append({
                'country': country,
                'year': year,
                'month': month,
                'records': len(output_df),
                'file': filepath
            })
            
            logger.info(f"  Wrote {len(output_df):,} records to {country}/{year}/{month:02d}")
        
        logger.info(f"✓ Wrote {stats['files_written']} files, {stats['records_written']:,} total records")
        
        return stats
