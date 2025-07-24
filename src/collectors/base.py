"""Base collector class for all data collectors."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.storage import Activity, ActivityType, get_db_session


class BaseCollector(ABC):
    """Base class for all data collectors."""

    def __init__(self, activity_type: ActivityType) -> None:
        """Initialize the collector.
        
        Args:
            activity_type: The type of activities this collector handles
        """
        self.activity_type = activity_type
        self.logger = logger.bind(collector=self.__class__.__name__)

    @abstractmethod
    async def collect(self, since: Optional[datetime] = None) -> List[Activity]:
        """Collect activities from the source.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            List of collected activities
        """
        pass

    def _create_activity(
        self,
        source_id: str,
        title: str,
        content: str,
        created_at: datetime,
        url: Optional[str] = None,
        author: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        is_newsworthy: bool = False,
    ) -> Activity:
        """Create an Activity object.
        
        Args:
            source_id: Unique identifier from the source system
            title: Activity title
            content: Activity content
            created_at: When the activity was created
            url: Optional URL to the activity
            author: Optional author of the activity
            extra_data: Optional extra data dictionary
            is_newsworthy: Whether this activity is considered newsworthy
            
        Returns:
            Activity object
        """
        return Activity(
            activity_type=self.activity_type,
            source_id=source_id,
            title=title,
            content=content,
            created_at=created_at,
            url=url,
            author=author,
            is_newsworthy=is_newsworthy,
            extra_data=json.dumps(extra_data) if extra_data else None,
        )

    def _save_activities(self, activities: List[Activity]) -> int:
        """Save activities to the database.
        
        Args:
            activities: List of activities to save
            
        Returns:
            Number of activities successfully saved
        """
        saved_count = 0
        
        with get_db_session() as session:
            for activity in activities:
                try:
                    session.add(activity)
                    session.flush()  # Flush to get any database errors
                    saved_count += 1
                    self.logger.debug(f"Saved activity: {activity.title}")
                except IntegrityError:
                    session.rollback()
                    self.logger.debug(f"Activity already exists: {activity.source_id}")
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Error saving activity {activity.source_id}: {e}")
                    
        self.logger.info(f"Saved {saved_count} new activities")
        return saved_count

    async def run_collection(self, since: Optional[datetime] = None) -> int:
        """Run the collection process.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            Number of activities collected and saved
        """
        try:
            self.logger.info(f"Starting collection for {self.activity_type}")
            activities = await self.collect(since)
            saved_count = self._save_activities(activities)
            self.logger.info(f"Collection completed: {saved_count} activities saved")
            return saved_count
        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            raise
