"""
Constants for the chat application to replace magic strings and numbers.
"""

# WebSocket Message Types
MESSAGE_TYPES = {
    'CHAT_MESSAGE': 'chat_message',
    'AI_MESSAGE': 'ai_message',
    'TYPING': 'typing',
    'STOP_TYPING': 'stop_typing',
    'USER_JOINED': 'user_joined',
    'USER_LEFT': 'user_left',
    'LIKE_MESSAGE': 'like_message',
    'GAME_OVER': 'game_over',
    'SUGGESTION_RESPONSE': 'suggestion_response',
    'SHARED_MESSAGE': 'shared_message',
    'MARK_MESSAGES_READ': 'mark_messages_read',
}

# AI Models Configuration
AI_MODELS = {
    'PRIMARY': 'gpt-4o',
    'FALLBACK': 'gpt-3.5-turbo',
    'CREATIVE': 'gpt-4',
    'FAST': 'gpt-3.5-turbo',
}

# Temperature Settings for AI
AI_TEMPERATURES = {
    'CREATIVE': 0.7,
    'BALANCED': 0.5,
    'FOCUSED': 0.2,
    'PRECISE': 0.0,
}

# Default Values
DEFAULTS = {
    'ROOM_NAME': 'default_room',
    'AI_HISTORY_LIMIT': 10,
    'MAX_RETRIES': 3,
    'TIMEOUT_SECONDS': 30,
}

# AI Modes
AI_MODES = {
    'ASSISTANT': 'A',
    'CREATIVE': 'C',
    'ANALYTICAL': 'N',
}

# Suggestion Response Types
SUGGESTION_RESPONSES = {
    'SENT': 'sent',
    'DISMISSED': 'dismissed',
    'NO_ACTION': 'no_action',
}

# OpenAI API Configuration
OPENAI_CONFIG = {
    'BASE_URL': 'https://api.openai.com/v1/chat/completions',
    'MAX_TOKENS': 1000,
    'RESPONSE_FORMAT_JSON': {'type': 'json_object'},
}

# Fixed Puzzle Configuration
FIXED_PUZZLE = {
    "question": "一名男子在餐廳吃完午餐，服務生拿來了帳單。他開了一張金額相符的支票，但突然將支票翻過來，在背面寫了幾句話恭喜餐廳老闆。為什麼？",
    "answer": """這名男子是一位世界聞名的人。他發現了一個巧妙的支付方式：在支付帳單時，他會開一張支票，然後在支票的背面，寫下幾句話並附上他獨特的簽名。他知道，對於餐廳老闆來說，一張帶有他親筆簽名的支票，其收藏價值，遠遠超過了帳單上的金額。因此，老闆會很樂意地收下這張支票並將其收藏，而不會拿去兌現。這成了一種雙贏的交換。"""
}

# Cache Configuration
CACHE_CONFIG = {
    'AI_RESPONSE_TIMEOUT': 3600,  # 1 hour
    'USER_SESSION_TIMEOUT': 1800,  # 30 minutes
    'DEFAULT_TIMEOUT': 300,  # 5 minutes
}

# Error Messages
ERROR_MESSAGES = {
    'AI_API_FAILED': 'AI service temporarily unavailable',
    'INVALID_MESSAGE': 'Invalid message format',
    'DATABASE_ERROR': 'Database operation failed',
    'AUTHENTICATION_ERROR': 'User authentication failed',
    'RATE_LIMIT_EXCEEDED': 'Too many requests, please try again later',
}