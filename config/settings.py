"""Configuration settings for the posting system."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/post_db",
        description="PostgreSQL database URL",
    )

    # Matrix
    matrix_homeserver: str = Field(
        default="https://matrix.org", description="Matrix homeserver URL"
    )
    matrix_username: str = Field(description="Matrix username (without @ symbol)")
    matrix_password: str = Field(description="Matrix password")
    matrix_room_id: str = Field(
        default="!mwmbl:matrix.org", description="Matrix room ID to monitor"
    )

    # GitHub
    github_token: str = Field(description="GitHub personal access token")
    github_org: str = Field(default="mwmbl", description="GitHub organization to monitor")

    # Mwmbl Stats API
    mwmbl_stats_url: str = Field(
        default="https://api.mwmbl.org/stats", description="Mwmbl stats API URL"
    )

    # Mastodon
    mastodon_instance_url: str = Field(description="Mastodon instance URL")
    mastodon_access_token: str = Field(description="Mastodon access token")

    # X/Twitter
    x_api_key: str = Field(description="X/Twitter API key")
    x_api_secret: str = Field(description="X/Twitter API secret")
    x_access_token: str = Field(description="X/Twitter access token")
    x_access_token_secret: str = Field(description="X/Twitter access token secret")
    x_bearer_token: str = Field(description="X/Twitter bearer token")

    # Anthropic Claude
    anthropic_api_key: str = Field(description="Anthropic API key for Claude")

    # Blog
    blog_repo_url: str = Field(
        default="https://github.com/mwmbl/blog.git", description="Blog repository URL"
    )
    blog_repo_path: str = Field(
        default="/tmp/blog", description="Local path for blog repository"
    )
    blog_author_name: str = Field(default="Mwmbl Bot", description="Blog post author name")
    blog_author_email: str = Field(
        default="bot@mwmbl.org", description="Blog post author email"
    )

    # Scheduling
    daily_post_time: str = Field(
        default="09:00", description="Daily posting time (HH:MM format)"
    )
    weekly_post_day: str = Field(
        default="monday", description="Weekly posting day"
    )
    weekly_post_time: str = Field(
        default="10:00", description="Weekly posting time (HH:MM format)"
    )

    # Content filtering
    min_post_interval_hours: int = Field(
        default=1, description="Minimum hours between posts to same platform"
    )
    max_daily_posts: int = Field(
        default=10, description="Maximum posts per day per platform"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="post.log", description="Log file path")


# Global settings instance
settings = Settings()
