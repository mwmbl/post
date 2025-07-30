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
            async with httpx.AsyncClient(timeout=30.0) as client:
                self.logger.info(f"Fetching stats from {settings.mwmbl_stats_url}")
                response = await client.get(settings.mwmbl_stats_url)
                response.raise_for_status()
                
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response content length: {len(response.content)}")
                
                stats_data = response.json()
                self.logger.info(f"Successfully parsed JSON with {len(stats_data)} keys")
                
                # Process different types of stats from the actual API response
                activities.extend(await self._process_crawling_stats(stats_data))
                activities.extend(await self._process_user_stats(stats_data))
                activities.extend(await self._process_domain_stats(stats_data))
                activities.extend(await self._process_index_stats(stats_data))
                activities.extend(await self._process_query_stats(stats_data))
                
        except Exception as e:
            self.logger.error(f"Error collecting Mwmbl stats: {e}")
            
        return activities

    async def _process_crawling_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process crawling statistics."""
        activities = []
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            urls_crawled_today = stats_data.get("urls_crawled_today", 0)
            urls_crawled_hourly = stats_data.get("urls_crawled_hourly", [])
            
            if urls_crawled_today > 0:
                # Determine if this is newsworthy based on crawling volume
                is_newsworthy = urls_crawled_today > 100000  # 100K+ URLs is significant
                
                # Calculate hourly peak if available
                hourly_peak = max(urls_crawled_hourly) if urls_crawled_hourly else 0
                
                content_parts = [f"{urls_crawled_today:,} URLs crawled today"]
                if hourly_peak > 0:
                    content_parts.append(f"Peak hour: {hourly_peak:,} URLs")
                
                content = "Crawling activity: " + ", ".join(content_parts)
                
                activity = self._create_activity(
                    source_id=f"crawling_stats_{current_date}",
                    title=f"Daily Crawling: {urls_crawled_today:,} URLs",
                    content=content,
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    extra_data={
                        "type": "crawling",
                        "urls_crawled_today": urls_crawled_today,
                        "urls_crawled_hourly": urls_crawled_hourly,
                        "hourly_peak": hourly_peak,
                        "urls_crawled_daily": stats_data.get("urls_crawled_daily", {}),
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing crawling stats: {e}")
            
        return activities

    async def _process_user_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process user statistics."""
        activities = []
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            top_users = stats_data.get("top_users", [])
            users_crawled_daily = stats_data.get("users_crawled_daily", {})
            top_user_results = stats_data.get("top_user_results", [])
            
            # Get today's user count
            today_users = users_crawled_daily.get(current_date, 0)
            
            if top_users or today_users > 0:
                # Determine newsworthiness based on user activity
                is_newsworthy = today_users > 5 or (top_users and len(top_users) > 3)
                
                content_parts = []
                if today_users > 0:
                    content_parts.append(f"{today_users} active crawlers today")
                
                if top_users:
                    top_user_count = top_users[0][1] if top_users[0] else 0
                    content_parts.append(f"Top crawler: {top_user_count:,} URLs")
                
                content = "User activity: " + ", ".join(content_parts) if content_parts else "User stats updated"
                
                activity = self._create_activity(
                    source_id=f"user_stats_{current_date}",
                    title=f"Crawler Activity: {today_users} active users",
                    content=content,
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    extra_data={
                        "type": "users",
                        "users_today": today_users,
                        "top_users": top_users[:10],  # Top 10 users
                        "top_user_results": top_user_results[:10],  # Top 10 by results
                        "users_crawled_daily": users_crawled_daily,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing user stats: {e}")
            
        return activities

    async def _process_domain_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process domain statistics."""
        activities = []
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            top_domains = stats_data.get("top_domains", [])
            
            if top_domains:
                # Get top domain info
                top_domain_name = top_domains[0][0] if top_domains[0] else "Unknown"
                top_domain_count = top_domains[0][1] if top_domains[0] else 0
                
                # Consider newsworthy if we have significant domain diversity
                is_newsworthy = len(top_domains) > 50 and top_domain_count > 1000
                
                content = f"Top crawled domains: {top_domain_name} leads with {top_domain_count:,} URLs"
                if len(top_domains) > 1:
                    content += f", followed by {top_domains[1][0]} ({top_domains[1][1]:,} URLs)"
                
                activity = self._create_activity(
                    source_id=f"domain_stats_{current_date}",
                    title=f"Domain Stats: {len(top_domains)} domains crawled",
                    content=content,
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    extra_data={
                        "type": "domains",
                        "top_domains": top_domains[:20],  # Top 20 domains
                        "total_domains": len(top_domains),
                        "top_domain_name": top_domain_name,
                        "top_domain_count": top_domain_count,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing domain stats: {e}")
            
        return activities

    async def _process_index_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process index statistics."""
        activities = []
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            urls_in_index_daily = stats_data.get("urls_in_index_daily", {})
            domains_in_index_daily = stats_data.get("domains_in_index_daily", {})
            results_in_index_daily = stats_data.get("results_in_index_daily", {})
            results_indexed_daily = stats_data.get("results_indexed_daily", {})
            
            # Get today's index stats
            urls_today = urls_in_index_daily.get(current_date, 0)
            domains_today = domains_in_index_daily.get(current_date, 0)
            results_today = results_in_index_daily.get(current_date, 0)
            indexed_today = results_indexed_daily.get(current_date, 0)
            
            if urls_today > 0 or results_today > 0:
                # Consider newsworthy if index has substantial content
                is_newsworthy = urls_today > 100000000 or indexed_today > 10000  # 100M+ URLs or 10K+ new results
                
                content_parts = []
                if urls_today > 0:
                    content_parts.append(f"{urls_today:,} URLs in index")
                if domains_today > 0:
                    content_parts.append(f"{domains_today:,} domains")
                if indexed_today > 0:
                    content_parts.append(f"{indexed_today:,} new results indexed today")
                
                content = "Index status: " + ", ".join(content_parts) if content_parts else "Index stats updated"
                
                activity = self._create_activity(
                    source_id=f"index_stats_{current_date}",
                    title=f"Index Stats: {urls_today:,} URLs indexed",
                    content=content,
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    extra_data={
                        "type": "index",
                        "urls_in_index": urls_today,
                        "domains_in_index": domains_today,
                        "results_in_index": results_today,
                        "results_indexed_today": indexed_today,
                        "urls_in_index_daily": urls_in_index_daily,
                        "domains_in_index_daily": domains_in_index_daily,
                        "results_in_index_daily": results_in_index_daily,
                        "results_indexed_daily": results_indexed_daily,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing index stats: {e}")
            
        return activities

    async def _process_query_stats(self, stats_data: Dict[str, Any]) -> List[Activity]:
        """Process query statistics."""
        activities = []
        
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            dataset_queries_daily = stats_data.get("dataset_queries_daily", {})
            dataset_results_daily = stats_data.get("dataset_results_daily", {})
            
            # Get today's query stats
            queries_today = dataset_queries_daily.get(current_date, 0)
            results_today = dataset_results_daily.get(current_date, 0)
            
            if queries_today > 0 or results_today > 0:
                # Consider newsworthy if there's significant query activity
                is_newsworthy = queries_today > 50000  # 50K+ queries is significant
                
                content_parts = []
                if queries_today > 0:
                    content_parts.append(f"{queries_today:,} dataset queries today")
                if results_today > 0:
                    content_parts.append(f"{results_today:,} results returned")
                
                content = "Query activity: " + ", ".join(content_parts) if content_parts else "Query stats updated"
                
                activity = self._create_activity(
                    source_id=f"query_stats_{current_date}",
                    title=f"Query Stats: {queries_today:,} searches today",
                    content=content,
                    created_at=datetime.now(),
                    url=settings.mwmbl_stats_url,
                    extra_data={
                        "type": "queries",
                        "queries_today": queries_today,
                        "results_today": results_today,
                        "dataset_queries_daily": dataset_queries_daily,
                        "dataset_results_daily": dataset_results_daily,
                    },
                    is_newsworthy=is_newsworthy,
                )
                activities.append(activity)
                
        except Exception as e:
            self.logger.error(f"Error processing query stats: {e}")
            
        return activities
