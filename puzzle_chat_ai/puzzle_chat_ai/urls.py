# puzzle_chat_ai/urls.py

from django.contrib import admin
from django.urls import path, include
from chat import views as chat_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 將網站首頁 (http://...) 指向我們的登入頁面
    path('', chat_views.login_view, name='login'), 

    # 將所有 /chat/ 開頭的 URL 請求，轉交給 chat app 的 urls.py 檔案
    path('chat/', include('chat.urls')),
]