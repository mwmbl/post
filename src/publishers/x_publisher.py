"""X (Twitter) publisher for posting to X/Twitter."""

from typing import Optional

import tweepy

from config.settings import settings
from src.storage import Activity, Platform

from .base import BasePublisher


class XPublisher(BasePublisher):
    """Publisher for X (formerly Twitter) social media platform."""

    def __init__(self) -> None:
        """Initialize the X publisher."""
        super().__init__(Platform.X)
        
        # Initialize Tweepy client with API v2
        self.client = tweepy.Client(
            bearer_token=settings.x_bearer_token,
            consumer_key=settings.x_api_key,
            consumer_secret=settings.x_api_secret,
            access_token=settings.x_access_token,
            access_token_secret=settings.x_access_token_secret,
            wait_on_rate_limit=True,
        )

    async def publish_activity(self, activity: Activity, content: str) -> Optional[str]:
        """Publish an activity to X.
        
        Args:
            activity: The activity to publish
            content: Formatted content ready for posting
            
        Returns:
            X post ID if successful, None otherwise
        """
        try:
            self.logger.info(f"Publishing activity to X: {activity.title}")
            
            # Post to X using API v2
            response = self.client.create_tweet(text=content)
            
            if response.data:
                post_id = str(response.data["id"])
                self.logger.info(f"Successfully posted to X: {post_id}")
                return post_id
            else:
                self.logger.error("X API returned no data")
                return None
            
        except Exception as e:
            self._handle_publish_error(e, "publishing activity to X")
            return None

    async def publish_weekly_summary(
        self, content: str, week_start_str: str, week_end_str: str
    ) -> Optional[str]:
        """Publish a weekly summary to X.
        
        Args:
            content: The weekly summary content
            week_start_str: Week start date as string
            week_end_str: Week end date as string
            
        Returns:
            X post ID if successful, None otherwise
        """
        try:
            # Create a summary post for X (character limit is strict)
            summary_content = self._create_summary_post(content, week_start_str, week_end_str)
            
            self.logger.info(f"Publishing weekly summary to X")
            
            response = self.client.create_tweet(text=summary_content)
            
            if response.data:
                post_id = str(response.data["id"])
                self.logger.info(f"Successfully posted weekly summary to X: {post_id}")
                return post_id
            else:
                self.logger.error("X API returned no data for weekly summary")
                return None
            
        except Exception as e:
            self._handle_publish_error(e, "publishing weekly summary to X")
            return None

    def _create_summary_post(self, content: str, week_start_str: str, week_end_str: str) -> str:
        """Create a summary post for X from blog content.
        
        Args:
            content: Full blog content
            week_start_str: Week start date as string
            week_end_str: Week end date as string
            
        Returns:
            Formatted summary for X (under 280 characters)
        """
        # Extract the title from the blog content
        lines = content.split('\n')
        title = lines[0].replace('#', '').strip() if lines else f"Weekly Update: {week_start_str} - {week_end_str}"
        
        # Create a very concise summary for X's character limit
        base_content = f"📊 {title}\n\nThis week in #mwmbl: development updates, community activity & progress stats.\n\nRead more: https://mwmbl.github.io/blog/\n\n#opensource #searchengine"
        
        # Ensure we're under the character limit
        if len(base_content) > 280:
            # Fallback to even shorter version
            base_content = f"📊 Weekly #mwmbl update: {week_start_str}-{week_end_str}\n\nDevelopment & community updates on our blog:\nhttps://mwmbl.github.io/blog/\n\n#opensource #searchengine"
        
        return base_content

    async def _test_connection_impl(self) -> bool:
        """Test connection to X."""
        try:
            # Verify credentials by getting user info
            user = self.client.get_me()
            if user.data:
                self.logger.info(f"Connected to X as @{user.data.username}")
                return True
            else:
                self.logger.error("X API returned no user data")
                return False
        except Exception as e:
            self.logger.error(f"X connection test failed: {e}")
            return False

    def get_post_url(self, post_id: str, username: str = None) -> str:
        """Get the URL for an X post.
        
        Args:
            post_id: The X post ID
            username: Optional username (will fetch if not provided)
            
        Returns:
            URL to the post
        """
        if not username:
            try:
                user = self.client.get_me()
                username = user.data.username if user.data else "unknown"
            except:
                username = "unknown"
        
        return f"https://x.com/{username}/status/{post_id}"

    async def create_thread(self, tweets: list[str]) -> Optional[list[str]]:
        """Create a thread of tweets.
        
        Args:
            tweets: List of tweet contents
            
        Returns:
            List of tweet IDs if successful, None otherwise
        """
        try:
            tweet_ids = []
            previous_tweet_id = None
            
            for i, tweet_content in enumerate(tweets):
                self.logger.info(f"Posting tweet {i+1}/{len(tweets)} in thread")
                
                if previous_tweet_id:
                    # Reply to previous tweet to create thread
                    response = self.client.create_tweet(
                        text=tweet_content,
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                else:
                    # First tweet in thread
                    response = self.client.create_tweet(text=tweet_content)
                
                if response.data:
                    tweet_id = str(response.data["id"])
                    tweet_ids.append(tweet_id)
                    previous_tweet_id = tweet_id
                else:
                    self.logger.error(f"Failed to post tweet {i+1} in thread")
                    return None
            
            self.logger.info(f"Successfully created thread with {len(tweet_ids)} tweets")
            return tweet_ids
            
        except Exception as e:
            self._handle_publish_error(e, "creating X thread")
            return None
