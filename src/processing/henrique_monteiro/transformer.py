"""
Transformer for Henrique & Monteiro data to Silver layer

Merges tenders, buyers, lots via relationship tables and maps to unified schema.
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os

from . import config

logger = logging.getLogger(__name__)


class HenriqueMonteiroTransformer:
    """Transforms H&M partner data to Silver layer format"""
    
    def __init__(self):
        self.source_name = config.SOURCE_NAME
        
    def load_source_data(self) -> Dict[str, pd.DataFrame]:
        """Load all H&M parquet files"""
        logger.info(f"Loading data from {config.INPUT_PATH}")
        
        data = {}
        files = {
            'tenders': 'tenders.parquet',
            'buyers': 'buyers.parquet',
            'lots': 'lots.parquet',
            'tender_buyer': 'tender_buyer_relationships.parquet',
            'tender_lot': 'tender_lot_relationships.parquet'
        }
        
        for key, filename in files.items():
            path = os.path.join(config.INPUT_PATH, filename)
            if os.path.exists(path):
                data[key] = pd.read_parquet(path)
                logger.info(f"  Loaded {key}: {len(data[key]):,} records")
            else:
                logger.warning(f"  File not found: {filename}")
                data[key] = pd.DataFrame()
        
        return data
    
    def merge_relationships(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Merge tenders with buyers and lots via relationship tables"""
        logger.info("Merging relationships...")
        
        # Start with tenders
        df = data['tenders'].copy()
        
        # Merge with buyers (via tender_buyer relationships)
        if not data['tender_buyer'].empty and not data['buyers'].empty:
            # Join tender_buyer relationships
            df = df.merge(
                data['tender_buyer'],
                left_on='tender_id',
                right_on='tender_id',
                how='left'
            )
            
            # Join buyer details
            df = df.merge(
                data['buyers'],
                left_on='buyer_id',
                right_on='buyer_id',
                how='left',
                suffixes=('', '_buyer')
            )
            logger.info(f"  Merged buyers: {df['buyer_id'].notna().sum():,} tenders have buyers")
        
        # Merge with lots (via tender_lot relationships) - take first lot per tender
        if not data['tender_lot'].empty and not data['lots'].empty:
            # Get first lot per tender
            first_lots = data['tender_lot'].groupby('tender_id').first().reset_index()
            
            # Join lot details
            lots_with_details = first_lots.merge(
                data['lots'],
                on='lot_id',
                how='left'
            )
            
            df = df.merge(
                lots_with_details[['tender_id', 'lot_status', 'lot_estimatedPrice', 'cpv_code', 'estimated_value']],
                on='tender_id',
                how='left',
                suffixes=('', '_lot')
            )
            logger.info(f"  Merged lots: {df['lot_status'].notna().sum():,} tenders have lot info")
        
        return df
    
    def map_to_silver_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map merged data to unified Silver schema"""
        logger.info("Mapping to Silver schema...")
        
        # Create output dataframe with Silver schema
        output = pd.DataFrame()
        
        # Map each field according to config
        output['tender_id'] = df['tender_id']
        
        # Generate OCID (Open Contracting ID) - format: ocds-{source}-{tender_id}
        output['ocid'] = 'ocds-henrique_monteiro-' + df['tender_id'].astype(str)
        
        # Source publication ID - use tender_id as publication identifier
        output['source_publication_id'] = df['tender_id'].astype(str)
        
        output['source'] = config.SOURCE_NAME
        output['source_country'] = 'PT'  # Portugal
        output['tender_title'] = df['tender_title']
        output['tender_description'] = df.get('tender_supplyType', None)
        
        # Status from lot or default
        output['tender_status'] = df.get('lot_status', 'ANNOUNCED')
        
        # Value - prefer lot estimated value, fallback to tender estimated price
        output['tender_value_amount'] = df.get('estimated_value', df.get('tender_estimatedPrice', 0.0))
        output['tender_value_currency'] = 'EUR'
        
        # Dates
        output['publication_date'] = pd.to_datetime(df.get('publication_date'), errors='coerce')
        output['deadline_date'] = pd.to_datetime(df.get('tender_bidDeadline'), errors='coerce')
        output['award_date'] = None
        output['contract_start_date'] = None
        output['contract_end_date'] = None
        
        # Buyer info
        output['buyer_id'] = df.get('buyer_id', None)
        output['buyer_name'] = df.get('buyer_name', None)
        output['buyer_type'] = df.get('buyer_buyerType', None)
        
        # Supplier info (not available in H&M data)
        output['supplier_id'] = None
        output['supplier_name'] = None
        output['supplier_country'] = None
        
        # Procurement details
        output['procurement_method'] = df.get('tender_procedureType', None)
        output['procurement_category'] = df.get('main_nature', 'SUPPLIES')
        
        # CPV - prefer from lot, fallback to tender
        output['cpv_code'] = df.get('cpv_code_lot', df.get('tender_mainCpv', None))
        output['cpv_description'] = None
        
        # Contract details
        output['contract_type'] = df.get('tender_supplyType', None)
        output['is_framework_agreement'] = False
        output['number_of_offers'] = None
        
        # Metadata
        output['extraction_date'] = pd.to_datetime(df.get('ingestion_timestamp', datetime.now()))
        
        logger.info(f"  Mapped {len(output):,} records to Silver schema")
        
        return output
    
    def validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality and clean"""
        logger.info("Validating and cleaning data...")
        
        initial_count = len(df)
        
        # Remove records without required fields
        for field in config.REQUIRED_FIELDS:
            before = len(df)
            df = df[df[field].notna()]
            removed = before - len(df)
            if removed > 0:
                logger.warning(f"  Removed {removed:,} records missing {field}")
        
        # Remove duplicates
        before = len(df)
        df = df.drop_duplicates(subset=[config.DEDUPLICATION_KEY])
        removed = before - len(df)
        if removed > 0:
            logger.warning(f"  Removed {removed:,} duplicate records")
        
        # Convert types
        df['tender_value_amount'] = pd.to_numeric(df['tender_value_amount'], errors='coerce').fillna(0.0)
        
        logger.info(f"  Final: {len(df):,} valid records ({initial_count - len(df):,} removed)")
        
        return df
    
    def transform(self) -> pd.DataFrame:
        """Main transformation pipeline"""
        logger.info(f"Starting transformation for {config.SOURCE_DISPLAY_NAME}")
        
        # Load source data
        data = self.load_source_data()
        
        if data['tenders'].empty:
            logger.error("No tender data found!")
            return pd.DataFrame()
        
        # Merge relationships
        merged = self.merge_relationships(data)
        
        # Map to Silver schema
        silver = self.map_to_silver_schema(merged)
        
        # Validate and clean
        silver = self.validate_and_clean(silver)
        
        logger.info(f"Transformation complete: {len(silver):,} records ready for Silver layer")
        
        return silver
