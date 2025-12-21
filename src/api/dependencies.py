"""
Dependency injection for FastAPI.
Provides singleton instances of services.
"""

from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Singleton instances (will be initialized on first access)
_llm_service = None
_dremio_client = None
_schema_inspector = None


@lru_cache()
def get_llm_service():
    """
    Get or create LLM service singleton.
    Handles both HuggingFace and Gemini models.
    """
    global _llm_service
    if _llm_service is None:
        from src.api.services.llm_service import LLMService
        _llm_service = LLMService()
        logger.info("LLM service instance created")
    return _llm_service


@lru_cache()
def get_dremio_client():
    """
    Get or create Dremio client singleton.
    """
    global _dremio_client
    if _dremio_client is None:
        from src.api.services.dremio_client import DremioClient
        _dremio_client = DremioClient()
        logger.info("Dremio client instance created")
    return _dremio_client


@lru_cache()
def get_schema_inspector():
    """
    Get or create schema inspector singleton.
    """
    global _schema_inspector
    if _schema_inspector is None:
        from src.api.services.schema_inspector import SchemaInspector
        dremio = get_dremio_client()
        _schema_inspector = SchemaInspector(dremio)
        logger.info("Schema inspector instance created")
    return _schema_inspector


def get_query_creator_bot():
    """
    Get Query Creator Bot instance.
    Creates new instance each time (not singleton).
    """
    from src.api.bots.query_creator import QueryCreatorBot
    llm_service = get_llm_service()
    schema_inspector = get_schema_inspector()
    return QueryCreatorBot(llm_service, schema_inspector)


def get_analytics_bot():
    """
    Get Analytics Bot instance.
    Creates new instance each time (not singleton).
    """
    from src.api.bots.analytics_bot import AnalyticsBot
    llm_service = get_llm_service()
    dremio_client = get_dremio_client()
    return AnalyticsBot(llm_service, dremio_client)


def cleanup_resources():
    """
    Cleanup resources on shutdown.
    Clears model cache and closes connections.
    """
    global _llm_service, _dremio_client, _schema_inspector

    try:
        if _llm_service is not None:
            logger.info("Cleaning up LLM service...")
            _llm_service.cleanup()

        if _dremio_client is not None:
            logger.info("Cleaning up Dremio client...")
            _dremio_client.close()

        _llm_service = None
        _dremio_client = None
        _schema_inspector = None

        # Clear lru_cache
        get_llm_service.cache_clear()
        get_dremio_client.cache_clear()
        get_schema_inspector.cache_clear()

        logger.info("Resource cleanup complete")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
