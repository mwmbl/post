"""Blog publisher for posting to GitHub Pages blog."""

import os
from datetime import datetime
from typing import Optional

from git import Repo
from loguru import logger

from config.settings import settings
from src.storage import Activity, Platform

from .base import BasePublisher


class BlogPublisher(BasePublisher):
    """Publisher for GitHub Pages blog."""

    def __init__(self) -> None:
        """Initialize the blog publisher."""
        super().__init__(Platform.BLOG)
        self.repo_path = settings.blog_repo_path
        self.repo_url = settings.blog_repo_url

    async def publish_activity(self, activity: Activity, content: str) -> Optional[str]:
        """Publish an individual activity to the blog.
        
        Note: Individual activities are not typically posted to the blog,
        only weekly summaries. This method is included for completeness.
        
        Args:
            activity: The activity to publish
            content: Formatted content ready for posting
            
        Returns:
            Blog post filename if successful, None otherwise
        """
        try:
            self.logger.info(f"Publishing individual activity to blog: {activity.title}")
            
            # Create a filename based on the activity
            date_str = datetime.now().strftime("%Y-%m-%d")
            safe_title = self._sanitize_filename(activity.title)
            filename = f"{date_str}-{safe_title}.md"
            
            # Create blog post content
            blog_content = self._create_individual_post(activity, content)
            
            # Write and commit the post
            success = await self._write_and_commit_post(filename, blog_content, f"Add post: {activity.title}")
            
            return filename if success else None
            
        except Exception as e:
            self._handle_publish_error(e, "publishing individual activity to blog")
            return None

    async def publish_weekly_summary(
        self, content: str, week_start_str: str, week_end_str: str
    ) -> Optional[str]:
        """Publish a weekly summary to the blog.
        
        Args:
            content: The weekly summary content
            week_start_str: Week start date as string
            week_end_str: Week end date as string
            
        Returns:
            Blog post filename if successful, None otherwise
        """
        try:
            self.logger.info(f"Publishing weekly summary to blog: {week_start_str} - {week_end_str}")
            
            # Create filename for weekly summary
            week_start_date = datetime.strptime(week_start_str, "%Y-%m-%d")
            filename = f"{week_start_date.strftime('%Y-%m-%d')}-weekly-update.md"
            
            # Add Jekyll front matter to the content
            blog_content = self._add_jekyll_frontmatter(content, week_start_str, week_end_str)
            
            # Write and commit the post
            success = await self._write_and_commit_post(
                filename, 
                blog_content, 
                f"Add weekly update: {week_start_str} to {week_end_str}"
            )
            
            return filename if success else None
            
        except Exception as e:
            self._handle_publish_error(e, "publishing weekly summary to blog")
            return None

    async def _write_and_commit_post(self, filename: str, content: str, commit_message: str) -> bool:
        """Write a blog post and commit it to the repository.
        
        Args:
            filename: The filename for the post
            content: The post content
            commit_message: Git commit message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clone or update the repository
            repo = await self._ensure_repo()
            if not repo:
                return False
            
            # Create the posts directory if it doesn't exist
            posts_dir = os.path.join(self.repo_path, "_posts")
            os.makedirs(posts_dir, exist_ok=True)
            
            # Write the post file
            post_path = os.path.join(posts_dir, filename)
            with open(post_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Add, commit, and push
            repo.index.add([post_path])
            repo.index.commit(
                commit_message,
                author_date=datetime.now().isoformat(),
                commit_date=datetime.now().isoformat(),
            )
            
            # Configure git user if not already set
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", settings.blog_author_name)
                git_config.set_value("user", "email", settings.blog_author_email)
            
            # Push to remote
            origin = repo.remote(name='origin')
            origin.push()
            
            self.logger.info(f"Successfully published blog post: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing and committing blog post: {e}")
            return False

    async def _ensure_repo(self) -> Optional[Repo]:
        """Ensure the blog repository is cloned and up to date.
        
        Returns:
            Git repository object if successful, None otherwise
        """
        try:
            if os.path.exists(self.repo_path):
                # Repository exists, pull latest changes
                repo = Repo(self.repo_path)
                origin = repo.remote(name='origin')
                origin.pull()
                self.logger.debug("Updated existing blog repository")
            else:
                # Clone the repository
                repo = Repo.clone_from(self.repo_url, self.repo_path)
                self.logger.info(f"Cloned blog repository to {self.repo_path}")
            
            return repo
            
        except Exception as e:
            self.logger.error(f"Error ensuring blog repository: {e}")
            return None

    def _add_jekyll_frontmatter(self, content: str, week_start_str: str, week_end_str: str) -> str:
        """Add Jekyll front matter to blog content.
        
        Args:
            content: The blog content
            week_start_str: Week start date string
            week_end_str: Week end date string
            
        Returns:
            Content with Jekyll front matter
        """
        # Extract title from content
        lines = content.split('\n')
        title = lines[0].replace('#', '').strip() if lines else f"Weekly Update: {week_start_str} - {week_end_str}"
        
        # Remove the title from content since it will be in front matter
        content_without_title = '\n'.join(lines[1:]).strip() if len(lines) > 1 else content
        
        # Create front matter
        frontmatter = f"""---
layout: post
title: "{title}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}
categories: [weekly-update]
tags: [mwmbl, development, community, stats]
author: {settings.blog_author_name}
---

"""
        
        return frontmatter + content_without_title

    def _create_individual_post(self, activity: Activity, content: str) -> str:
        """Create a blog post for an individual activity.
        
        Args:
            activity: The activity
            content: Formatted content
            
        Returns:
            Complete blog post content with front matter
        """
        # Create front matter for individual post
        frontmatter = f"""---
layout: post
title: "{activity.title}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}
categories: [activity]
tags: [mwmbl, {activity.activity_type.value.replace('_', '-')}]
author: {activity.author or settings.blog_author_name}
---

"""
        
        return frontmatter + content

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize a title for use as a filename.
        
        Args:
            title: The title to sanitize
            
        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        sanitized = title.lower()
        sanitized = ''.join(c if c.isalnum() or c in '-_' else '-' for c in sanitized)
        sanitized = '-'.join(word for word in sanitized.split('-') if word)  # Remove empty parts
        return sanitized[:50]  # Limit length

    async def _test_connection_impl(self) -> bool:
        """Test connection to the blog repository."""
        try:
            repo = await self._ensure_repo()
            if repo:
                self.logger.info(f"Successfully connected to blog repository")
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"Blog repository connection test failed: {e}")
            return False

    def get_post_url(self, filename: str) -> str:
        """Get the URL for a blog post.
        
        Args:
            filename: The blog post filename
            
        Returns:
            URL to the blog post
        """
        # Extract date and title from filename
        # Format: YYYY-MM-DD-title.md
        base_name = filename.replace('.md', '')
        return f"https://mwmbl.github.io/blog/{base_name}/"

    async def cleanup_repo(self) -> None:
        """Clean up the local repository directory."""
        try:
            if os.path.exists(self.repo_path):
                import shutil
                shutil.rmtree(self.repo_path)
                self.logger.info("Cleaned up blog repository directory")
        except Exception as e:
            self.logger.error(f"Error cleaning up repository: {e}")
