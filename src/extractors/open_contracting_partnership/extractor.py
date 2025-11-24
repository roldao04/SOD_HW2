"""
Open Contracting Partnership Data Extractor

Extracts OCDS (Open Contracting Data Standard) data from the OCP Data Registry
for European countries and saves to Bronze layer.

License: Data is CC BY-NC-SA 4.0 (Non-commercial, Attribution, Share-alike)
"""
import json
import logging
import time
import gzip
from typing import Dict, List, Optional
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO

from .config import EUROPEAN_PUBLICATIONS, REQUEST_CONFIG
from .utils import (
    filter_records_by_year,
    save_records_to_bronze,
    add_license_metadata
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCPExtractor:
    """
    Extractor for Open Contracting Partnership data.
    """

    def __init__(self, base_data_dir: str = "/home/roldao/Desktop/MEI/SOD/hw2/data"):
        """
        Initialize the extractor.

        Args:
            base_data_dir: Base directory for data storage
        """
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
            'Accept': 'application/json, text/html',
        })

        return session

    def _build_download_url(self, publication_id: str, year: int) -> str:
        """
        Build the download URL for a specific publication and year.

        Args:
            publication_id: Publication ID
            year: Year to download

        Returns:
            Download URL
        """
        return f"https://data.open-contracting.org/en/publication/{publication_id}/download?name={year}.jsonl.gz"

    def _download_and_parse_jsonl_gz(self, url: str) -> Optional[List[Dict]]:
        """
        Download and parse a gzipped JSONL file.

        Args:
            url: URL of the .jsonl.gz file

        Returns:
            List of parsed JSON objects or None if download fails
        """
        try:
            logger.info(f"Downloading: {url}")
            response = self.session.get(
                url,
                timeout=REQUEST_CONFIG['timeout'],
                stream=True
            )

            if response.status_code == 404:
                logger.debug(f"File not found (404): {url}")
                return None

            response.raise_for_status()

            # Decompress gzip content
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
                content = gz.read()

            # Parse JSONL (each line is a JSON object)
            records = []
            for line_num, line in enumerate(content.decode('utf-8').splitlines(), 1):
                if line.strip():
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON at line {line_num}: {e}")
                        continue

            logger.info(f"Successfully downloaded and parsed {len(records)} records")
            return records

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing file from {url}: {e}")
            return None

    def _extract_from_publication(
        self,
        pub_key: str,
        pub_config: Dict,
        year_filter: int = 2025
    ) -> Dict:
        """
        Extract data from a single publication.

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
            # Build download URL for the target year
            download_url = self._build_download_url(
                pub_config['publication_id'],
                year_filter
            )

            # Download and parse the data
            records = self._download_and_parse_jsonl_gz(download_url)

            if not records:
                result['error'] = f"No data available for year {year_filter}"
                return result

            result['records_downloaded'] = len(records)
            logger.info(f"Downloaded {len(records)} records for {year_filter}")

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
            logger.error(f"Unexpected error extracting {pub_config['name']}: {e}")
            result['error'] = str(e)

        return result

    def extract_all(self, year_filter: int = 2025) -> Dict:
        """
        Extract data from all European publications.

        Args:
            year_filter: Year to filter records for

        Returns:
            Dictionary with overall extraction results
        """
        logger.info(f"Starting extraction for all European publications (year: {year_filter})")

        results = {
            'total_publications': len(EUROPEAN_PUBLICATIONS),
            'successful_publications': 0,
            'failed_publications': 0,
            'total_records_saved': 0,
            'publication_results': [],
            'start_time': time.time()
        }

        for pub_key, pub_config in EUROPEAN_PUBLICATIONS.items():
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

    def extract_country(self, country: str, year_filter: int = 2025) -> Dict:
        """
        Extract data for a specific country only.

        Args:
            country: Country code (e.g., 'uk', 'spain', 'germany')
            year_filter: Year to filter records for

        Returns:
            Dictionary with extraction results
        """
        country_pubs = {
            k: v for k, v in EUROPEAN_PUBLICATIONS.items()
            if v['country'] == country.lower()
        }

        if not country_pubs:
            logger.error(f"No publications found for country: {country}")
            return {
                'success': False,
                'error': f"Country '{country}' not found"
            }

        logger.info(f"Extracting data for country: {country.upper()} ({len(country_pubs)} publications)")

        results = []
        for pub_key, pub_config in country_pubs.items():
            pub_result = self._extract_from_publication(pub_key, pub_config, year_filter)
            results.append(pub_result)
            time.sleep(REQUEST_CONFIG['rate_limit_delay'])

        return {
            'success': True,
            'country': country,
            'publications_processed': len(results),
            'results': results
        }
