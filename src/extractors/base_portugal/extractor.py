"""
BASE Portugal Data Extractor

Extracts public procurement data from Portugal's BASE portal
via dados.gov.pt Open Data Portal (XLSX format) and saves to Bronze layer.

License: Open Data License (dados.gov.pt)
"""
import json
import logging
import time
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO
import openpyxl

from .config import PORTUGAL_PUBLICATIONS, REQUEST_CONFIG
from .utils import (
    save_records_to_bronze,
    add_license_metadata,
    parse_ocds_date
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BasePortugalExtractor:
    """
    Extractor for Portugal BASE portal data via dados.gov.pt (XLSX format).
    """

    def __init__(self, base_data_dir: str = None):
        """
        Initialize the extractor.

        Args:
            base_data_dir: Base directory for data storage
        """
        if base_data_dir is None:
            base_data_dir = str(Path(__file__).parent.parent.parent.parent / "data")

        self.base_data_dir = base_data_dir
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic and proper headers.

        Returns:
            Configured requests Session
        """
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=REQUEST_CONFIG['retry_attempts'],
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            'User-Agent': REQUEST_CONFIG['user_agent'],
            'Accept': 'application/json, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return session

    def _get_dataset_resources(self, dataset_id: str) -> Optional[List[Dict]]:
        """
        Get available resources (files) for a dataset from dados.gov.pt API.

        Args:
            dataset_id: Dataset ID

        Returns:
            List of resource dictionaries or None if request fails
        """
        try:
            api_url = f"https://dados.gov.pt/api/1/datasets/{dataset_id}/"
            logger.info(f"Fetching dataset info: {api_url}")

            response = self.session.get(
                api_url,
                timeout=REQUEST_CONFIG['timeout']
            )
            response.raise_for_status()

            data = response.json()
            resources = data.get('resources', [])

            logger.info(f"Found {len(resources)} resources")
            return resources

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch dataset info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing dataset info: {e}")
            return None

    def _find_year_resource(self, resources: List[Dict], year: int) -> Optional[Dict]:
        """
        Find the XLSX resource file for a specific year.

        Args:
            resources: List of resource dictionaries from API
            year: Year to find

        Returns:
            Resource dictionary or None if not found
        """
        year_str = str(year)

        for resource in resources:
            title = resource.get('title', '')
            format_type = resource.get('format', '').lower()
            url = resource.get('url', '')

            # Look for XLSX file with year in title
            if year_str in title and format_type == 'xlsx':
                logger.info(f"Found XLSX resource for {year}: {title}")
                return resource

        logger.warning(f"No XLSX resource found for year {year}")
        return None

    def _download_xlsx(self, url: str) -> Optional[openpyxl.Workbook]:
        """
        Download and load an XLSX file into memory.

        Args:
            url: URL of the XLSX file

        Returns:
            openpyxl Workbook or None if download fails
        """
        try:
            logger.info(f"Downloading XLSX: {url}")
            response = self.session.get(
                url,
                timeout=REQUEST_CONFIG['timeout'],
                stream=True
            )

            if response.status_code == 404:
                logger.error(f"File not found (404): {url}")
                return None

            response.raise_for_status()

            # Load workbook from memory
            wb = openpyxl.load_workbook(BytesIO(response.content), read_only=True)
            logger.info(f"Successfully loaded XLSX with {len(wb.sheetnames)} sheets")
            return wb

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing XLSX from {url}: {e}")
            return None

    def _convert_xlsx_to_ocds(self, wb: openpyxl.Workbook, year: int) -> List[Dict]:
        """
        Convert XLSX workbook to OCDS-like format.

        Args:
            wb: openpyxl Workbook
            year: Year of the data

        Returns:
            List of OCDS-like records
        """
        records = []
        sheet = wb.active

        # Get headers from first row
        headers = []
        for cell in sheet[1]:
            headers.append(cell.value)

        logger.info(f"Found {len(headers)} columns: {headers[:5]}...")

        # Process rows
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
            if row_idx % 1000 == 0:
                logger.info(f"Processing row {row_idx}...")

            try:
                # Create record dict from row
                record_data = dict(zip(headers, row))

                # Convert to OCDS-like structure
                ocds_record = self._row_to_ocds(record_data, year)
                if ocds_record:
                    records.append(ocds_record)

            except Exception as e:
                logger.warning(f"Error processing row {row_idx}: {e}")
                continue

        logger.info(f"Converted {len(records)} records from XLSX")
        return records

    def _row_to_ocds(self, row: Dict, year: int) -> Optional[Dict]:
        """
        Convert a single Excel row to OCDS-like format.

        Args:
            row: Dictionary with column names as keys
            year: Year of the data

        Returns:
            OCDS-like record or None if conversion fails
        """
        try:
            # Generate unique OCID from available fields
            # Use contract ID or combination of fields
            contract_id = row.get('ID do Contrato') or row.get('ID Contrato') or row.get('Identificador')

            if not contract_id:
                # Try to find any ID field
                for key in row.keys():
                    if 'ID' in str(key).upper() or 'Identificador' in str(key):
                        contract_id = row.get(key)
                        break

            if not contract_id:
                return None

            ocid = f"ocds-base-pt-{year}-{contract_id}"

            # Parse dates
            pub_date = None
            for date_field in ['Data Publicação', 'Data de Publicação', 'Data']:
                if row.get(date_field):
                    pub_date = self._parse_excel_date(row.get(date_field))
                    if pub_date:
                        break

            if not pub_date:
                pub_date = f"{year}-01-01"  # Default to year start

            # Build OCDS-like record
            ocds_record = {
                'ocid': ocid,
                'date': pub_date,
                'tender': {
                    'id': str(contract_id),
                    'title': row.get('Objeto do Contrato') or row.get('Descrição') or '',
                    'status': row.get('Estado') or 'active',
                    'value': {
                        'amount': self._parse_amount(row.get('Preço Contratual') or row.get('Valor')),
                        'currency': 'EUR'
                    }
                },
                'buyer': {
                    'id': row.get('NIF Adjudicante') or '',
                    'name': row.get('Adjudicante') or row.get('Entidade Adjudicante') or ''
                },
                'awards': []
            }

            # Add award info if available
            supplier_name = row.get('Adjudicatário') or row.get('Entidade Adjudicatária')
            if supplier_name:
                award = {
                    'date': pub_date,
                    'value': {
                        'amount': self._parse_amount(row.get('Preço Contratual') or row.get('Valor')),
                        'currency': 'EUR'
                    },
                    'suppliers': [{
                        'id': row.get('NIF Adjudicatário') or '',
                        'name': supplier_name
                    }]
                }
                ocds_record['awards'].append(award)

            return ocds_record

        except Exception as e:
            logger.warning(f"Error converting row to OCDS: {e}")
            return None

    def _parse_excel_date(self, value) -> Optional[str]:
        """Parse Excel date value to ISO string."""
        if not value:
            return None

        try:
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d')
            elif isinstance(value, str):
                # Try parsing string date
                date_obj = parse_ocds_date(value)
                if date_obj:
                    return date_obj.strftime('%Y-%m-%d')
            return None
        except:
            return None

    def _parse_amount(self, value) -> float:
        """Parse amount value to float."""
        if not value:
            return 0.0

        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Remove currency symbols and spaces
                clean = value.replace('€', '').replace(' ', '').replace(',', '.')
                return float(clean)
            return 0.0
        except:
            return 0.0

    def _extract_from_publication(
        self,
        pub_key: str,
        pub_config: Dict,
        year_filter: int = 2025
    ) -> Dict:
        """
        Extract data from BASE Portugal publication.

        Args:
            pub_key: Publication key
            pub_config: Publication configuration
            year_filter: Year to filter records for

        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Starting extraction for: {pub_config['name']}")

        result = {
            'publication_key': pub_key,
            'publication_name': pub_config['name'],
            'country': pub_config['country'],
            'success': False,
            'records_downloaded': 0,
            'records_saved': 0,
            'error': None
        }

        try:
            # Get dataset resources from API
            resources = self._get_dataset_resources(pub_config['dataset_id'])

            if not resources:
                result['error'] = "Failed to fetch dataset resources from API"
                return result

            # Find XLSX resource for the target year
            year_resource = self._find_year_resource(resources, year_filter)

            if not year_resource:
                result['error'] = f"No XLSX file available for year {year_filter}"
                return result

            download_url = year_resource.get('url')
            if not download_url:
                result['error'] = "Resource has no download URL"
                return result

            # Download XLSX file
            wb = self._download_xlsx(download_url)

            if not wb:
                result['error'] = f"Failed to download XLSX from {download_url}"
                return result

            # Convert XLSX to OCDS-like format
            logger.info("Converting XLSX to OCDS format...")
            records = self._convert_xlsx_to_ocds(wb, year_filter)
            wb.close()

            if not records:
                result['error'] = "No records extracted from XLSX"
                return result

            result['records_downloaded'] = len(records)
            logger.info(f"Extracted {len(records)} records from XLSX")

            # Save to Bronze layer
            total_saved, date_counts = save_records_to_bronze(
                records,
                pub_config['country'],
                self.base_data_dir
            )

            result['records_saved'] = total_saved
            result['date_distribution'] = date_counts
            result['success'] = True

            logger.info(f"Successfully extracted {total_saved} records for {pub_config['name']}")

        except Exception as e:
            logger.error(f"Unexpected error extracting {pub_config['name']}: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    def extract_all(self, year_filter: int = 2025) -> Dict:
        """
        Extract data from all Portugal publications.

        Args:
            year_filter: Year to filter records for

        Returns:
            Dictionary with overall extraction results
        """
        logger.info(f"Starting extraction for Portugal publications (year: {year_filter})")

        results = {
            'total_publications': len(PORTUGAL_PUBLICATIONS),
            'successful_publications': 0,
            'failed_publications': 0,
            'total_records_saved': 0,
            'publication_results': [],
            'start_time': time.time()
        }

        for pub_key, pub_config in PORTUGAL_PUBLICATIONS.items():
            # Extract from publication
            pub_result = self._extract_from_publication(pub_key, pub_config, year_filter)
            results['publication_results'].append(pub_result)

            if pub_result['success']:
                results['successful_publications'] += 1
                results['total_records_saved'] += pub_result['records_saved']
            else:
                results['failed_publications'] += 1

            # Rate limiting between publications
            time.sleep(REQUEST_CONFIG['rate_limit_delay'])

        results['end_time'] = time.time()
        results['duration_seconds'] = results['end_time'] - results['start_time']

        # Summary
        logger.info("=" * 80)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total publications: {results['total_publications']}")
        logger.info(f"Successful: {results['successful_publications']}")
        logger.info(f"Failed: {results['failed_publications']}")
        logger.info(f"Total records saved: {results['total_records_saved']}")
        logger.info(f"Duration: {results['duration_seconds']:.2f} seconds")
        logger.info("=" * 80)

        return results

    def extract_country(self, country: str = "portugal", year_filter: int = 2025) -> Dict:
        """
        Extract data for Portugal (wrapper for consistency with OCP extractor).

        Args:
            country: Country code (defaults to 'portugal')
            year_filter: Year to filter records for

        Returns:
            Dictionary with extraction results
        """
        return self.extract_all(year_filter)
