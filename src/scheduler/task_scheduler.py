"""Task scheduler for orchestrating data collection and posting."""

import asyncio
from datetime import datetime, timedelta
from typing import List

from loguru import logger

from config.settings import settings
from src.collectors import GitHubCollector, MatrixCollector, MwmblStatsCollector
from src.processors import AISummarizer, ContentFilter, ContentFormatter
from src.publishers import BlogPublisher, MastodonPublisher, XPublisher
from src.storage import Platform, Post, get_db_session


class TaskScheduler:
    """Orchestrates data collection and posting tasks."""

    def __init__(self) -> None:
        """Initialize the task scheduler."""
        self.logger = logger.bind(component="TaskScheduler")
        
        # Initialize collectors
        self.collectors = [
            GitHubCollector(),
            MatrixCollector(),
            MwmblStatsCollector(),
        ]
        
        # Initialize processors
        self.content_filter = ContentFilter()
        self.content_formatter = ContentFormatter()
        self.ai_summarizer = AISummarizer()
        
        # Initialize publishers
        self.publishers = {
            Platform.MASTODON: MastodonPublisher(),
            Platform.X: XPublisher(),
            Platform.BLOG: BlogPublisher(),
        }

    async def run_data_collection(self, since: datetime = None) -> int:
        """Run data collection from all sources.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            Total number of activities collected
        """
        self.logger.info("Starting data collection from all sources")
        
        total_collected = 0
        
        for collector in self.collectors:
            try:
                collected = await collector.run_collection(since)
                total_collected += collected
            except Exception as e:
                self.logger.error(f"Error in collector {collector.__class__.__name__}: {e}")
        
        self.logger.info(f"Data collection completed: {total_collected} total activities")
        return total_collected

    async def run_daily_posting(self) -> dict:
        """Run daily posting to social media platforms.
        
        Returns:
            Dictionary with posting results for each platform
        """
        self.logger.info("Starting daily posting process")
        
        results = {}
        since = datetime.now() - timedelta(days=1)  # Last 24 hours
        
        # Post to Mastodon and X
        for platform in [Platform.MASTODON, Platform.X]:
            try:
                result = await self._post_to_platform(platform, since)
                results[platform.value] = result
            except Exception as e:
                self.logger.error(f"Error posting to {platform.value}: {e}")
                results[platform.value] = {"success": False, "error": str(e)}
        
        self.logger.info(f"Daily posting completed: {results}")
        return results

    async def run_weekly_posting(self) -> dict:
        """Run weekly posting (blog summary).
        
        Returns:
            Dictionary with posting results
        """
        self.logger.info("Starting weekly posting process")
        
        # Calculate week boundaries (Monday to Sunday)
        today = datetime.now()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday, hours=today.hour, 
                                     minutes=today.minute, seconds=today.second, 
                                     microseconds=today.microsecond)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        try:
            # Get activities for the week
            activities = self.content_filter.get_weekly_summary_activities(week_start, week_end)
            
            if not activities:
                self.logger.info("No activities found for weekly summary")
                return {"success": True, "message": "No activities to summarize"}
            
            # Generate AI summary
            summary_content = await self.ai_summarizer.generate_weekly_summary(
                activities, week_start, week_end
            )
            
            # Post to blog
            blog_publisher = self.publishers[Platform.BLOG]
            post_id = await blog_publisher.publish_weekly_summary(
                summary_content,
                week_start.strftime("%Y-%m-%d"),
                week_end.strftime("%Y-%m-%d")
            )
            
            if post_id:
                # Record the weekly summary post
                await self._record_weekly_summary_post(
                    Platform.BLOG, post_id, summary_content, week_start, week_end
                )
                
                # Also post summary announcements to social media
                await self._announce_weekly_summary(summary_content, week_start, week_end)
                
                self.logger.info(f"Weekly summary posted successfully: {post_id}")
                return {"success": True, "post_id": post_id}
            else:
                return {"success": False, "error": "Failed to post weekly summary"}
                
        except Exception as e:
            self.logger.error(f"Error in weekly posting: {e}")
            return {"success": False, "error": str(e)}

    async def _post_to_platform(self, platform: Platform, since: datetime) -> dict:
        """Post newsworthy activities to a specific platform.
        
        Args:
            platform: The platform to post to
            since: Only consider activities created after this datetime
            
        Returns:
            Dictionary with posting results
        """
        try:
            # Get newsworthy activities
            activities = self.content_filter.get_newsworthy_activities(since, platform)
            
            if not activities:
                return {"success": True, "message": "No newsworthy activities to post"}
            
            publisher = self.publishers[platform]
            posted_count = 0
            
            for activity in activities:
                try:
                    # Format content for the platform
                    formatted_content = self.content_formatter.format_activity(activity, platform)
                    
                    # Publish the activity
                    post_id = await publisher.publish_activity(activity, formatted_content)
                    
                    if post_id:
                        # Mark as posted
                        self.content_filter.mark_activity_as_posted(activity, platform, post_id)
                        posted_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error posting activity {activity.id} to {platform.value}: {e}")
            
            return {
                "success": True,
                "posted_count": posted_count,
                "total_activities": len(activities)
            }
            
        except Exception as e:
            self.logger.error(f"Error posting to {platform.value}: {e}")
            return {"success": False, "error": str(e)}

    async def _announce_weekly_summary(
        self, summary_content: str, week_start: datetime, week_end: datetime
    ) -> None:
        """Announce the weekly summary on social media platforms.
        
        Args:
            summary_content: The blog summary content
            week_start: Start of the week
            week_end: End of the week
        """
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end_str = week_end.strftime("%Y-%m-%d")
        
        for platform in [Platform.MASTODON, Platform.X]:
            try:
                publisher = self.publishers[platform]
                post_id = await publisher.publish_weekly_summary(
                    summary_content, week_start_str, week_end_str
                )
                
                if post_id:
                    await self._record_weekly_summary_post(
                        platform, post_id, summary_content, week_start, week_end
                    )
                    self.logger.info(f"Weekly summary announced on {platform.value}: {post_id}")
                
            except Exception as e:
                self.logger.error(f"Error announcing weekly summary on {platform.value}: {e}")

    async def _record_weekly_summary_post(
        self, platform: Platform, post_id: str, content: str, 
        week_start: datetime, week_end: datetime
    ) -> None:
        """Record a weekly summary post in the database.
        
        Args:
            platform: The platform where it was posted
            post_id: Platform-specific post ID
            content: The post content
            week_start: Start of the week
            week_end: End of the week
        """
        try:
            with get_db_session() as session:
                post = Post(
                    platform=platform,
                    platform_post_id=post_id,
                    content=content[:1000],  # Truncate for storage
                    is_weekly_summary=True,
                    week_start=week_start,
                    week_end=week_end,
                )
                session.add(post)
                session.commit()
                
        except Exception as e:
            self.logger.error(f"Error recording weekly summary post: {e}")

    async def test_all_connections(self) -> dict:
        """Test connections to all external services.
        
        Returns:
            Dictionary with connection test results
        """
        self.logger.info("Testing connections to all services")
        
        results = {}
        
        # Test publishers
        for platform, publisher in self.publishers.items():
            try:
                connected = await publisher.test_connection()
                results[f"{platform.value}_publisher"] = connected
            except Exception as e:
                self.logger.error(f"Error testing {platform.value} publisher: {e}")
                results[f"{platform.value}_publisher"] = False
        
        # Test database connection
        try:
            with get_db_session() as session:
                session.execute("SELECT 1")
            results["database"] = True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            results["database"] = False
        
        self.logger.info(f"Connection test results: {results}")
        return results

    async def get_posting_stats(self, days: int = 7) -> dict:
        """Get posting statistics for the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with posting statistics
        """
        since = datetime.now() - timedelta(days=days)
        
        with get_db_session() as session:
            posts = session.query(Post).filter(Post.posted_at >= since).all()
            
            stats = {
                "total_posts": len(posts),
                "by_platform": {},
                "weekly_summaries": 0,
                "individual_posts": 0,
            }
            
            for post in posts:
                platform = post.platform.value
                if platform not in stats["by_platform"]:
                    stats["by_platform"][platform] = 0
                stats["by_platform"][platform] += 1
                
                if post.is_weekly_summary:
                    stats["weekly_summaries"] += 1
                else:
                    stats["individual_posts"] += 1
        
        return stats
