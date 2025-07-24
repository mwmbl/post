"""GitHub activity collector."""

from datetime import datetime
from typing import List, Optional

from github import Github
from github.PaginatedList import PaginatedList

from config.settings import settings
from src.storage import Activity, ActivityType

from .base import BaseCollector


class GitHubCollector(BaseCollector):
    """Collects activities from GitHub repositories."""

    def __init__(self) -> None:
        """Initialize the GitHub collector."""
        super().__init__(ActivityType.GITHUB_PR)
        self.github = Github(settings.github_token)
        self.org = self.github.get_organization(settings.github_org)

    async def collect(self, since: Optional[datetime] = None) -> List[Activity]:
        """Collect GitHub activities.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            List of collected activities
        """
        activities = []
        
        # Get all repositories in the organization
        repos = self.org.get_repos()
        
        for repo in repos:
            self.logger.debug(f"Collecting activities from {repo.name}")
            
            # Collect pull requests
            activities.extend(await self._collect_pull_requests(repo, since))
            
            # Collect issues
            activities.extend(await self._collect_issues(repo, since))
            
            # Collect releases
            activities.extend(await self._collect_releases(repo, since))
            
            # Collect recent commits (only from main/master branch)
            activities.extend(await self._collect_commits(repo, since))
        
        return activities

    async def _collect_pull_requests(self, repo, since: Optional[datetime] = None) -> List[Activity]:
        """Collect pull requests from a repository."""
        activities = []
        
        try:
            prs = repo.get_pulls(state="all", sort="updated", direction="desc")
            
            for pr in prs:
                if since and pr.created_at < since:
                    break
                    
                # Determine if this PR is newsworthy
                is_newsworthy = (
                    pr.state == "closed" and pr.merged and
                    (pr.additions + pr.deletions) > 10  # Significant changes
                )
                
                activity = self._create_activity(
                    source_id=f"pr_{repo.name}_{pr.number}",
                    title=f"PR #{pr.number}: {pr.title}",
                    content=pr.body or f"Pull request in {repo.name}",
                    created_at=pr.created_at,
                    url=pr.html_url,
                    author=pr.user.login if pr.user else None,
                    extra_data={
                        "repo": repo.name,
                        "state": pr.state,
                        "merged": pr.merged,
                        "additions": pr.additions,
                        "deletions": pr.deletions,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error collecting PRs from {repo.name}: {e}")
            
        return activities

    async def _collect_issues(self, repo, since: Optional[datetime] = None) -> List[Activity]:
        """Collect issues from a repository."""
        activities = []
        
        try:
            issues = repo.get_issues(state="all", sort="updated", direction="desc")
            
            for issue in issues:
                if issue.pull_request:  # Skip PRs (they appear as issues too)
                    continue
                    
                if since and issue.created_at < since:
                    break
                
                # Issues are newsworthy if they're labeled as important or are closed
                labels = [label.name.lower() for label in issue.labels]
                is_newsworthy = (
                    issue.state == "closed" or
                    any(label in labels for label in ["bug", "enhancement", "feature"])
                )
                
                activity = self._create_activity(
                    source_id=f"issue_{repo.name}_{issue.number}",
                    title=f"Issue #{issue.number}: {issue.title}",
                    content=issue.body or f"Issue in {repo.name}",
                    created_at=issue.created_at,
                    url=issue.html_url,
                    author=issue.user.login if issue.user else None,
                    extra_data={
                        "repo": repo.name,
                        "state": issue.state,
                        "labels": labels,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error collecting issues from {repo.name}: {e}")
            
        return activities

    async def _collect_releases(self, repo, since: Optional[datetime] = None) -> List[Activity]:
        """Collect releases from a repository."""
        activities = []
        
        try:
            releases = repo.get_releases()
            
            for release in releases:
                if since and release.created_at < since:
                    break
                
                # All releases are newsworthy
                activity = self._create_activity(
                    source_id=f"release_{repo.name}_{release.id}",
                    title=f"Release {release.tag_name}: {release.name or release.tag_name}",
                    content=release.body or f"New release in {repo.name}",
                    created_at=release.created_at,
                    url=release.html_url,
                    author=release.author.login if release.author else None,
                    extra_data={
                        "repo": repo.name,
                        "tag_name": release.tag_name,
                        "prerelease": release.prerelease,
                        "draft": release.draft,
                    },
                    is_newsworthy=True,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error collecting releases from {repo.name}: {e}")
            
        return activities

    async def _collect_commits(self, repo, since: Optional[datetime] = None) -> List[Activity]:
        """Collect recent commits from the main branch."""
        activities = []
        
        try:
            # Get the default branch
            default_branch = repo.default_branch
            commits = repo.get_commits(sha=default_branch)
            
            # Only collect the most recent commits (limit to avoid spam)
            commit_count = 0
            for commit in commits:
                if commit_count >= 10:  # Limit to 10 most recent commits
                    break
                    
                if since and commit.commit.author.date < since:
                    break
                
                # Commits are newsworthy if they're significant (multiple files changed)
                files_changed = len(commit.files) if commit.files else 0
                is_newsworthy = files_changed > 3
                
                activity = self._create_activity(
                    source_id=f"commit_{repo.name}_{commit.sha}",
                    title=f"Commit: {commit.commit.message.split('\n')[0][:100]}",
                    content=commit.commit.message,
                    created_at=commit.commit.author.date,
                    url=commit.html_url,
                    author=commit.author.login if commit.author else commit.commit.author.name,
                    extra_data={
                        "repo": repo.name,
                        "sha": commit.sha,
                        "files_changed": files_changed,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                commit_count += 1
                
        except Exception as e:
            self.logger.error(f"Error collecting commits from {repo.name}: {e}")
            
        return activities
