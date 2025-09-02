"""
Database service for optimized async database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from asgiref.sync import sync_to_async
from django.db import models
from django.core.cache import cache

from ..models import ChatMessage, ChatUser, AIChatMessage
from ..constants import CACHE_CONFIG, DEFAULTS

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for optimized database operations with caching."""
    
    @staticmethod
    async def create_chat_user(user_name: str) -> Optional['ChatUser']:
        """Create a new chat user asynchronously."""
        try:
            return await sync_to_async(ChatUser.objects.create)(user_name=user_name)
        except Exception as e:
            logger.error(f"Failed to create user {user_name}: {e}")
            return None
    
    @staticmethod
    async def create_chat_message(
        room_name: str,
        user_name: str,
        message: str,
        reply_message: str = "",
        reply_author: str = ""
    ) -> Optional['ChatMessage']:
        """Create a new chat message asynchronously."""
        try:
            return await sync_to_async(ChatMessage.objects.create)(
                room_name=room_name,
                user_name=user_name,
                message=message,
                reply_message=reply_message,
                reply_author=reply_author
            )
        except Exception as e:
            logger.error(f"Failed to create chat message: {e}")
            return None
    
    @staticmethod
    async def create_ai_message(
        room_name: str,
        user_name: str,
        message: str,
        ai_message: str,
        mode: str = 'A',
        awareness_summary: str = ""
    ) -> Optional['AIChatMessage']:
        """Create a new AI message asynchronously."""
        try:
            return await sync_to_async(AIChatMessage.objects.create)(
                room_name=room_name,
                user_name=user_name,
                message=message,
                ai_message=ai_message,
                mode=mode,
                awareness_summary=awareness_summary
            )
        except Exception as e:
            logger.error(f"Failed to create AI message: {e}")
            return None
    
    @staticmethod
    async def get_room_messages(
        room_name: str, 
        limit: int = 50,
        use_cache: bool = True
    ) -> List['ChatMessage']:
        """Get room messages with caching and optimization."""
        cache_key = f"room_messages:{room_name}:{limit}"
        
        if use_cache:
            cached_messages = cache.get(cache_key)
            if cached_messages:
                return cached_messages
        
        try:
            # Use select_related to avoid N+1 queries if there are foreign keys
            messages = await sync_to_async(list)(
                ChatMessage.objects.filter(room_name=room_name)
                .order_by('-timestamp')[:limit]
            )
            
            if use_cache:
                cache.set(cache_key, messages, CACHE_CONFIG['DEFAULT_TIMEOUT'])
            
            return messages
        except Exception as e:
            logger.error(f"Failed to get room messages: {e}")
            return []
    
    @staticmethod
    async def get_ai_messages(
        room_name: str,
        user_name: Optional[str] = None,
        limit: int = None
    ) -> List['AIChatMessage']:
        """Get AI messages with optimized querying."""
        try:
            queryset = AIChatMessage.objects.filter(room_name=room_name)
            
            if user_name:
                queryset = queryset.filter(user_name=user_name)
            
            if limit:
                queryset = queryset[:limit]
            
            return await sync_to_async(list)(
                queryset.order_by('-timestamp')
            )
        except Exception as e:
            logger.error(f"Failed to get AI messages: {e}")
            return []
    
    @staticmethod
    async def update_message_likes(
        message_id: int,
        user_name: str,
        action: str = 'toggle'
    ) -> Dict[str, Any]:
        """Update message likes optimistically."""
        try:
            message = await sync_to_async(ChatMessage.objects.get)(id=message_id)
            
            liked_by = message.liked_by or []
            
            if action == 'toggle':
                if user_name in liked_by:
                    liked_by.remove(user_name)
                else:
                    liked_by.append(user_name)
            elif action == 'add' and user_name not in liked_by:
                liked_by.append(user_name)
            elif action == 'remove' and user_name in liked_by:
                liked_by.remove(user_name)
            
            message.liked_by = liked_by
            await sync_to_async(message.save)(update_fields=['liked_by'])
            
            return {
                'success': True,
                'liked_by': liked_by,
                'count': len(liked_by)
            }
        except ChatMessage.DoesNotExist:
            logger.error(f"Message {message_id} not found")
            return {'success': False, 'error': 'Message not found'}
        except Exception as e:
            logger.error(f"Failed to update message likes: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    async def update_ai_suggestion_response(
        message_id: int,
        response_type: str
    ) -> bool:
        """Update AI suggestion response status."""
        try:
            message = await sync_to_async(AIChatMessage.objects.get)(id=message_id)
            message.suggestion_response = response_type
            await sync_to_async(message.save)(update_fields=['suggestion_response'])
            return True
        except AIChatMessage.DoesNotExist:
            logger.error(f"AI Message {message_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to update suggestion response: {e}")
            return False
    
    @staticmethod
    async def get_user_count(room_name: str) -> int:
        """Get active user count for a room (with caching)."""
        cache_key = f"user_count:{room_name}"
        count = cache.get(cache_key)
        
        if count is None:
            try:
                # This is a simplified count - in reality you'd track active connections
                count = await sync_to_async(
                    ChatUser.objects.filter(user_name__icontains=room_name).count
                )()
                cache.set(cache_key, count, CACHE_CONFIG['DEFAULT_TIMEOUT'])
            except Exception as e:
                logger.error(f"Failed to get user count: {e}")
                count = 0
        
        return count
    
    @staticmethod
    def invalidate_room_cache(room_name: str):
        """Invalidate all cache entries for a room."""
        cache_patterns = [
            f"room_messages:{room_name}:*",
            f"user_count:{room_name}",
        ]
        
        for pattern in cache_patterns:
            try:
                cache.delete(pattern)
            except Exception as e:
                logger.error(f"Failed to invalidate cache {pattern}: {e}")


# Global database service instance
db_service = DatabaseService()