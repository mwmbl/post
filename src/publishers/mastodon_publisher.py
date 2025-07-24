"""Mastodon publisher for posting to Mastodon instances."""

from typing import Optional

from mastodon import Mastodon

from config.settings import settings
from src.storage import Activity, Platform

from .base import BasePublisher


class MastodonPublisher(BasePublisher):
    """Publisher for Mastodon social media platform."""

    def __init__(self) -> None:
        """Initialize the Mastodon publisher."""
        super().__init__(Platform.MASTODON)
        self.mastodon = Mastodon(
            access_token=settings.mastodon_access_token,
            api_base_url=settings.mastodon_instance_url,
        )

    async def publish_activity(self, activity: Activity, content: str) -> Optional[str]:
        """Publish an activity to Mastodon.
        
        Args:
            activity: The activity to publish
            content: Formatted content ready for posting
            
        Returns:
            Mastodon post ID if successful, None otherwise
        """
        try:
            self.logger.info(f"Publishing activity to Mastodon: {activity.title}")
            
            # Post to Mastodon
            status = self.mastodon.status_post(
                status=content,
                visibility="public",
                language="en",
            )
            
            post_id = str(status["id"])
            self.logger.info(f"Successfully posted to Mastodon: {post_id}")
            return post_id
            
        except Exception as e:
            self._handle_publish_error(e, "publishing activity to Mastodon")
            return None

    async def publish_weekly_summary(
        self, content: str, week_start_str: str, week_end_str: str
    ) -> Optional[str]:
        """Publish a weekly summary to Mastodon.
        
        Args:
            content: The weekly summary content
            week_start_str: Week start date as string
            week_end_str: Week end date as string
            
        Returns:
            Mastodon post ID if successful, None otherwise
        """
        try:
            # Create a summary post for Mastodon (since full blog content would be too long)
            summary_content = self._create_summary_post(content, week_start_str, week_end_str)
            
            self.logger.info(f"Publishing weekly summary to Mastodon")
            
            status = self.mastodon.status_post(
                status=summary_content,
                visibility="public",
                language="en",
            )
            
            post_id = str(status["id"])
            self.logger.info(f"Successfully posted weekly summary to Mastodon: {post_id}")
            return post_id
            
        except Exception as e:
            self._handle_publish_error(e, "publishing weekly summary to Mastodon")
            return None

    def _create_summary_post(self, content: str, week_start_str: str, week_end_str: str) -> str:
        """Create a summary post for Mastodon from blog content.
        
        Args:
            content: Full blog content
            week_start_str: Week start date as string
            week_end_str: Week end date as string
            
        Returns:
            Formatted summary for Mastodon
        """
        # Extract the title from the blog content
        lines = content.split('\n')
        title = lines[0].replace('#', '').strip() if lines else f"Weekly Update: {week_start_str} - {week_end_str}"
        
        # Create a concise summary
        summary_parts = [
            f"📊 {title}",
            "",
            "This week in #mwmbl:",
            "• Development updates",
            "• Community activity", 
            "• Statistics & progress",
            "",
            "Read the full update on our blog! 👇",
            "https://mwmbl.github.io/blog/",
            "",
            "#opensource #searchengine #community"
        ]
        
        return "\n".join(summary_parts)

    async def _test_connection_impl(self) -> bool:
        """Test connection to Mastodon."""
        try:
            # Verify credentials by getting account info
            account = self.mastodon.me()
            self.logger.info(f"Connected to Mastodon as @{account['username']}")
            return True
        except Exception as e:
            self.logger.error(f"Mastodon connection test failed: {e}")
            return False

    def get_post_url(self, post_id: str) -> str:
        """Get the URL for a Mastodon post.
        
        Args:
            post_id: The Mastodon post ID
            
        Returns:
            URL to the post
        """
        # Extract instance domain from the API base URL
        instance_domain = settings.mastodon_instance_url.replace("https://", "").replace("http://", "")
        return f"https://{instance_domain}/@{self.mastodon.me()['username']}/{post_id}"
