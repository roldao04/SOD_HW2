"""
LLM Service Layer - Unified interface for Gemini models.
Handles model initialization, inference, and resource management.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

from src.api.config import settings

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Supported model types."""
    QUERY_CREATOR = "query_creator"  # Gemini (SQL Generation)
    ANALYTICS = "analytics"  # Gemini (Analytics)


class LLMService:
    """
    Unified LLM service using Gemini API for all tasks.
    """

    def __init__(self):
        """Initialize LLM service."""
        self._query_creator_model = None
        self._analytics_model = None
        self._initialized = False

        logger.info("LLM Service initialized")

    async def initialize(self):
        """
        Initialize Gemini models asynchronously.
        This is called during app startup.
        """
        if self._initialized:
            logger.info("LLM Service already initialized")
            return

        try:
            # Initialize Gemini clients
            logger.info("Initializing Gemini models...")
            self._initialize_gemini()

            self._initialized = True
            logger.info("LLM Service initialization complete")

        except Exception as e:
            logger.error(f"Error during LLM Service initialization: {e}")
            raise

    def _initialize_gemini(self):
        """
        Initialize Gemini API clients for both query creation and analytics.
        """
        try:
            import google.generativeai as genai

            if not settings.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY not set - Service will not be available")
                raise ValueError("GEMINI_API_KEY is required")

            # Configure Gemini API
            genai.configure(api_key=settings.GEMINI_API_KEY)

            # Create Query Creator model instance
            self._query_creator_model = genai.GenerativeModel(
                model_name=settings.QUERY_CREATOR_MODEL,
                generation_config={
                    "temperature": settings.QUERY_CREATOR_TEMPERATURE,
                    "max_output_tokens": settings.QUERY_CREATOR_MAX_TOKENS,
                }
            )
            logger.info(f"Query Creator model initialized: {settings.QUERY_CREATOR_MODEL}")

            # Create Analytics model instance
            self._analytics_model = genai.GenerativeModel(
                model_name=settings.ANALYTICS_MODEL,
                generation_config={
                    "temperature": settings.ANALYTICS_TEMPERATURE,
                    "max_output_tokens": settings.ANALYTICS_MAX_TOKENS,
                }
            )
            logger.info(f"Analytics model initialized: {settings.ANALYTICS_MODEL}")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    def generate_query_creator(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """
        Generate SQL using Gemini model (Query Creator).

        Args:
            prompt: Input prompt with schema and user query
            max_tokens: Maximum tokens to generate (overrides config)
            temperature: Sampling temperature (overrides config)

        Returns:
            Generated SQL query or None if failed
        """
        if self._query_creator_model is None:
            logger.error("Query Creator model not initialized")
            return None

        try:
            # Override generation config if parameters provided
            if max_tokens is not None or temperature is not None:
                import google.generativeai as genai
                model = genai.GenerativeModel(
                    model_name=settings.QUERY_CREATOR_MODEL,
                    generation_config={
                        "temperature": temperature if temperature is not None else settings.QUERY_CREATOR_TEMPERATURE,
                        "max_output_tokens": max_tokens if max_tokens is not None else settings.QUERY_CREATOR_MAX_TOKENS,
                    }
                )
            else:
                model = self._query_creator_model

            # Generate content
            response = model.generate_content(prompt)

            if response and response.text:
                logger.info("SQL generated successfully")
                return response.text
            else:
                logger.warning("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return None

    def generate_analytics(
        self,
        prompt: str,
    ) -> Optional[str]:
        """
        Generate analytics insights using Gemini API.

        Args:
            prompt: Input prompt with data and analysis request

        Returns:
            Generated analysis or None if failed
        """
        if self._analytics_model is None:
            logger.error("Analytics model not initialized")
            return None

        try:
            # Generate content
            response = self._analytics_model.generate_content(prompt)

            if response and response.text:
                logger.info("Analytics generated successfully")
                return response.text
            else:
                logger.warning("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Error generating analytics: {e}")
            return None

    def generate(
        self,
        prompt: str,
        model_type: ModelType,
        **kwargs
    ) -> Optional[str]:
        """
        Unified generation interface.

        Args:
            prompt: Input prompt
            model_type: Which model to use (QUERY_CREATOR or ANALYTICS)
            **kwargs: Additional generation parameters

        Returns:
            Generated text or None if failed
        """
        if model_type == ModelType.QUERY_CREATOR:
            return self.generate_query_creator(prompt, **kwargs)
        elif model_type == ModelType.ANALYTICS:
            return self.generate_analytics(prompt, **kwargs)
        else:
            logger.error(f"Unknown model type: {model_type}")
            return None

    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    def get_model_status(self) -> Dict[str, bool]:
        """
        Get status of loaded models.

        Returns:
            Dictionary with model availability status
        """
        return {
            "query_creator": self._query_creator_model is not None,
            "analytics": self._analytics_model is not None,
            "initialized": self._initialized
        }

    def cleanup(self):
        """
        Cleanup models and free memory.
        """
        try:
            logger.info("Cleaning up Gemini models...")

            if self._query_creator_model is not None:
                self._query_creator_model = None

            if self._analytics_model is not None:
                self._analytics_model = None

            self._initialized = False
            logger.info("LLM Service cleanup complete")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
