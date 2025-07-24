"""Content filtering for determining newsworthy activities."""

from datetime import datetime, timedelta
from typing import List

from loguru import logger
from sqlalchemy import and_, func

from config.settings import settings
from src.storage import Activity, Platform, Post, get_db_session


class ContentFilter:
    """Filters activities to determine what should be posted."""

    def __init__(self) -> None:
        """Initialize the content filter."""
        self.logger = logger.bind(component="ContentFilter")

    def get_newsworthy_activities(
        self, since: datetime, platform: Platform
    ) -> List[Activity]:
        """Get newsworthy activities that haven't been posted to the platform.
        
        Args:
            since: Get activities created after this datetime
            platform: The platform to check for existing posts
            
        Returns:
            List of newsworthy activities ready for posting
        """
        with get_db_session() as session:
            # Get activities that are newsworthy and haven't been posted to this platform
            activities = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.is_newsworthy == True,
                        Activity.created_at >= since,
                        ~Activity.id.in_(
                            session.query(Post.activity_id)
                            .filter(Post.platform == platform)
                            .filter(Post.activity_id.isnot(None))
                        ),
                    )
                )
                .order_by(Activity.created_at.desc())
                .limit(settings.max_daily_posts)
                .all()
            )

            # Apply additional filtering based on posting frequency
            filtered_activities = self._apply_frequency_filter(activities, platform)

            self.logger.info(
                f"Found {len(filtered_activities)} newsworthy activities for {platform}"
            )
            return filtered_activities

    def _apply_frequency_filter(
        self, activities: List[Activity], platform: Platform
    ) -> List[Activity]:
        """Apply frequency-based filtering to avoid spam.
        
        Args:
            activities: List of activities to filter
            platform: The platform being posted to
            
        Returns:
            Filtered list of activities
        """
        if not activities:
            return activities

        with get_db_session() as session:
            # Check when we last posted to this platform
            last_post = (
                session.query(Post)
                .filter(Post.platform == platform)
                .order_by(Post.posted_at.desc())
                .first()
            )

            if last_post:
                time_since_last_post = datetime.now() - last_post.posted_at
                min_interval = timedelta(hours=settings.min_post_interval_hours)

                if time_since_last_post < min_interval:
                    self.logger.info(
                        f"Skipping posts to {platform} - last post was {time_since_last_post} ago"
                    )
                    return []

            # Prioritize activities by type and recency
            prioritized_activities = self._prioritize_activities(activities)

            return prioritized_activities

    def _prioritize_activities(self, activities: List[Activity]) -> List[Activity]:
        """Prioritize activities based on type and importance.
        
        Args:
            activities: List of activities to prioritize
            
        Returns:
            Prioritized list of activities
        """
        # Define priority order (higher number = higher priority)
        priority_map = {
            "github_release": 10,
            "mwmbl_stats": 8,
            "matrix_post": 7,
            "github_pr": 6,
            "github_issue": 4,
            "github_commit": 2,
        }

        def get_priority(activity: Activity) -> int:
            base_priority = priority_map.get(activity.activity_type.value, 1)
            
            # Boost priority for recent activities
            hours_old = (datetime.now() - activity.created_at).total_seconds() / 3600
            recency_boost = max(0, 5 - hours_old)  # Up to 5 point boost for very recent
            
            return base_priority + recency_boost

        # Sort by priority (highest first)
        sorted_activities = sorted(activities, key=get_priority, reverse=True)

        self.logger.debug(
            f"Prioritized {len(sorted_activities)} activities: "
            f"{[f'{a.activity_type.value}({get_priority(a):.1f})' for a in sorted_activities[:5]]}"
        )

        return sorted_activities

    def get_weekly_summary_activities(
        self, start_date: datetime, end_date: datetime
    ) -> List[Activity]:
        """Get all activities for a weekly summary.
        
        Args:
            start_date: Start of the week
            end_date: End of the week
            
        Returns:
            List of activities from the week
        """
        with get_db_session() as session:
            activities = (
                session.query(Activity)
                .filter(
                    and_(
                        Activity.created_at >= start_date,
                        Activity.created_at <= end_date,
                    )
                )
                .order_by(Activity.activity_type, Activity.created_at.desc())
                .all()
            )

            self.logger.info(
                f"Found {len(activities)} activities for weekly summary "
                f"({start_date.date()} to {end_date.date()})"
            )
            return activities

    def mark_activity_as_posted(
        self, activity: Activity, platform: Platform, platform_post_id: str = None
    ) -> None:
        """Mark an activity as posted to a platform.
        
        Args:
            activity: The activity that was posted
            platform: The platform it was posted to
            platform_post_id: Optional ID from the platform
        """
        with get_db_session() as session:
            post = Post(
                activity_id=activity.id,
                platform=platform,
                platform_post_id=platform_post_id,
                content=activity.content[:1000],  # Truncate for storage
            )
            session.add(post)
            session.commit()

            self.logger.debug(
                f"Marked activity {activity.id} as posted to {platform}"
            )
