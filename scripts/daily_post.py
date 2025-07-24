"""Daily posting script."""

import asyncio
import sys
from datetime import datetime, timedelta

from loguru import logger

from config.settings import settings
from src.scheduler import TaskScheduler
from src.storage import db_manager


async def main() -> None:
    """Run daily data collection and posting."""
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

    logger.info("Starting daily posting process")
    
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
        
        # Run data collection (last 2 hours to catch recent activities)
        since = datetime.now() - timedelta(hours=2)
        collected = await scheduler.run_data_collection(since)
        logger.info(f"Collected {collected} activities")
        
        # Run daily posting
        posting_results = await scheduler.run_daily_posting()
        
        # Log results
        for platform, result in posting_results.items():
            if result.get("success"):
                posted = result.get("posted_count", 0)
                total = result.get("total_activities", 0)
                logger.info(f"{platform}: Posted {posted}/{total} activities")
            else:
                logger.error(f"{platform}: Failed - {result.get('error', 'Unknown error')}")
        
        # Get and log stats
        stats = await scheduler.get_posting_stats(days=1)
        logger.info(f"Daily stats: {stats}")
        
        logger.info("Daily posting process completed successfully")
        
    except Exception as e:
        logger.error(f"Daily posting process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
