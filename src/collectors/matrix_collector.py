"""Matrix room activity collector."""

import asyncio
from datetime import datetime
from typing import List, Optional

from nio import AsyncClient, MatrixRoom, RoomMessageText

from config.settings import settings
from src.storage import Activity, ActivityType

from .base import BaseCollector


class MatrixCollector(BaseCollector):
    """Collects activities from Matrix rooms."""

    def __init__(self) -> None:
        """Initialize the Matrix collector."""
        super().__init__(ActivityType.MATRIX_POST)
        self.client = AsyncClient(settings.matrix_homeserver, settings.matrix_user_id)
        self.client.access_token = settings.matrix_access_token

    async def collect(self, since: Optional[datetime] = None) -> List[Activity]:
        """Collect Matrix room activities.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            List of collected activities
        """
        activities = []
        
        try:
            # Join the room if not already joined
            await self.client.join(settings.matrix_room_id)
            
            # Get room messages
            room = self.client.rooms.get(settings.matrix_room_id)
            if not room:
                self.logger.error(f"Could not find room {settings.matrix_room_id}")
                return activities
            
            # Sync to get recent messages
            await self.client.sync(timeout=30000)
            
            # Get room timeline
            response = await self.client.room_messages(
                room_id=settings.matrix_room_id,
                start="",
                limit=100,
                direction="b"  # backwards from most recent
            )
            
            if hasattr(response, 'chunk'):
                for event in response.chunk:
                    if hasattr(event, 'server_timestamp') and hasattr(event, 'body'):
                        event_time = datetime.fromtimestamp(event.server_timestamp / 1000)
                        
                        if since and event_time < since:
                            continue
                        
                        # Determine if this message is newsworthy
                        is_newsworthy = self._is_newsworthy_message(event.body, event.sender)
                        
                        activity = self._create_activity(
                            source_id=f"matrix_{event.event_id}",
                            title=f"Matrix message from {event.sender}",
                            content=event.body,
                            created_at=event_time,
                            url=f"https://matrix.to/#/{settings.matrix_room_id}/{event.event_id}",
                            author=event.sender,
                            metadata={
                                "room_id": settings.matrix_room_id,
                                "event_id": event.event_id,
                                "event_type": event.type,
                            },
                            is_newsworthy=is_newsworthy,
                        )
                        activities.append(activity)
            
        except Exception as e:
            self.logger.error(f"Error collecting Matrix messages: {e}")
        finally:
            await self.client.close()
            
        return activities

    def _is_newsworthy_message(self, content: str, sender: str) -> bool:
        """Determine if a Matrix message is newsworthy.
        
        Args:
            content: Message content
            sender: Message sender
            
        Returns:
            True if the message is considered newsworthy
        """
        content_lower = content.lower()
        
        # Messages from the configured user are always newsworthy
        if sender == settings.matrix_user_id:
            return True
        
        # Messages about new members, releases, or important updates
        newsworthy_keywords = [
            "new member",
            "welcome",
            "release",
            "update",
            "announcement",
            "important",
            "breaking",
            "feature",
            "bug fix",
            "milestone",
            "version",
            "launch",
            "deployed",
        ]
        
        return any(keyword in content_lower for keyword in newsworthy_keywords)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()
