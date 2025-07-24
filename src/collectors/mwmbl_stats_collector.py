"""Mwmbl stats API collector."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from src.storage import Activity, ActivityType

from .base import BaseCollector


class MwmblStatsCollector(BaseCollector):
    """Collects statistics from the Mwmbl stats API."""

    def __init__(self) -> None:
        """Initialize the Mwmbl stats collector."""
        super().__init__(ActivityType.MWMBL_STATS)

    async def collect(self, since: Optional[datetime] = None) -> List[Activity]:
        """Collect Mwmbl statistics.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            List of collected activities
        """
        activities = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.mwmbl_stats_url)
                response.raise_for_status()
                
                stats_data = response.json()
                
                # Create activities for different types of stats
                activities.extend(await self._process_dataset_stats(stats_data))
                activities.extend(await self._process_crawler_stats(stats_data))
                
        except Exception as e:
            self.logger.error(f"Error collecting Mwmbl stats: {e}")
            
        return activities

    async def _process_dataset_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process dataset statistics."""
        activities = []
        
        try:
            dataset_stats = stats_data.get("dataset", {})
            
            if dataset_stats:
                # Create a unique ID based on the current date for daily stats
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                # Check if we have significant dataset updates
                total_pages = dataset_stats.get("total_pages", 0)
                total_domains = dataset_stats.get("total_domains", 0)
                
                # Consider it newsworthy if we have substantial numbers
                is_newsworthy = total_pages > 1000 or total_domains > 100
                
                activity = self._create_activity(
                    source_id=f"dataset_stats_{current_date}",
                    title=f"Dataset Stats Update: {total_pages:,} pages, {total_domains:,} domains",
                    content=f"Current dataset contains {total_pages:,} pages from {total_domains:,} domains",
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    metadata={
                        "type": "dataset",
                        "total_pages": total_pages,
                        "total_domains": total_domains,
                        **dataset_stats,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing dataset stats: {e}")
            
        return activities

    async def _process_crawler_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process crawler statistics."""
        activities = []
        
        try:
            crawler_stats = stats_data.get("crawler", {})
            
            if crawler_stats:
                # Create a unique ID based on the current date for daily stats
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                # Extract key crawler metrics
                pages_crawled = crawler_stats.get("pages_crawled_today", 0)
                active_crawlers = crawler_stats.get("active_crawlers", 0)
                queue_size = crawler_stats.get("queue_size", 0)
                
                # Consider it newsworthy if there's significant crawling activity
                is_newsworthy = pages_crawled > 100 or active_crawlers > 0
                
                content_parts = []
                if pages_crawled > 0:
                    content_parts.append(f"{pages_crawled:,} pages crawled today")
                if active_crawlers > 0:
                    content_parts.append(f"{active_crawlers} active crawlers")
                if queue_size > 0:
                    content_parts.append(f"{queue_size:,} pages in queue")
                
                content = "Crawler activity: " + ", ".join(content_parts) if content_parts else "Crawler stats updated"
                
                activity = self._create_activity(
                    source_id=f"crawler_stats_{current_date}",
                    title=f"Crawler Stats: {pages_crawled:,} pages crawled",
                    content=content,
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    metadata={
                        "type": "crawler",
                        "pages_crawled_today": pages_crawled,
                        "active_crawlers": active_crawlers,
                        "queue_size": queue_size,
                        **crawler_stats,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing crawler stats: {e}")
            
        return activities

    async def _process_general_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process general statistics that don't fit other categories."""
        activities = []
        
        try:
            # Look for any other interesting stats
            for key, value in stats_data.items():
                if key not in ["dataset", "crawler"] and isinstance(value, dict):
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    
                    activity = self._create_activity(
                        source_id=f"general_stats_{key}_{current_date}",
                        title=f"Stats Update: {key.replace('_', ' ').title()}",
                        content=f"Updated statistics for {key}",
                        created_at=datetime.now(),
                        url=settings.mwmbl_stats_url,
                        metadata={
                            "type": "general",
                            "category": key,
                            **value,
                        },
                        is_newsworthy=False,  # General stats are usually not newsworthy
                    )
                    activities.append(activity)
                    
        except Exception as e:
            self.logger.error(f"Error processing general stats: {e}")
            
        return activities
