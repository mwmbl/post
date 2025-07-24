"""Content formatting for different platforms."""

import re
from typing import Dict, List

from loguru import logger

from src.storage import Activity, Platform


class ContentFormatter:
    """Formats content for different social media platforms."""

    def __init__(self) -> None:
        """Initialize the content formatter."""
        self.logger = logger.bind(component="ContentFormatter")

        # Platform-specific character limits
        self.limits = {
            Platform.MASTODON: 500,
            Platform.X: 280,
            Platform.BLOG: None,  # No limit for blog posts
        }

    def format_activity(self, activity: Activity, platform: Platform) -> str:
        """Format an activity for a specific platform.
        
        Args:
            activity: The activity to format
            platform: The target platform
            
        Returns:
            Formatted content string
        """
        if platform == Platform.BLOG:
            return self._format_for_blog(activity)
        elif platform == Platform.MASTODON:
            return self._format_for_mastodon(activity)
        elif platform == Platform.X:
            return self._format_for_x(activity)
        else:
            return self._format_generic(activity)

    def _format_for_mastodon(self, activity: Activity) -> str:
        """Format content for Mastodon."""
        content_parts = []
        
        # Add emoji based on activity type
        emoji = self._get_activity_emoji(activity)
        if emoji:
            content_parts.append(emoji)
        
        # Add title
        title = self._clean_title(activity.title)
        content_parts.append(title)
        
        # Add URL if available
        if activity.url:
            content_parts.append(f"\n🔗 {activity.url}")
        
        # Add hashtags
        hashtags = self._get_hashtags(activity)
        if hashtags:
            content_parts.append(f"\n{' '.join(hashtags)}")
        
        content = " ".join(content_parts)
        
        # Truncate if necessary
        return self._truncate_content(content, self.limits[Platform.MASTODON])

    def _format_for_x(self, activity: Activity) -> str:
        """Format content for X/Twitter."""
        content_parts = []
        
        # Add emoji
        emoji = self._get_activity_emoji(activity)
        if emoji:
            content_parts.append(emoji)
        
        # Add shortened title
        title = self._clean_title(activity.title)
        content_parts.append(title)
        
        # Add URL if available (X auto-shortens URLs)
        if activity.url:
            content_parts.append(activity.url)
        
        # Add hashtags (fewer for X due to character limit)
        hashtags = self._get_hashtags(activity, max_tags=2)
        if hashtags:
            content_parts.append(" ".join(hashtags))
        
        content = " ".join(content_parts)
        
        # Truncate if necessary
        return self._truncate_content(content, self.limits[Platform.X])

    def _format_for_blog(self, activity: Activity) -> str:
        """Format content for blog posts (markdown)."""
        content_parts = []
        
        # Add title as markdown header
        title = self._clean_title(activity.title)
        content_parts.append(f"### {title}")
        
        # Add content
        if activity.content and activity.content != title:
            content_parts.append(activity.content)
        
        # Add metadata
        if activity.author:
            content_parts.append(f"*By: {activity.author}*")
        
        # Add URL as markdown link
        if activity.url:
            content_parts.append(f"[View on {self._get_platform_name(activity)}]({activity.url})")
        
        return "\n\n".join(content_parts)

    def _format_generic(self, activity: Activity) -> str:
        """Generic formatting fallback."""
        return f"{activity.title}\n{activity.content[:200]}..."

    def _get_activity_emoji(self, activity: Activity) -> str:
        """Get appropriate emoji for activity type."""
        emoji_map = {
            "matrix_post": "💬",
            "github_pr": "🔀",
            "github_issue": "🐛",
            "github_commit": "📝",
            "github_release": "🚀",
            "mwmbl_stats": "📊",
        }
        return emoji_map.get(activity.activity_type.value, "📢")

    def _get_hashtags(self, activity: Activity, max_tags: int = 5) -> List[str]:
        """Generate relevant hashtags for an activity."""
        hashtags = ["#mwmbl"]
        
        # Add activity-type specific hashtags
        type_hashtags = {
            "matrix_post": ["#community"],
            "github_pr": ["#development", "#pullrequest"],
            "github_issue": ["#development", "#issue"],
            "github_commit": ["#development", "#commit"],
            "github_release": ["#release", "#update"],
            "mwmbl_stats": ["#stats", "#data"],
        }
        
        activity_tags = type_hashtags.get(activity.activity_type.value, [])
        hashtags.extend(activity_tags)
        
        # Add search engine related tags
        hashtags.extend(["#searchengine", "#opensource"])
        
        return hashtags[:max_tags]

    def _clean_title(self, title: str) -> str:
        """Clean and normalize title text."""
        # Remove excessive whitespace
        title = re.sub(r'\s+', ' ', title.strip())
        
        # Remove markdown formatting
        title = re.sub(r'[*_`]', '', title)
        
        # Remove issue/PR prefixes for cleaner display
        title = re.sub(r'^(PR #\d+:|Issue #\d+:|Commit:)\s*', '', title)
        
        return title

    def _get_platform_name(self, activity: Activity) -> str:
        """Get human-readable platform name from activity."""
        if "github" in activity.activity_type.value:
            return "GitHub"
        elif "matrix" in activity.activity_type.value:
            return "Matrix"
        elif "mwmbl" in activity.activity_type.value:
            return "Mwmbl"
        else:
            return "Source"

    def _truncate_content(self, content: str, max_length: int) -> str:
        """Truncate content to fit platform limits."""
        if not max_length or len(content) <= max_length:
            return content
        
        # Try to truncate at word boundary
        truncated = content[:max_length - 3]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can save most of the content
            truncated = truncated[:last_space]
        
        return truncated + "..."

    def format_weekly_summary(self, activities: List[Activity]) -> str:
        """Format a weekly summary of activities for blog post.
        
        Args:
            activities: List of activities from the week
            
        Returns:
            Formatted markdown content for blog post
        """
        if not activities:
            return "No significant activities this week."
        
        # Group activities by type
        grouped_activities = {}
        for activity in activities:
            activity_type = activity.activity_type.value
            if activity_type not in grouped_activities:
                grouped_activities[activity_type] = []
            grouped_activities[activity_type].append(activity)
        
        content_parts = []
        
        # Define section order and titles
        section_order = [
            ("github_release", "🚀 Releases"),
            ("mwmbl_stats", "📊 Statistics"),
            ("matrix_post", "💬 Community Updates"),
            ("github_pr", "🔀 Pull Requests"),
            ("github_issue", "🐛 Issues"),
            ("github_commit", "📝 Development Activity"),
        ]
        
        for activity_type, section_title in section_order:
            if activity_type in grouped_activities:
                activities_of_type = grouped_activities[activity_type]
                content_parts.append(f"## {section_title}")
                
                for activity in activities_of_type[:10]:  # Limit to 10 per section
                    formatted_activity = self._format_for_blog(activity)
                    content_parts.append(formatted_activity)
                
                if len(activities_of_type) > 10:
                    content_parts.append(f"*...and {len(activities_of_type) - 10} more*")
        
        return "\n\n".join(content_parts)
