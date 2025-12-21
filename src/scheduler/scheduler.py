#!/usr/bin/env python3
"""
Pipeline Orchestration Scheduler

Automates the execution of the complete data pipeline:
1. Extract from all sources (Bronze layer)
2. Process to Silver layer
3. Generate Gold layer
4. Upload to MinIO

Usage:
    # Full pipeline
    python -m src.scheduler.scheduler

    # Specific sources only
    python -m src.scheduler.scheduler --sources base_portugal open_contracting

    # Only extraction
    python -m src.scheduler.scheduler --extract-only

    # Only processing
    python -m src.scheduler.scheduler --process-only

    # Only gold layer
    python -m src.scheduler.scheduler --gold-only
"""

import logging
import time
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the complete data pipeline execution."""
    
    # Available sources
    SOURCES = {
        'base_portugal': {
            'extractor': ['python3', '-m', 'src.extractors.base_portugal.main', '--all'],
            'processor': ['python3', '-m', 'src.processing.base_portugal.main', '--all'],
        },
        'open_contracting': {
            'extractor': ['python3', '-m', 'src.extractors.open_contracting_partnership.main', '--all'],
            'processor': ['python3', '-m', 'src.processing.open_contracting_partnership.main', '--all'],
        },
        'ted': {
            'extractor': None,  # No extractor available
            'processor': ['python3', '-m', 'src.processing.ted.main', '--all'],
        },
        'henrique_monteiro': {
            'extractor': None,  # Static data (Excel file)
            'processor': ['python3', '-m', 'src.processing.henrique_monteiro.main', '--all'],
        },
    }
    
    def __init__(self):
        self.start_time = datetime.now()
        self.stats = {
            'extractors': {},
            'processors': {},
            'gold_layer': {},
            'errors': [],
            'warnings': []
        }
    
    def _run_command(
        self,
        cmd: List[str],
        name: str,
        timeout: int = 600,
        allow_failure: bool = False
    ) -> bool:
        """
        Run a subprocess command.
        
        Args:
            cmd: Command list
            name: Task name for logging
            timeout: Timeout in seconds
            allow_failure: If True, don't fail on error
            
        Returns:
            True if successful
        """
        logger.info(f"▶ Running: {name}")
        logger.info(f"  Command: {' '.join(cmd)}")
        logger.info(f"  Timeout: {timeout}s")
        start = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            duration = time.time() - start
            
            # Log stdout for debugging (check for "Skipping" messages)
            if result.stdout:
                # Check for state management messages
                if 'Skipping' in result.stdout or 'already extracted' in result.stdout:
                    logger.info(f"State management detected - skipping already processed data")
                    # Show first few lines of output
                    lines = result.stdout.strip().split('\n')
                    for line in lines[:10]:
                        if 'Skipping' in line or 'already extracted' in line:
                            logger.info(f"     {line}")
                
                # Check for extraction/processing counts
                if 'Total records' in result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if 'Total records' in line or 'Successful:' in line or 'records saved' in line:
                            logger.info(f"     {line.strip()}")
            
            if result.returncode == 0:
                logger.info(f" {name} completed in {duration:.1f}s ({duration/60:.1f} min)")
                return True
            else:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                
                if allow_failure:
                    logger.warning(f" {name} failed (continuing): {error_msg[:100]}")
                    # Show more output for debugging
                    if result.stdout:
                        logger.warning(f"  Last stdout lines:")
                        for line in result.stdout.strip().split('\n')[-5:]:
                            logger.warning(f"     {line}")
                    self.stats['warnings'].append({
                        'task': name,
                        'error': error_msg
                    })
                    return False
                else:
                    logger.error(f" {name} failed: {error_msg[:200]}")
                    self.stats['errors'].append({
                        'task': name,
                        'error': error_msg
                    })
                    return False
                    
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start
            logger.error(f" {name} timeout after {timeout}s (actual: {duration:.1f}s)")
            # Try to get partial output
            if hasattr(e, 'stdout') and e.stdout:
                logger.error(f"  Partial stdout before timeout:")
                for line in e.stdout.strip().split('\n')[-10:]:
                    logger.error(f"     {line}")
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"  Partial stderr before timeout:")
                for line in e.stderr.strip().split('\n')[-10:]:
                    logger.error(f"     {line}")
            self.stats['errors'].append({
                'task': name,
                'error': f'Timeout after {timeout}s'
            })
            return False
        except Exception as e:
            logger.error(f" {name} error: {e}")
            self.stats['errors'].append({
                'task': name,
                'error': str(e)
            })
            return False
    
    def run_extractors(self, sources: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Run extractors for specified sources.
        
        Args:
            sources: List of source names (None = all)
            
        Returns:
            Dict mapping source name to status
        """
        logger.info("\n" + "=" * 70)
        logger.info(" PHASE 1: EXTRACTION (Bronze Layer)")
        logger.info("=" * 70)
        
        # Determine which sources to extract
        if sources:
            sources_to_extract = {k: v for k, v in self.SOURCES.items() if k in sources}
        else:
            sources_to_extract = self.SOURCES
        
        results = {}
        
        for source_name, config in sources_to_extract.items():
            extractor_cmd = config.get('extractor')
            
            if extractor_cmd is None:
                logger.warning(f" No extractor available for {source_name}, skipping")
                results[source_name] = 'no_extractor'
                self.stats['warnings'].append({
                    'task': f'Extract {source_name}',
                    'error': 'No extractor available'
                })
                continue
            
            success = self._run_command(
                extractor_cmd,
                f"Extract {source_name}",
                timeout=1800,  # 30 min for extractors (first run takes ~20 min, subsequent ~2 min)
                allow_failure=True  # Continue on extractor failure
            )
            
            results[source_name] = 'success' if success else 'failed'
            self.stats['extractors'][source_name] = results[source_name]
        
        # Summary
        successful = sum(1 for s in results.values() if s == 'success')
        logger.info(f"\nExtraction Summary: {successful}/{len(results)} sources successful")
        
        return results
    
    def run_processors(self, sources: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Run processors for specified sources.
        
        Args:
            sources: List of source names (None = all)
            
        Returns:
            Dict mapping source name to status
        """
        logger.info("\n" + "=" * 70)
        logger.info(" PHASE 2: PROCESSING (Silver Layer)")
        logger.info("=" * 70)
        
        # Determine which sources to process
        if sources:
            sources_to_process = {k: v for k, v in self.SOURCES.items() if k in sources}
        else:
            sources_to_process = self.SOURCES
        
        results = {}
        
        for source_name, config in sources_to_process.items():
            processor_cmd = config.get('processor')
            
            if processor_cmd is None:
                logger.warning(f" No processor available for {source_name}, skipping")
                results[source_name] = 'no_processor'
                continue
            
            success = self._run_command(
                processor_cmd,
                f"Process {source_name}",
                timeout=1200,  # 20 min for processors
                allow_failure=True  # Continue on processor failure
            )
            
            results[source_name] = 'success' if success else 'failed'
            self.stats['processors'][source_name] = results[source_name]
        
        # Summary
        successful = sum(1 for s in results.values() if s == 'success')
        logger.info(f"\nProcessing Summary: {successful}/{len(results)} sources successful")
        
        return results
    
    def run_gold_layer(self) -> bool:
        """
        Generate Gold layer (unified + aggregates).
        
        Returns:
            True if successful
        """
        logger.info("\n" + "=" * 70)
        logger.info(" PHASE 3: GOLD LAYER GENERATION")
        logger.info("=" * 70)
        
        # Generate Gold layer
        logger.info("\nGenerating unified dataset + aggregates...")
        success = self._run_command(
            ['python3', '-m', 'src.gold_layer.main', '--all'],
            'Generate Gold Layer',
            timeout=900,  # 15 min
            allow_failure=False
        )
        
        self.stats['gold_layer']['generation'] = 'success' if success else 'failed'
        
        if not success:
            logger.error("Gold layer generation failed, skipping upload")
            return False
        
        # Upload to MinIO
        logger.info("\nUploading to MinIO...")
        upload_success = self._run_command(
            ['python3', '-m', 'src.gold_layer.upload_to_minio'],
            'Upload to MinIO',
            timeout=600,  # 10 min
            allow_failure=True  # Upload failure is not critical
        )
        
        self.stats['gold_layer']['upload'] = 'success' if upload_success else 'failed'
        
        return success
    
    def generate_report(self):
        """Generate and display execution report."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        logger.info("\n" + "=" * 70)
        logger.info(" PIPELINE EXECUTION REPORT")
        logger.info("=" * 70)
        
        logger.info(f"\n  Total Duration: {duration:.1f}s ({duration/60:.1f} min)")
        
        # Extractors
        if self.stats['extractors']:
            logger.info("\nExtractors:")
            for name, status in self.stats['extractors'].items():
                symbol = "" if status == 'success' else "" if status == 'failed' else "⊘"
                logger.info(f"  {symbol} {name}: {status}")
        
        # Processors
        if self.stats['processors']:
            logger.info("\nProcessors:")
            for name, status in self.stats['processors'].items():
                symbol = "" if status == 'success' else "" if status == 'failed' else "⊘"
                logger.info(f"  {symbol} {name}: {status}")
        
        # Gold layer
        if self.stats['gold_layer']:
            logger.info("\nGold Layer:")
            for phase, status in self.stats['gold_layer'].items():
                symbol = "" if status == 'success' else ""
                logger.info(f"  {symbol} {phase}: {status}")
        
        # Warnings
        if self.stats['warnings']:
            logger.info(f"\nWarnings ({len(self.stats['warnings'])}):")
            for warning in self.stats['warnings'][:5]:  # Show first 5
                logger.info(f"  • {warning['task']}: {warning['error'][:80]}...")
        
        # Errors
        if self.stats['errors']:
            logger.info(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5
                logger.info(f"  • {error['task']}: {error['error'][:80]}...")
        
        # Save detailed report
        self._save_report(duration)
        
        # Final status
        logger.info("\n" + "=" * 70)
        if self.stats['errors']:
            logger.warning("Pipeline completed WITH ERRORS")
            return False
        elif self.stats['warnings']:
            logger.info(" Pipeline completed with warnings")
            return True
        else:
            logger.info(" Pipeline completed SUCCESSFULLY")
            return True
    
    def _save_report(self, duration: float):
        """Save detailed execution report to file."""
        report_path = Path('data/pipeline_execution_report.txt')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write(" PIPELINE EXECUTION REPORT\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {duration:.1f}s ({duration/60:.1f} min)\n\n")
            
            f.write("EXTRACTORS:\n")
            for name, status in self.stats['extractors'].items():
                f.write(f"  - {name}: {status}\n")
            
            f.write("\nPROCESSORS:\n")
            for name, status in self.stats['processors'].items():
                f.write(f"  - {name}: {status}\n")
            
            f.write("\nGOLD LAYER:\n")
            for phase, status in self.stats['gold_layer'].items():
                f.write(f"  - {phase}: {status}\n")
            
            if self.stats['warnings']:
                f.write(f"\nWARNINGS ({len(self.stats['warnings'])}):\n")
                for warning in self.stats['warnings']:
                    f.write(f"  - {warning['task']}: {warning['error']}\n")
            
            if self.stats['errors']:
                f.write(f"\nERRORS ({len(self.stats['errors'])}):\n")
                for error in self.stats['errors']:
                    f.write(f"  - {error['task']}: {error['error']}\n")
        
        logger.info(f"\nDetailed report saved to: {report_path}")
    
    def run_full_pipeline(self, sources: Optional[List[str]] = None):
        """
        Execute complete pipeline.
        
        Args:
            sources: List of source names (None = all)
        """
        logger.info("\n" + "=" * 70)
        logger.info(" STARTING PIPELINE ORCHESTRATION")
        logger.info("=" * 70)
        
        if sources:
            logger.info(f"Sources: {', '.join(sources)}")
        else:
            logger.info("Sources: ALL")
        
        # Phase 1: Extract
        self.run_extractors(sources)
        
        # Phase 2: Process
        self.run_processors(sources)
        
        # Phase 3: Gold layer
        self.run_gold_layer()
        
        # Report
        success = self.generate_report()
        
        return success


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Orchestrate E-Procurement data pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python -m src.scheduler.scheduler

  # Run only for specific sources
  python -m src.scheduler.scheduler --sources base_portugal open_contracting

  # Only extract data
  python -m src.scheduler.scheduler --extract-only

  # Only process to Silver
  python -m src.scheduler.scheduler --process-only

  # Only generate Gold layer
  python -m src.scheduler.scheduler --gold-only
"""
    )
    
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['base_portugal', 'open_contracting', 'ted'],
        help='Sources to process (default: all)',
        default=None
    )
    
    parser.add_argument(
        '--extract-only',
        action='store_true',
        help='Only run extractors'
    )
    
    parser.add_argument(
        '--process-only',
        action='store_true',
        help='Only run processors'
    )
    
    parser.add_argument(
        '--gold-only',
        action='store_true',
        help='Only run gold layer generation'
    )
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = PipelineOrchestrator()
    
    try:
        # Execute based on arguments
        if args.extract_only:
            orchestrator.run_extractors(args.sources)
            success = orchestrator.generate_report()
        elif args.process_only:
            orchestrator.run_processors(args.sources)
            success = orchestrator.generate_report()
        elif args.gold_only:
            success = orchestrator.run_gold_layer()
            orchestrator.generate_report()
        else:
            success = orchestrator.run_full_pipeline(args.sources)
        
        # Exit code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n\nPipeline interrupted by user")
        orchestrator.generate_report()
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        orchestrator.generate_report()
        sys.exit(1)


if __name__ == "__main__":
    main()
