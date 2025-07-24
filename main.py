"""Main CLI interface for the posting system."""

import asyncio
import sys
from datetime import datetime, timedelta

import click
from loguru import logger

from config.settings import settings
from src.scheduler import TaskScheduler
from src.storage import db_manager


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    logger.remove()
    
    log_level = "DEBUG" if verbose else settings.log_level
    
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.add(
        settings.log_file,
        level=log_level,
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool) -> None:
    """Mwmbl posting system CLI."""
    setup_logging(verbose)


@cli.command()
async def init_db() -> None:
    """Initialize the database tables."""
    try:
        db_manager.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


@cli.command()
async def test_connections() -> None:
    """Test connections to all external services."""
    try:
        scheduler = TaskScheduler()
        results = await scheduler.test_all_connections()
        
        click.echo("\nConnection Test Results:")
        click.echo("=" * 30)
        
        for service, status in results.items():
            status_icon = "✅" if status else "❌"
            click.echo(f"{status_icon} {service}: {'Connected' if status else 'Failed'}")
        
        failed_count = sum(1 for status in results.values() if not status)
        if failed_count > 0:
            click.echo(f"\n⚠️  {failed_count} connection(s) failed")
            sys.exit(1)
        else:
            click.echo("\n🎉 All connections successful!")
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--hours", "-h", default=24, help="Hours to look back for activities")
async def collect(hours: int) -> None:
    """Collect activities from all sources."""
    try:
        db_manager.create_tables()
        scheduler = TaskScheduler()
        
        since = datetime.now() - timedelta(hours=hours)
        collected = await scheduler.run_data_collection(since)
        
        click.echo(f"✅ Collected {collected} activities from the last {hours} hours")
        
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        sys.exit(1)


@cli.command()
async def daily_post() -> None:
    """Run daily posting to social media platforms."""
    try:
        db_manager.create_tables()
        scheduler = TaskScheduler()
        
        # Collect recent activities first
        since = datetime.now() - timedelta(hours=2)
        collected = await scheduler.run_data_collection(since)
        logger.info(f"Collected {collected} recent activities")
        
        # Run daily posting
        results = await scheduler.run_daily_posting()
        
        click.echo("\nDaily Posting Results:")
        click.echo("=" * 25)
        
        for platform, result in results.items():
            if result.get("success"):
                posted = result.get("posted_count", 0)
                total = result.get("total_activities", 0)
                click.echo(f"✅ {platform}: Posted {posted}/{total} activities")
            else:
                error = result.get("error", "Unknown error")
                click.echo(f"❌ {platform}: {error}")
        
    except Exception as e:
        logger.error(f"Daily posting failed: {e}")
        sys.exit(1)


@cli.command()
async def weekly_post() -> None:
    """Run weekly posting (blog summary)."""
    try:
        db_manager.create_tables()
        scheduler = TaskScheduler()
        
        # Collect activities from the past week
        since = datetime.now() - timedelta(days=7)
        collected = await scheduler.run_data_collection(since)
        logger.info(f"Collected {collected} activities for weekly summary")
        
        # Run weekly posting
        result = await scheduler.run_weekly_posting()
        
        if result.get("success"):
            post_id = result.get("post_id")
            if post_id:
                click.echo(f"✅ Weekly summary posted successfully: {post_id}")
            else:
                click.echo(f"✅ {result.get('message', 'Weekly posting completed')}")
        else:
            error = result.get("error", "Unknown error")
            click.echo(f"❌ Weekly posting failed: {error}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Weekly posting failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--days", "-d", default=7, help="Number of days to show stats for")
async def stats(days: int) -> None:
    """Show posting statistics."""
    try:
        scheduler = TaskScheduler()
        stats_data = await scheduler.get_posting_stats(days)
        
        click.echo(f"\nPosting Statistics (Last {days} days):")
        click.echo("=" * 40)
        click.echo(f"Total posts: {stats_data['total_posts']}")
        click.echo(f"Weekly summaries: {stats_data['weekly_summaries']}")
        click.echo(f"Individual posts: {stats_data['individual_posts']}")
        
        if stats_data['by_platform']:
            click.echo("\nBy Platform:")
            for platform, count in stats_data['by_platform'].items():
                click.echo(f"  {platform}: {count}")
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        sys.exit(1)


@cli.command()
async def cleanup() -> None:
    """Clean up temporary files and repositories."""
    try:
        from src.publishers import BlogPublisher
        
        blog_publisher = BlogPublisher()
        await blog_publisher.cleanup_repo()
        
        click.echo("✅ Cleanup completed")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)


# Async command wrapper
def async_command(f):
    """Decorator to run async commands."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Apply async wrapper to all async commands
for command in [init_db, test_connections, collect, daily_post, weekly_post, stats, cleanup]:
    command.callback = async_command(command.callback)


if __name__ == "__main__":
    cli()
