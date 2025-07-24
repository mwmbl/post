"""Weekly posting script."""

import asyncio
import sys
from datetime import datetime, timedelta

from loguru import logger

from config.settings import settings
from src.scheduler import TaskScheduler
from src.storage import db_manager


async def main() -> None:
    """Run weekly data collection and blog posting."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        settings.log_file,
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    logger.info("Starting weekly posting process")
    
    try:
        # Initialize database
        db_manager.create_tables()
        
        # Initialize scheduler
        scheduler = TaskScheduler()
        
        # Test connections first
        connection_results = await scheduler.test_all_connections()
        failed_connections = [k for k, v in connection_results.items() if not v]
        
        if failed_connections:
            logger.warning(f"Some connections failed: {failed_connections}")
            # Continue anyway - we might still be able to post to some platforms
        
        # Run data collection for the past week to ensure we have all activities
        since = datetime.now() - timedelta(days=7)
        collected = await scheduler.run_data_collection(since)
        logger.info(f"Collected {collected} activities for weekly summary")
        
        # Run weekly posting
        posting_result = await scheduler.run_weekly_posting()
        
        # Log results
        if posting_result.get("success"):
            post_id = posting_result.get("post_id")
            if post_id:
                logger.info(f"Weekly summary posted successfully: {post_id}")
            else:
                logger.info(f"Weekly posting completed: {posting_result.get('message', 'Success')}")
        else:
            error = posting_result.get("error", "Unknown error")
            logger.error(f"Weekly posting failed: {error}")
        
        # Get and log stats
        stats = await scheduler.get_posting_stats(days=7)
        logger.info(f"Weekly stats: {stats}")
        
        logger.info("Weekly posting process completed")
        
    except Exception as e:
        logger.error(f"Weekly posting process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
