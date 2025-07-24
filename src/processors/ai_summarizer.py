"""AI-powered content summarization using Claude."""

from datetime import datetime
from typing import List

from anthropic import Anthropic
from loguru import logger

from config.settings import settings
from src.storage import Activity


class AISummarizer:
    """Uses Claude AI to generate summaries of activities."""

    def __init__(self) -> None:
        """Initialize the AI summarizer."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.logger = logger.bind(component="AISummarizer")

    async def generate_weekly_summary(
        self, activities: List[Activity], week_start: datetime, week_end: datetime
    ) -> str:
        """Generate a weekly summary blog post using Claude.
        
        Args:
            activities: List of activities from the week
            week_start: Start date of the week
            week_end: End date of the week
            
        Returns:
            Generated blog post content in markdown format
        """
        if not activities:
            return self._generate_empty_week_summary(week_start, week_end)

        # Prepare activity data for Claude
        activity_data = self._prepare_activity_data(activities)
        
        # Create the prompt for Claude
        prompt = self._create_weekly_summary_prompt(activity_data, week_start, week_end)
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            summary = response.content[0].text
            self.logger.info(f"Generated weekly summary ({len(summary)} characters)")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating weekly summary: {e}")
            # Fallback to basic summary
            return self._generate_fallback_summary(activities, week_start, week_end)

    def _prepare_activity_data(self, activities: List[Activity]) -> str:
        """Prepare activity data for the AI prompt."""
        activity_lines = []
        
        for activity in activities:
            activity_info = [
                f"Type: {activity.activity_type.value}",
                f"Title: {activity.title}",
                f"Content: {activity.content[:200]}...",
                f"Author: {activity.author or 'Unknown'}",
                f"Date: {activity.created_at.strftime('%Y-%m-%d %H:%M')}",
            ]
            
            if activity.url:
                activity_info.append(f"URL: {activity.url}")
                
            activity_lines.append(" | ".join(activity_info))
        
        return "\n".join(activity_lines)

    def _create_weekly_summary_prompt(
        self, activity_data: str, week_start: datetime, week_end: datetime
    ) -> str:
        """Create the prompt for Claude to generate a weekly summary."""
        return f"""
You are writing a weekly summary blog post for Mwmbl, an open-source search engine project. 

Please create an engaging blog post summarizing the week's activities from {week_start.strftime('%B %d')} to {week_end.strftime('%B %d, %Y')}.

Here are the activities from this week:

{activity_data}

Please write a blog post that:
1. Has an engaging title
2. Provides a brief introduction to the week
3. Groups similar activities together logically
4. Highlights the most important developments
5. Uses a friendly, community-focused tone
6. Includes relevant emojis where appropriate
7. Ends with a forward-looking statement or call to action
8. Is formatted in markdown

Focus on:
- New releases and major features
- Community growth and engagement
- Development progress
- Statistical milestones
- Any significant issues resolved

Keep the tone professional but approachable, suitable for both technical and non-technical readers interested in the Mwmbl project.
"""

    def _generate_empty_week_summary(
        self, week_start: datetime, week_end: datetime
    ) -> str:
        """Generate a summary for weeks with no activities."""
        return f"""# Weekly Update: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}

This week was relatively quiet on the development front, but that doesn't mean progress has stopped! 

Sometimes the most important work happens behind the scenes - planning, research, and preparation for future features. The Mwmbl team continues to work on improving the search engine and building our community.

## What's Next?

Stay tuned for upcoming developments and consider contributing to the project if you're interested in open-source search technology.

---

*Want to get involved? Check out our [GitHub repositories](https://github.com/mwmbl) or join our [Matrix community](https://matrix.to/#/#mwmbl:matrix.org)!*
"""

    def _generate_fallback_summary(
        self, activities: List[Activity], week_start: datetime, week_end: datetime
    ) -> str:
        """Generate a basic fallback summary if AI fails."""
        self.logger.warning("Using fallback summary generation")
        
        content_parts = [
            f"# Weekly Update: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}",
            "",
            f"This week we had {len(activities)} activities across the Mwmbl project:",
            "",
        ]
        
        # Group activities by type
        activity_groups = {}
        for activity in activities:
            activity_type = activity.activity_type.value
            if activity_type not in activity_groups:
                activity_groups[activity_type] = []
            activity_groups[activity_type].append(activity)
        
        # Add each group
        for activity_type, group_activities in activity_groups.items():
            type_name = activity_type.replace('_', ' ').title()
            content_parts.append(f"## {type_name}")
            content_parts.append("")
            
            for activity in group_activities[:5]:  # Limit to 5 per group
                content_parts.append(f"- {activity.title}")
                if activity.url:
                    content_parts.append(f"  - [View details]({activity.url})")
            
            if len(group_activities) > 5:
                content_parts.append(f"- ...and {len(group_activities) - 5} more")
            
            content_parts.append("")
        
        content_parts.extend([
            "---",
            "",
            "*Want to get involved? Check out our [GitHub repositories](https://github.com/mwmbl) or join our [Matrix community](https://matrix.to/#/#mwmbl:matrix.org)!*"
        ])
        
        return "\n".join(content_parts)

    async def generate_social_post_summary(self, activity: Activity) -> str:
        """Generate a concise summary for social media posts.
        
        Args:
            activity: The activity to summarize
            
        Returns:
            Concise summary suitable for social media
        """
        if len(activity.content) <= 100:
            return activity.content
        
        prompt = f"""
Please create a concise, engaging summary of this activity for social media (under 100 characters):

Title: {activity.title}
Content: {activity.content}
Type: {activity.activity_type.value}

Make it informative but brief, suitable for Twitter/X or Mastodon. Focus on the key point or achievement.
"""
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Faster model for simple tasks
                max_tokens=100,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            summary = response.content[0].text.strip()
            self.logger.debug(f"Generated social summary: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating social summary: {e}")
            # Fallback to truncated content
            return activity.content[:97] + "..." if len(activity.content) > 100 else activity.content
