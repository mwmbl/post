"""Base publisher class for all platform publishers."""

from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger

from src.storage import Activity, Platform


class BasePublisher(ABC):
    """Base class for all platform publishers."""

    def __init__(self, platform: Platform) -> None:
        """Initialize the publisher.
        
        Args:
            platform: The platform this publisher handles
        """
        self.platform = platform
        self.logger = logger.bind(publisher=self.__class__.__name__)

    @abstractmethod
    async def publish_activity(self, activity: Activity, content: str) -> Optional[str]:
        """Publish an activity to the platform.
        
        Args:
            activity: The activity to publish
            content: Formatted content ready for posting
            
        Returns:
            Platform-specific post ID if successful, None otherwise
        """
        pass

    @abstractmethod
    async def publish_weekly_summary(
        self, content: str, week_start_str: str, week_end_str: str
    ) -> Optional[str]:
        """Publish a weekly summary to the platform.
        
        Args:
            content: The weekly summary content
            week_start_str: Week start date as string
            week_end_str: Week end date as string
            
        Returns:
            Platform-specific post ID if successful, None otherwise
        """
        pass

    async def test_connection(self) -> bool:
        """Test the connection to the platform.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return await self._test_connection_impl()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    @abstractmethod
    async def _test_connection_impl(self) -> bool:
        """Platform-specific connection test implementation."""
        pass

    def _handle_publish_error(self, error: Exception, context: str) -> None:
        """Handle publishing errors with appropriate logging.
        
        Args:
            error: The exception that occurred
            context: Context description for the error
        """
        error_msg = str(error)
        
        # Check for common error types
        if "rate limit" in error_msg.lower():
            self.logger.warning(f"Rate limit hit while {context}: {error}")
        elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
            self.logger.error(f"Authentication error while {context}: {error}")
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            self.logger.warning(f"Network error while {context}: {error}")
        else:
            self.logger.error(f"Unexpected error while {context}: {error}")
