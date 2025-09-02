"""
AI Service for handling OpenAI API interactions with caching and error handling.
"""

import json
import logging
import hashlib
from typing import Dict, List, Optional, Any
import aiohttp
from django.core.cache import cache
from django.conf import settings
from asgiref.sync import sync_to_async

from ..constants import (
    AI_MODELS, AI_TEMPERATURES, OPENAI_CONFIG, 
    CACHE_CONFIG, ERROR_MESSAGES, DEFAULTS
)
from ..models import AIChatMessage

logger = logging.getLogger(__name__)


class AIService:
    """Service for handling AI interactions with caching and error handling."""
    
    def __init__(self):
        self.api_url = OPENAI_CONFIG['BASE_URL']
        self.max_retries = DEFAULTS['MAX_RETRIES']
        self.timeout = DEFAULTS['TIMEOUT_SECONDS']
    
    def _generate_cache_key(self, messages: List[Dict], model: str, temperature: float) -> str:
        """Generate a cache key for AI responses."""
        content = json.dumps({
            'messages': messages,
            'model': model,
            'temperature': temperature
        }, sort_keys=True)
        return f"ai_response:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _make_api_request(self, data: Dict[str, Any]) -> Optional[str]:
        """Make API request to OpenAI with proper error handling."""
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.api_url, 
                    json=data, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"OpenAI API request failed: {e}")
                return None
    
    async def get_ai_response(
        self, 
        messages: List[Dict], 
        model: str = AI_MODELS['PRIMARY'],
        temperature: float = AI_TEMPERATURES['BALANCED'],
        use_cache: bool = True,
        response_format: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get AI response with caching and fallback model support.
        
        Args:
            messages: List of message dictionaries
            model: AI model to use
            temperature: Response creativity (0.0-1.0)
            use_cache: Whether to use caching
            response_format: Optional response format specification
            
        Returns:
            AI response string or None if failed
        """
        # Check cache first
        if use_cache:
            cache_key = self._generate_cache_key(messages, model, temperature)
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.info("AI response served from cache")
                return cached_response
        
        # Prepare API request data
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": OPENAI_CONFIG['MAX_TOKENS']
        }
        
        if response_format:
            data["response_format"] = response_format
        
        # Try primary model
        response = await self._make_api_request(data)
        
        # Fallback to secondary model if primary fails
        if response is None and model != AI_MODELS['FALLBACK']:
            logger.warning(f"Primary model {model} failed, trying fallback")
            data["model"] = AI_MODELS['FALLBACK']
            response = await self._make_api_request(data)
        
        # Cache successful response
        if response and use_cache:
            cache.set(cache_key, response, CACHE_CONFIG['AI_RESPONSE_TIMEOUT'])
            logger.info("AI response cached")
        
        return response
    
    async def get_puzzle_hint(self, user_message: str, room_name: str) -> Optional[str]:
        """Get a puzzle hint based on user message and context."""
        context_messages = await self._get_room_context(room_name)
        
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant for a puzzle game. Provide hints without giving away the answer."},
            *context_messages,
            {"role": "user", "content": user_message}
        ]
        
        return await self.get_ai_response(
            messages, 
            temperature=AI_TEMPERATURES['CREATIVE']
        )
    
    async def get_conversation_summary(self, room_name: str, user_name: str) -> Optional[str]:
        """Generate a conversation summary for awareness."""
        messages = await self._get_recent_ai_messages(room_name, user_name)
        
        if not messages:
            return None
        
        summary_prompt = [
            {"role": "system", "content": "Summarize the conversation briefly in 1-2 sentences."},
            {"role": "user", "content": f"Summarize these messages: {messages}"}
        ]
        
        return await self.get_ai_response(
            summary_prompt,
            temperature=AI_TEMPERATURES['FOCUSED']
        )
    
    async def check_puzzle_solution(self, user_message: str, puzzle_answer: str) -> Dict[str, Any]:
        """Check if user message contains the puzzle solution."""
        messages = [
            {
                "role": "system", 
                "content": f"""You are judging if a user's answer matches the puzzle solution.
                Puzzle answer: {puzzle_answer}
                
                Respond with JSON: {{"is_correct": true/false, "explanation": "brief explanation"}}"""
            },
            {"role": "user", "content": user_message}
        ]
        
        response = await self.get_ai_response(
            messages,
            temperature=AI_TEMPERATURES['PRECISE'],
            response_format=OPENAI_CONFIG['RESPONSE_FORMAT_JSON']
        )
        
        try:
            return json.loads(response) if response else {"is_correct": False, "explanation": "Analysis failed"}
        except json.JSONDecodeError:
            return {"is_correct": False, "explanation": "Invalid response format"}
    
    async def _get_room_context(self, room_name: str, limit: int = 5) -> List[Dict]:
        """Get recent room context for AI."""
        # This would be implemented to get recent messages from the room
        # Placeholder implementation
        return []
    
    async def _get_recent_ai_messages(self, room_name: str, user_name: str) -> List[str]:
        """Get recent AI messages for summary."""
        try:
            messages = await sync_to_async(list)(
                AIChatMessage.objects.filter(
                    room_name=room_name, 
                    user_name=user_name
                ).order_by('-timestamp')[:DEFAULTS['AI_HISTORY_LIMIT']]
            )
            return [msg.ai_message for msg in messages]
        except Exception as e:
            logger.error(f"Failed to get AI messages: {e}")
            return []


# Global AI service instance
ai_service = AIService()