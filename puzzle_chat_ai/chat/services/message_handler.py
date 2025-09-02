"""
WebSocket message handler for processing different message types.
"""

import json
import logging
from typing import Dict, Any, Optional

from ..constants import MESSAGE_TYPES, ERROR_MESSAGES, FIXED_PUZZLE
from .ai_service import ai_service
from .db_service import db_service

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles different types of WebSocket messages."""
    
    def __init__(self, consumer):
        self.consumer = consumer
        self.room_name = consumer.room_name
        self.user_name = consumer.user_name
        self.room_group_name = consumer.room_group_name
    
    async def handle_message(self, message_type: str, data: Dict[str, Any]) -> None:
        """Route message to appropriate handler based on type."""
        handlers = {
            MESSAGE_TYPES['CHAT_MESSAGE']: self._handle_chat_message,
            MESSAGE_TYPES['AI_MESSAGE']: self._handle_ai_message,
            MESSAGE_TYPES['LIKE_MESSAGE']: self._handle_like_message,
            MESSAGE_TYPES['SUGGESTION_RESPONSE']: self._handle_suggestion_response,
            MESSAGE_TYPES['TYPING']: self._handle_typing,
            MESSAGE_TYPES['STOP_TYPING']: self._handle_stop_typing,
        }
        
        handler = handlers.get(message_type)
        if handler:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error handling {message_type}: {e}")
                await self._send_error(ERROR_MESSAGES['INVALID_MESSAGE'])
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await self._send_error(ERROR_MESSAGES['INVALID_MESSAGE'])
    
    async def _handle_chat_message(self, data: Dict[str, Any]) -> None:
        """Handle regular chat messages."""
        message = data.get('message', '').strip()
        reply_text = data.get('replyText', '')
        reply_author = data.get('replyAuthor', '')
        
        if not message:
            await self._send_error("Message cannot be empty")
            return
        
        # Save to database
        chat_message = await db_service.create_chat_message(
            room_name=self.room_name,
            user_name=self.user_name,
            message=message,
            reply_message=reply_text,
            reply_author=reply_author
        )
        
        if chat_message:
            # Check if this might be a puzzle solution
            solution_check = await ai_service.check_puzzle_solution(
                message, FIXED_PUZZLE['answer']
            )
            
            # Broadcast to room
            await self.consumer.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'user_name': self.user_name,
                    'message': message,
                    'reply_text': reply_text,
                    'reply_author': reply_author,
                    'timestamp': chat_message.timestamp.isoformat(),
                    'message_id': chat_message.id,
                    'is_solution': solution_check.get('is_correct', False)
                }
            )
            
            # Handle game over if solution is correct
            if solution_check.get('is_correct', False):
                await self._handle_game_over(message)
        
        # Invalidate cache
        db_service.invalidate_room_cache(self.room_name)
    
    async def _handle_ai_message(self, data: Dict[str, Any]) -> None:
        """Handle AI interaction requests."""
        user_message = data.get('message', '').strip()
        mode = data.get('mode', 'A')
        
        if not user_message:
            await self._send_error("Message cannot be empty")
            return
        
        # Get AI response
        ai_response = await ai_service.get_puzzle_hint(user_message, self.room_name)
        
        if ai_response:
            # Save to database
            ai_message = await db_service.create_ai_message(
                room_name=self.room_name,
                user_name=self.user_name,
                message=user_message,
                ai_message=ai_response,
                mode=mode
            )
            
            if ai_message:
                # Send to user
                await self.consumer.send(text_data=json.dumps({
                    'type': MESSAGE_TYPES['AI_MESSAGE'],
                    'sender': self.user_name,
                    'ai_message': ai_response,
                    'user_message': user_message,
                    'timestamp': ai_message.timestamp.isoformat(),
                    'message_id': ai_message.id
                }))
                
                # Send to shared view for others
                await self.consumer.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'shared_message',
                        'sender': self.user_name,
                        'user_message': user_message,
                        'ai_reply_content': ai_response
                    }
                )
        else:
            await self._send_error(ERROR_MESSAGES['AI_API_FAILED'])
    
    async def _handle_like_message(self, data: Dict[str, Any]) -> None:
        """Handle message like/unlike actions."""
        message_id = data.get('messageId')
        
        if not message_id:
            await self._send_error("Message ID required")
            return
        
        result = await db_service.update_message_likes(
            message_id, self.user_name, 'toggle'
        )
        
        if result['success']:
            # Broadcast like update
            await self.consumer.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'like_update',
                    'message_id': message_id,
                    'liked_by': result['liked_by'],
                    'count': result['count']
                }
            )
        else:
            await self._send_error("Failed to update like")
    
    async def _handle_suggestion_response(self, data: Dict[str, Any]) -> None:
        """Handle AI suggestion responses."""
        message_id = data.get('messageId')
        response_type = data.get('responseType')
        
        if not message_id or not response_type:
            await self._send_error("Message ID and response type required")
            return
        
        success = await db_service.update_ai_suggestion_response(
            message_id, response_type
        )
        
        if not success:
            await self._send_error("Failed to update suggestion response")
    
    async def _handle_typing(self, data: Dict[str, Any]) -> None:
        """Handle typing indicator."""
        message = data.get('message', '')
        
        await self.consumer.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_name': self.user_name,
                'message': message
            }
        )
    
    async def _handle_stop_typing(self, data: Dict[str, Any]) -> None:
        """Handle stop typing indicator."""
        await self.consumer.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'stop_typing_indicator',
                'user_name': self.user_name
            }
        )
    
    async def _handle_game_over(self, winning_message: str) -> None:
        """Handle game over scenario."""
        await self.consumer.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_over',
                'winner': self.user_name,
                'final_answer': FIXED_PUZZLE['answer'],
                'winning_message': winning_message
            }
        )
    
    async def _send_error(self, error_message: str) -> None:
        """Send error message to client."""
        await self.consumer.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))