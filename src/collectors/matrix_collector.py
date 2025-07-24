"""Matrix room activity collector."""

import asyncio
from datetime import datetime
from typing import List, Optional

from nio import AsyncClient, LoginResponse, MatrixRoom, RoomMessageText

from config.settings import settings
from src.storage import Activity, ActivityType

from .base import BaseCollector


class MatrixCollector(BaseCollector):
    """Collects activities from Matrix rooms."""

    def __init__(self) -> None:
        """Initialize the Matrix collector."""
        super().__init__(ActivityType.MATRIX_POST)
        # Construct user ID from username and homeserver
        homeserver_domain = settings.matrix_homeserver.split("://")[-1]
        self.user_id = f"@{settings.matrix_username}:{homeserver_domain}"
        self.client = AsyncClient(settings.matrix_homeserver, self.user_id)
        self._logged_in = False

    async def _ensure_logged_in(self) -> bool:
        """Ensure the client is logged in to Matrix.
        
        Returns:
            True if login successful, False otherwise
        """
        if self._logged_in:
            return True
            
        try:
            self.logger.info("Logging in to Matrix...")
            response = await self.client.login(settings.matrix_password)
            
            if isinstance(response, LoginResponse):
                self.logger.info(f"Successfully logged in as {response.user_id}")
                self._logged_in = True
                return True
            else:
                self.logger.error(f"Matrix login failed: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error logging in to Matrix: {e}")
            return False

    async def collect(self, since: Optional[datetime] = None) -> List[Activity]:
        """Collect Matrix room activities.
        
        Args:
            since: Only collect activities created after this datetime
            
        Returns:
            List of collected activities
        """
        activities = []
        
        try:
            # Ensure we're logged in
            if not await self._ensure_logged_in():
                self.logger.error("Failed to log in to Matrix")
                return activities
            
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
                            extra_data={
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
        if sender == self.user_id:
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
