"""Database models for the posting system."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class ActivityType(str, Enum):
    """Types of activities that can be collected."""

    MATRIX_POST = "matrix_post"
    GITHUB_PR = "github_pr"
    GITHUB_ISSUE = "github_issue"
    GITHUB_COMMIT = "github_commit"
    GITHUB_RELEASE = "github_release"
    MWMBL_STATS = "mwmbl_stats"


class Platform(str, Enum):
    """Publishing platforms."""

    MASTODON = "mastodon"
    X = "x"
    BLOG = "blog"


class Activity(Base):
    """Model for storing collected activities."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activity_type: Mapped[ActivityType] = mapped_column(SQLEnum(ActivityType))
    source_id: Mapped[str] = mapped_column(String(255))  # External ID from source
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_newsworthy: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    __table_args__ = (
        UniqueConstraint("activity_type", "source_id", name="unique_activity"),
    )

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, type={self.activity_type}, title='{self.title[:50]}...')>"


class Post(Base):
    """Model for tracking published posts."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform))
    platform_post_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # ID from the platform
    content: Mapped[str] = mapped_column(Text)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_weekly_summary: Mapped[bool] = mapped_column(Boolean, default=False)
    week_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    week_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, platform={self.platform}, posted_at={self.posted_at})>"
