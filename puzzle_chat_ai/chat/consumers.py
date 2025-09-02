"""
Refactored ChatConsumer with separation of concerns and improved architecture.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

from .constants import MESSAGE_TYPES, DEFAULTS, ERROR_MESSAGES
from .services.message_handler import MessageHandler
from .services.db_service import db_service

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Refactored WebSocket consumer with single responsibility principle.
    Delegates message handling to specialized services.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        try:
            await self._parse_connection_params()
            await self._join_room()
            await self._create_user()
            await self.accept()
            logger.info(f"User {self.user_name} connected to room {self.room_name}")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"User {self.user_name} disconnected from room {self.room_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if not message_type:
                await self._send_error(ERROR_MESSAGES['INVALID_MESSAGE'])
                return
            
            # Delegate to message handler
            handler = MessageHandler(self)
            await handler.handle_message(message_type, data)
            
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self._send_error(ERROR_MESSAGES['INVALID_MESSAGE'])
    
    # WebSocket event handlers (called by channel layer)
    
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': MESSAGE_TYPES['CHAT_MESSAGE'],
            **event
        }))
    
    async def ai_message(self, event):
        """Send AI message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': MESSAGE_TYPES['AI_MESSAGE'],
            **event
        }))
    
    async def shared_message(self, event):
        """Send shared message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': MESSAGE_TYPES['SHARED_MESSAGE'],
            **event
        }))
    
    async def like_update(self, event):
        """Send like update to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': MESSAGE_TYPES['LIKE_MESSAGE'],
            **event
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send typing indicator to the sender
        if event.get('user_name') != self.user_name:
            await self.send(text_data=json.dumps({
                'type': MESSAGE_TYPES['TYPING'],
                **event
            }))
    
    async def stop_typing_indicator(self, event):
        """Send stop typing indicator to WebSocket."""
        if event.get('user_name') != self.user_name:
            await self.send(text_data=json.dumps({
                'type': MESSAGE_TYPES['STOP_TYPING'],
                **event
            }))
    
    async def game_over(self, event):
        """Send game over notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': MESSAGE_TYPES['GAME_OVER'],
            **event
        }))
    
    async def mark_messages_read(self, event):
        """Send mark messages read notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': MESSAGE_TYPES['MARK_MESSAGES_READ'],
            **event
        }))
    
    # Private helper methods
    
    async def _parse_connection_params(self):
        """Parse connection parameters from query string."""
        query_string = self.scope['query_string'].decode()
        if not query_string:
            raise ValueError("Missing connection parameters")
        
        params = {}
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        self.user_name = params.get('userName')
        self.room_name = params.get('roomName', DEFAULTS['ROOM_NAME'])
        self.room_group_name = f'chat_{self.room_name}'
        
        if not self.user_name:
            raise ValueError("Username is required")
    
    async def _join_room(self):
        """Join the room group."""
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
    
    async def _create_user(self):
        """Create user in database."""
        if self.user_name:
            await db_service.create_chat_user(self.user_name)
    
    async def _send_error(self, error_message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))