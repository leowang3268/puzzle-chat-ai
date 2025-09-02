# chat/views.py (簡化後)

from django.shortcuts import render
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from .models import ChatUser

# 視圖：處理使用者登入頁面
def login_view(request):
    """
    這個視圖負責渲染使用者輸入「暱稱」和「房間號碼」的登入頁面 (login.html)。
    """
    return render(request, 'chat/login.html')

# 視圖：處理聊天室頁面
def chat_room_view(request, room_name):
    """
    這個視圖負責渲染特定房間的聊天室主頁面 (chat.html)。
    """
    return render(request, 'chat/chat.html', {
        'room_name': room_name,
    })

# 視圖：處理 AJAX 請求以檢查使用者名稱是否重複 (可選，但建議保留)
def check_username_view(request):
    user_name = request.GET.get('userName', '').strip()
    if not user_name:
        return JsonResponse({'valid': False, 'message': 'Username cannot be empty.'})
    if ChatUser.objects.filter(user_name=user_name).exists():
        return JsonResponse({'valid': False, 'message': 'The name has already been used. Please enter a different name.'})
    return JsonResponse({'valid': True})