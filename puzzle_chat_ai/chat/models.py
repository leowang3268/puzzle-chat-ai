from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.timezone import now



class ChatMessage(models.Model):
    room_name = models.CharField(max_length=100, default="default_room") # 新增
    user_name = models.CharField(max_length=100)
    message = models.TextField()
    reply_message = models.TextField(default="")
    # ↓↓↓ 新增這一行來儲存被回覆訊息的作者 ↓↓↓
    reply_author = models.CharField(max_length=100, blank=True, null=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    liked_by = models.JSONField(default=list, blank=True)



class chatMessage_summary(models.Model):
    room_name = models.CharField(max_length=100, default="default_room") # 新增
    summary_idx=models.IntegerField(default=0)
    summary_message=models.TextField(default="")


class ai_ChatMessage(models.Model):
    room_name = models.CharField(max_length=255, default="default_room")
    user_name = models.CharField(max_length=100)
    message = models.TextField()
    ai_message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # ↓↓↓ 新增這兩個欄位以匹配 consumers.py 的邏輯 ↓↓↓
    mode = models.CharField(max_length=1, default='A')
    awareness_summary = models.CharField(max_length=255, blank=True, null=True)

    # ⭐ START: NEW FIELD TO TRACK SUGGESTION RESPONSE
    suggestion_response = models.CharField(
        max_length=10, 
        choices=[('sent', 'Sent'), ('dismissed', 'Dismissed'), ('no_action', 'No Action')],
        default='no_action',
        blank=True
    )
    # ⭐ END: NEW FIELD

class ai_ChatMessage_summary(models.Model):
    room_name = models.CharField(max_length=100, default="default_room") # 新增
    user_name = models.CharField(max_length=100)
    summary = models.TextField(default="")

    
    
class ChatUser(models.Model):
    user_name = models.CharField(max_length=100)


    def __str__(self):
        return self.user_name
    


    
