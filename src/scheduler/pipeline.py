"""
Pipeline Orchestrator
Coordena a execução completa do pipeline de dados
"""
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import traceback

from . import config


# ============================================================
# LOGGING SETUP
# ============================================================

def setup_logger(run_id: str) -> logging.Logger:
    """Setup logger para esta execução"""
    logger = logging.getLogger(f'pipeline_{run_id}')
    logger.setLevel(logging.INFO)
    
    # File handler
    log_file = config.LOGS_DIR / f"pipeline_{run_id}.log"
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


# ============================================================
# PIPELINE EXECUTOR
# ============================================================

class PipelineOrchestrator:
    """Orquestra a execução completa do pipeline"""
    
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.logger = setup_logger(self.run_id)
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'extractors': {},
            'processors': {},
            'gold': {},
            'errors': []
        }
    
    def run(self) -> Dict:
        """Executa pipeline completo"""
        self.logger.info("=" * 60)
        self.logger.info(f" Iniciando Pipeline Run: {self.run_id}")
        self.logger.info("=" * 60)
        
        try:
            # Phase 1: Extraction (Bronze)
            self.logger.info("\n PHASE 1: EXTRACTION (Bronze)")
            extraction_success = self._run_extractors()
            
            if not extraction_success and not config.CONTINUE_ON_ERROR:
                self.logger.error(" Extraction failed. Aborting pipeline.")
                return self._finalize_stats(success=False)
            
            # Phase 2: Processing (Silver)
            self.logger.info("\n PHASE 2: PROCESSING (Silver)")
            processing_success = self._run_processors()
            
            if not processing_success and not config.CONTINUE_ON_ERROR:
                self.logger.error(" Processing failed. Aborting pipeline.")
                return self._finalize_stats(success=False)
            
            # Phase 3: Gold Layer
            self.logger.info("\n PHASE 3: GOLD LAYER")
            gold_success = self._run_gold_layer()
            
            if not gold_success:
                self.logger.error(" Gold layer generation failed.")
                return self._finalize_stats(success=False)
            
            # Phase 4: Upload to MinIO (opcional)
            if config.UPLOAD_TO_MINIO:
                self.logger.info("\n  PHASE 4: UPLOAD TO MINIO")
                self._upload_to_minio()
            
            self.logger.info("\n" + "=" * 60)
            self.logger.info(" Pipeline completed successfully!")
            self.logger.info("=" * 60)
            
            return self._finalize_stats(success=True)
            
        except Exception as e:
            self.logger.error(f" Pipeline failed with exception: {e}")
            self.logger.error(traceback.format_exc())
            self.stats['errors'].append({
                'phase': 'pipeline',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return self._finalize_stats(success=False)
    
    def _run_extractors(self) -> bool:
        """Executa todos os extractors"""
        all_success = True
        
        for source in config.EXTRACTOR_ORDER:
            self.logger.info(f"\n Extracting: {source}")
            success, stats = self._run_extractor(source)
            
            self.stats['extractors'][source] = {
                'success': success,
                'stats': stats
            }
            
            if not success:
                self.logger.error(f" {source} extraction failed")
                all_success = False
                if not config.CONTINUE_ON_ERROR:
                    break
            else:
                self.logger.info(f" {source} extraction completed")
        
        return all_success
    
    def _run_extractor(self, source: str) -> Tuple[bool, Dict]:
        """Executa um extractor específico"""
        try:
            cmd = [
                sys.executable,
                '-m', f'src.extractors.{source}.main'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hora timeout
            )
            
            if result.returncode == 0:
                return True, {'output': result.stdout}
            else:
                self.logger.error(f"Extractor stderr: {result.stderr}")
                self.stats['errors'].append({
                    'phase': 'extraction',
                    'source': source,
                    'error': result.stderr
                })
                return False, {'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            error_msg = f"Extractor timeout after 1 hour"
            self.logger.error(error_msg)
            self.stats['errors'].append({
                'phase': 'extraction',
                'source': source,
                'error': error_msg
            })
            return False, {'error': error_msg}
        except Exception as e:
            self.logger.error(f"Extractor exception: {e}")
            self.stats['errors'].append({
                'phase': 'extraction',
                'source': source,
                'error': str(e)
            })
            return False, {'error': str(e)}
    
    def _run_processors(self) -> bool:
        """Executa todos os processors"""
        all_success = True
        
        for source in config.PROCESSOR_ORDER:
            self.logger.info(f"\n  Processing: {source}")
            success, stats = self._run_processor(source)
            
            self.stats['processors'][source] = {
                'success': success,
                'stats': stats
            }
            
            if not success:
                self.logger.error(f" {source} processing failed")
                all_success = False
                if not config.CONTINUE_ON_ERROR:
                    break
            else:
                self.logger.info(f" {source} processing completed")
        
        return all_success
    
    def _run_processor(self, source: str) -> Tuple[bool, Dict]:
        """Executa um processor específico"""
        try:
            cmd = [
                sys.executable,
                '-m', f'src.processing.{source}.main'
            ]
            
            # Adiciona flag --all para processar tudo
            cmd.append('--all')
            
            result = subprocess.run(
                cmd,
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hora timeout
            )
            
            if result.returncode == 0:
                return True, {'output': result.stdout}
            else:
                self.logger.error(f"Processor stderr: {result.stderr}")
                self.stats['errors'].append({
                    'phase': 'processing',
                    'source': source,
                    'error': result.stderr
                })
                return False, {'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            error_msg = f"Processor timeout after 1 hour"
            self.logger.error(error_msg)
            self.stats['errors'].append({
                'phase': 'processing',
                'source': source,
                'error': error_msg
            })
            return False, {'error': error_msg}
        except Exception as e:
            self.logger.error(f"Processor exception: {e}")
            self.stats['errors'].append({
                'phase': 'processing',
                'source': source,
                'error': str(e)
            })
            return False, {'error': str(e)}
    
    def _run_gold_layer(self) -> bool:
        """Executa geração do Gold layer"""
        try:
            self.logger.info(" Generating Gold layer...")
            
            cmd = [
                sys.executable,
                '-m', 'src.gold_layer.main'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos timeout
            )
            
            if result.returncode == 0:
                self.logger.info(" Gold layer generated successfully")
                self.stats['gold'] = {
                    'success': True,
                    'output': result.stdout
                }
                return True
            else:
                self.logger.error(f"Gold layer stderr: {result.stderr}")
                self.stats['gold'] = {
                    'success': False,
                    'error': result.stderr
                }
                self.stats['errors'].append({
                    'phase': 'gold',
                    'error': result.stderr
                })
                return False
                
        except Exception as e:
            self.logger.error(f"Gold layer exception: {e}")
            self.stats['gold'] = {
                'success': False,
                'error': str(e)
            }
            self.stats['errors'].append({
                'phase': 'gold',
                'error': str(e)
            })
            return False
    
    def _upload_to_minio(self) -> bool:
        """Upload Gold layer para MinIO"""
        try:
            self.logger.info("  Uploading to MinIO...")
            
            cmd = [
                sys.executable,
                '-m', 'src.gold_layer.upload_to_minio'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos timeout
            )
            
            if result.returncode == 0:
                self.logger.info(" Upload to MinIO completed")
                return True
            else:
                self.logger.warning(f"  MinIO upload warning: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.warning(f"  MinIO upload exception: {e}")
            return False
    
    def _finalize_stats(self, success: bool) -> Dict:
        """Finaliza estatísticas da execução"""
        self.stats['end_time'] = datetime.now()
        self.stats['duration_seconds'] = (
            self.stats['end_time'] - self.stats['start_time']
        ).total_seconds()
        self.stats['success'] = success
        
        # Log summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info(" EXECUTION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Run ID: {self.run_id}")
        self.logger.info(f"Duration: {self.stats['duration_seconds']:.2f} seconds")
        self.logger.info(f"Success: {success}")
        self.logger.info(f"Errors: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            self.logger.info("\n Errors encountered:")
            for error in self.stats['errors']:
                self.logger.info(f"  - {error['phase']}: {error.get('source', 'N/A')}")
        
        return self.stats


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def run_pipeline(run_id: Optional[str] = None) -> Dict:
    """Executa pipeline completo - função conveniente"""
    orchestrator = PipelineOrchestrator(run_id)
    return orchestrator.run()


if __name__ == '__main__':
    # Para testes: python -m src.scheduler.pipeline
    stats = run_pipeline()
    sys.exit(0 if stats['success'] else 1)
