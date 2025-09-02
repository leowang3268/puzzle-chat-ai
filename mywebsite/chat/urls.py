# chat/urls.py (簡化後)

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # 用於 AJAX 檢查使用者名稱
    path('check_username/', views.check_username_view, name='check_username'),

    # 處理聊天室頁面，例如 /chat/房間名稱/
    path('<str:room_name>/', views.chat_room_view, name='chat_room'),
]