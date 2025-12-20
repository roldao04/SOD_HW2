"""
Multi-level data quality validation for Silver layer records.

Provides comprehensive validation including:
- Schema validation (field types)
- Required field validation (non-null/empty)
- Data type validation
- Range validation (bounds checking)
- Business rule validation
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict

if TYPE_CHECKING:
    from src.storage import MinIOClient

logger = logging.getLogger(__name__)


@dataclass
class FieldValidation:
    """Validation result for a single field."""
    field_name: str
    passed: bool
    null_count: int = 0
    empty_count: int = 0
    invalid_count: int = 0
    type_mismatches: int = 0
    out_of_range: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class QualityReport:
    """Comprehensive data quality report."""
    timestamp: str
    source: str
    total_records: int
    validation_passed: int
    validation_failed: int
    completeness_score: float  # % of non-null values
    field_validations: Dict[str, FieldValidation]
    business_rule_validations: Dict[str, int]  # rule_name -> violation_count
    summary: Dict[str, Any]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'source': self.source,
            'total_records': self.total_records,
            'validation_passed': self.validation_passed,
            'validation_failed': self.validation_failed,
            'completeness_score': self.completeness_score,
            'field_validations': {
                name: asdict(validation)
                for name, validation in self.field_validations.items()
            },
            'business_rule_validations': self.business_rule_validations,
            'summary': self.summary
        }


class QualityValidator:
    """
    Multi-level data quality validator.

    Validates records against schema, business rules, and quality thresholds.
    """

    def __init__(
        self,
        schema: Dict[str, str],
        required_fields: List[str],
        min_quality_score: float = 0.80,
        max_null_percentage: float = 0.15
    ):
        """
        Initialize validator.

        Args:
            schema: Expected schema (field_name -> type_string)
            required_fields: List of required field names
            min_quality_score: Minimum acceptable completeness score
            max_null_percentage: Maximum acceptable null percentage
        """
        self.schema = schema
        self.required_fields = required_fields
        self.min_quality_score = float(os.getenv('MIN_QUALITY_SCORE', min_quality_score))
        self.max_null_percentage = float(os.getenv('MAX_NULL_PERCENTAGE', max_null_percentage))

    def validate_records(
        self,
        records: List[Dict],
        source_name: str
    ) -> QualityReport:
        """
        Validate a list of records.

        Args:
            records: List of record dictionaries
            source_name: Name of data source

        Returns:
            QualityReport with validation results
        """
        if not records:
            return self._empty_report(source_name)

        field_validations = {}
        validation_passed = 0
        validation_failed = 0

        # Initialize field validation trackers
        for field_name in self.schema.keys():
            field_validations[field_name] = FieldValidation(
                field_name=field_name,
                passed=True
            )

        # Validate each record
        for record in records:
            record_valid = self._validate_single_record(record, field_validations)
            if record_valid:
                validation_passed += 1
            else:
                validation_failed += 1

        # Business rule validation
        business_validations = self._validate_business_rules(records)

        # Calculate completeness score
        completeness = self._calculate_completeness(records)

        # Create summary
        summary = self._create_summary(
            records,
            validation_passed,
            validation_failed,
            completeness,
            business_validations
        )

        return QualityReport(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source=source_name,
            total_records=len(records),
            validation_passed=validation_passed,
            validation_failed=validation_failed,
            completeness_score=completeness,
            field_validations=field_validations,
            business_rule_validations=business_validations,
            summary=summary
        )

    def _validate_single_record(
        self,
        record: Dict,
        field_validations: Dict[str, FieldValidation]
    ) -> bool:
        """
        Validate a single record.

        Args:
            record: Record dictionary
            field_validations: Field validation trackers (updated in-place)

        Returns:
            True if record passes all required validations
        """
        record_valid = True

        for field_name, expected_type in self.schema.items():
            validation = field_validations[field_name]
            value = record.get(field_name)

            # Check null
            if value is None:
                validation.null_count += 1
                if field_name in self.required_fields:
                    validation.passed = False
                    record_valid = False
                continue

            # Check empty (for strings)
            if expected_type == 'string' and value == '':
                validation.empty_count += 1
                if field_name in self.required_fields:
                    validation.passed = False
                    record_valid = False
                continue

            # Type validation
            if not self._check_type(value, expected_type):
                validation.type_mismatches += 1
                validation.passed = False
                record_valid = False

            # Range validation
            if not self._check_range(field_name, value):
                validation.out_of_range += 1
                validation.passed = False

        return record_valid

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_checkers = {
            'string': lambda v: isinstance(v, str),
            'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
            'float': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            'list[string]': lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
        }

        checker = type_checkers.get(expected_type)
        if checker:
            return checker(value)

        # Default: accept any value
        return True

    def _check_range(self, field_name: str, value: Any) -> bool:
        """Check if value is within acceptable range."""
        # Amount fields should be non-negative
        if field_name.endswith('_amount') or field_name.startswith('num_'):
            try:
                if float(value) < 0:
                    return False
            except (ValueError, TypeError):
                return False

        # Date fields should not be in the far future
        if field_name.endswith('_date'):
            if isinstance(value, str) and value:
                try:
                    # Parse date and check it's not more than 1 year in future
                    date_str = value[:10]  # Get YYYY-MM-DD part
                    record_date = datetime.strptime(date_str, '%Y-%m-%d')
                    future_limit = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
                    if record_date > future_limit:
                        return False
                except (ValueError, IndexError):
                    return False

        return True

    def _validate_business_rules(self, records: List[Dict]) -> Dict[str, int]:
        """
        Validate business rules across all records.

        Returns:
            Dictionary of rule_name -> violation_count
        """
        violations = {
            'invalid_ocid_format': 0,
            'invalid_currency_code': 0,
            'end_date_before_start_date': 0,
            'award_date_before_tender_date': 0,
            'negative_amounts': 0,
        }

        for record in records:
            # OCID format (must start with 'ocds-')
            ocid = record.get('ocid', '')
            if ocid and not str(ocid).startswith('ocds-'):
                violations['invalid_ocid_format'] += 1

            # Currency code (must be 3 letters if present)
            for curr_field in ['tender_value_currency', 'award_currency']:
                currency = record.get(curr_field, '')
                if currency and (len(currency) != 3 or not currency.isalpha()):
                    violations['invalid_currency_code'] += 1

            # Date consistency
            start_date = record.get('tender_start_date')
            end_date = record.get('tender_end_date')
            if start_date and end_date:
                try:
                    if start_date > end_date:
                        violations['end_date_before_start_date'] += 1
                except TypeError:
                    pass

            # Award date should be after tender date
            pub_date = record.get('publication_date')
            award_date = record.get('award_date')
            if pub_date and award_date:
                try:
                    if award_date < pub_date:
                        violations['award_date_before_tender_date'] += 1
                except TypeError:
                    pass

            # Negative amounts
            for amt_field in ['tender_value_amount', 'award_amount']:
                amount = record.get(amt_field, 0)
                try:
                    if float(amount) < 0:
                        violations['negative_amounts'] += 1
                        break
                except (ValueError, TypeError):
                    pass

        return violations

    def _calculate_completeness(self, records: List[Dict]) -> float:
        """
        Calculate completeness score (% of non-null values).

        Args:
            records: List of records

        Returns:
            Completeness score between 0.0 and 1.0
        """
        if not records:
            return 0.0

        total_fields = len(self.schema) * len(records)
        non_null_count = 0

        for record in records:
            for field_name in self.schema.keys():
                value = record.get(field_name)
                if value is not None and value != '':
                    non_null_count += 1

        return non_null_count / total_fields if total_fields > 0 else 0.0

    def _create_summary(
        self,
        records: List[Dict],
        passed: int,
        failed: int,
        completeness: float,
        business_violations: Dict[str, int]
    ) -> Dict[str, Any]:
        """Create summary statistics."""
        total_violations = sum(business_violations.values())

        return {
            'quality_score': completeness,
            'pass_rate': passed / len(records) if records else 0.0,
            'fail_rate': failed / len(records) if records else 0.0,
            'total_business_violations': total_violations,
            'quality_check_passed': (
                completeness >= self.min_quality_score and
                (failed / len(records) if records else 1.0) <= self.max_null_percentage
            ),
            'warnings': self._generate_warnings(completeness, failed, len(records), business_violations)
        }

    def _generate_warnings(
        self,
        completeness: float,
        failed: int,
        total: int,
        business_violations: Dict[str, int]
    ) -> List[str]:
        """Generate warning messages for quality issues."""
        warnings = []

        if completeness < self.min_quality_score:
            warnings.append(
                f"Low completeness score: {completeness:.2%} (minimum: {self.min_quality_score:.2%})"
            )

        fail_rate = failed / total if total > 0 else 0
        if fail_rate > self.max_null_percentage:
            warnings.append(
                f"High failure rate: {fail_rate:.2%} (maximum: {self.max_null_percentage:.2%})"
            )

        for rule_name, count in business_violations.items():
            if count > 0:
                warnings.append(f"Business rule violation '{rule_name}': {count} occurrences")

        return warnings

    def _empty_report(self, source_name: str) -> QualityReport:
        """Create empty quality report."""
        return QualityReport(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source=source_name,
            total_records=0,
            validation_passed=0,
            validation_failed=0,
            completeness_score=0.0,
            field_validations={},
            business_rule_validations={},
            summary={'quality_check_passed': False, 'warnings': ['No records to validate']}
        )

    @staticmethod
    def save_quality_report(
        report: QualityReport,
        output_dir: str,
        storage_client: Optional['MinIOClient'] = None
    ) -> None:
        """
        Save quality report to storage.

        Args:
            report: QualityReport to save
            output_dir: Local output directory
            storage_client: Optional MinIO client
        """
        import json

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_quality.json"

        # Save to local
        output_path = Path(output_dir) / 'quality_reports'
        output_path.mkdir(parents=True, exist_ok=True)
        local_file = output_path / filename

        with open(local_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved quality report to {local_file}")

        # Save to MinIO if available
        if storage_client:
            try:
                object_path = f"{report.source}/quality_reports/{filename}"
                storage_client.write_json('silver', object_path, report.to_dict())
                logger.info(f"Saved quality report to MinIO: silver/{object_path}")
            except Exception as e:
                logger.warning(f"Failed to save quality report to MinIO: {e}")
