# consumers.py

import json
import aiohttp
import asyncio
import re
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.conf import settings
from .models import ChatMessage, ChatUser, AIChatMessage

logger = logging.getLogger(__name__)

# --- UNCHANGED CODE (FIXED_PUZZLE, ChatConsumer class definition) ---
# 使用固定的海龜湯題目
FIXED_PUZZLE = {
    "question": "一名男子在餐廳吃完午餐，服務生拿來了帳單。他開了一張金額相符的支票，但突然將支票翻過來，在背面寫了幾句話恭喜餐廳老闆。為什麼？",
    "answer": """這名男子是一位世界聞名的人。他發現了一個巧妙的支付方式：在支付帳單時，他會開一張支票，然後在支票的背面，寫下幾句話並附上他獨特的簽名。他知道，對於餐廳老闆來說，一張帶有他親筆簽名的支票，其收藏價值，遠遠超過了帳單上的金額。因此，老闆會很樂意地收下這張支票並將其收藏，而不會拿去兌現。這成了一種雙贏的交換。"""
}

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        params = dict(param.split('=') for param in query_string.split('&'))
        
        self.user_name = params.get('userName')
        self.room_name = params.get('roomName', 'default_room')
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        if self.user_name:
            await sync_to_async(ChatUser.objects.create)(user_name=self.user_name)
        
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

# ⭐ MODIFIED START: Added a centralized helper function for API calls with fallback.
    async def call_openai_with_fallback(self, messages, primary_model, fallback_model, temperature, response_format=None):
        api_url = "https://api.openai.com/v1/chat/completions"
        api_key = settings.OPENAI_API_KEY
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        models_to_try = [primary_model, fallback_model]
        
        for model in models_to_try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format:
                data["response_format"] = response_format

            try:
                timeout = aiohttp.ClientTimeout(total=20)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(api_url, headers=headers, json=data) as resp:
                        if resp.status == 200:
                            # If successful, return the JSON response
                            return await resp.json()
                        else:
                            # If status is not 200, log it and try the next model
                            logger.warning(f"API call with model {model} failed with status {resp.status}: {await resp.text()}")
                            continue # Go to the next model in the loop
            except asyncio.TimeoutError:
                logger.warning(f"API call with model {model} timed out.")
                continue # Go to the next model in the loop
            except Exception as e:
                logger.error(f"An unexpected error occurred with model {model}: {e}")
                continue # Go to the next model in the loop
                
        # If all models fail, return None
        return None

    # Condition A: 生成「基線」建議
    async def get_baseline_suggestion(self, puzzle_main_question, user_question, ai_answer, chat_history, current_user_name):
        api_url = "https://api.openai.com/v1/chat/completions"
        api_key = settings.OPENAI_API_KEY
        # print api key
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        system_prompt = f"""
你是我的「海龜湯」遊戲搭檔。你的目標是根據我的問答和聊天紀錄，為我（使用者名稱：{current_user_name}）草擬一段給夥伴的訊息。
這段訊息必須以『我』的口吻，包含兩部分：
1. **口語化總結**：用我的語氣，總結我剛才的發現。
2. **提出通用的互動問題**：在結尾加上一句「關於這點你有什麼想法嗎？」

**重要**：直接輸出訊息，不要有任何前綴。
---海龜湯總問題：{puzzle_main_question}---
"""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"# 聊天紀錄:\n{chat_history}\n\n# 我剛才的行動:\n- 我的問題: \"{user_question}\"\n- 裁判的回答: \"{ai_answer}\"\n\n# 請幫我（{current_user_name}）草擬訊息："}]
        # data = {"model": "gpt-4o", "messages": messages, "temperature": 0.2}
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(api_url, headers=headers, json=data) as resp:
        #         if resp.status == 200:
        #             response_json = await resp.json()
        #             content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '我剛才確認到一個線索。關於這點你有什麼想法嗎？')
        #             return content.strip().strip('"')
        #         else: return "我剛才確認到一個線索。關於這點你有什麼想法嗎？"
        response_json = await self.call_openai_with_fallback(messages, "gpt-4.1", "gpt-4-turbo", 0.2)
        
        if response_json:
            content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '我剛才確認到一個線索。關於這點你有什麼想法嗎？')
            return content.strip().strip('"')
        else:
            return "AI建議服務暫時不可用，請稍後再試。"

    # Condition B: 生成「過程導向」建議 (闡述假說)
    async def get_process_oriented_suggestion(self, puzzle_main_question, user_question, ai_answer, chat_history, current_user_name):
        api_url = "https://api.openai.com/v1/chat/completions"
        api_key = settings.OPENAI_API_KEY
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        system_prompt = f"""
# 在接下來的聊天紀錄中，「Me」代表我本人，「Partner」代表我的夥伴。聊天紀錄:\n{chat_history}\n\n

你是我的「海龜湯」遊戲搭檔，也是一位邏輯清晰的思考者。你的任務是，在我問完裁判後，根據聊天紀錄，幫我（使用者名稱：{current_user_name}）草擬一段訊息，讓他了解我的思考過程。

**結構模板 (必須遵守):**
1.  **口語化總結**：用口語化的方式，清晰地總結我剛從裁判那裡得到的「發現」。


**嚴格禁止**：
-   搞錯「我」和「夥伴」的角色。
-   提供任何新的解謎方向或下一步建議。
-   你的輸出只能是這段要傳給夥伴的訊息，不要包含任何其他前綴或解釋。

---海龜湯總問題：{puzzle_main_question}---
"""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"# 我剛才的行動:\n- 我的問題: \"{user_question}\"\n- 裁判的回答: \"{ai_answer}\"\n\n# 請幫我（{current_user_name}）草擬訊息："}]
        # data = {"model": "gpt-4.1", "messages": messages, "temperature": 0.7}
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(api_url, headers=headers, json=data) as resp:
        #         if resp.status == 200:
        #             response_json = await resp.json()
        #             content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '我剛才確認到一個線索，我們可以一起討論。')
        #             return content.strip().strip('"')
        #         else: return "我剛才確認到一個線索，我們可以一起討論。"
        response_json = await self.call_openai_with_fallback(messages, "gpt-4.1", "gpt-4-turbo", 0.7)
        
        if response_json:
            content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '我剛才確認到一個線索，我們可以一起討論。')
            return content.strip().strip('"')
        else:
            return "AI建議服務暫時不可用，請稍後再試。"

    # Condition C: 生成「高凝聚力序列」建議
    async def get_cohesive_sequence_suggestion(self, puzzle_main_question, user_question, ai_answer, chat_history, current_user_name):
        api_url = "https://api.openai.com/v1/chat/completions"
        api_key = settings.OPENAI_API_KEY

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        system_prompt = f"""
# 在接下來的聊天紀錄中，「Me」代表我本人，「Partner」代表我的夥伴。聊天紀錄:\n{chat_history}\n\n

你是我的「海龜湯」遊戲搭檔，也是一位頂尖的團隊溝通教練。你會根據我們的聊天紀錄和我剛才的行動，為我（使用者名稱：{current_user_name}）生成一句能「開啟高凝聚力溝通序列」的建議。

**你的行為準則:**
-   高凝聚力序列：道歉→鼓勵, 回答→提問
-   你會仔細閱讀聊天紀錄，判斷哪則訊息是哪個使用者說的，以便做出精準的反應，例如肯定夥伴之前提出的觀點，或承認我的想法錯誤。

---
**核心反應原則 (以『我』的視角)：**
**0.  **口語化總結**：用口語化的方式，清晰地總結我剛從裁判那裡得到的「發現」。

**1. 當我得到「與此無關」的答案時 (處於逆境):**
   - **你的目標：** 開啟「道歉→鼓勵」的序列。
   - **反應策略：** 草擬一個簡短的「道歉」（承認自己想錯了），並把問題拋給夥伴，創造讓他「鼓勵」我的機會。**如果夥伴之前提過不同方向，你必須藉機肯定他。**

**2. 當我得到其他的答案時 (得到一個需要處理的『回答』):**
   - **你的目標：** 開啟「回答→提問」的序列。
   - **反應策略：** 草擬一句話，先簡述裁判的「回答」，然後立刻基於這個回答和「聊天紀錄」，向夥伴提出一個能將討論推進下去的建設性「提問」。**如果這個答案驗證了夥伴的猜測，你必須歸功於他。**
---

   - **注意：** 這個提問必須是開放式的，讓夥伴有空間去思考和回應，而不是簡單的「是」或「否」。

**嚴格禁止**：
-   搞錯「我」和「夥伴」的角色。
-   提供任何新的解謎方向或下一步建議。
-   你的輸出只能是這段要傳給夥伴的訊息，不要包含任何其他前綴或解釋。

請根據聊天紀錄和我提供的「我的問題」和「裁判的回答」，遵循上述原則，先簡述我問了AI什麼問題，以及AI的答覆，再為「我」生成一句最適當的、能開啟高凝聚力溝通序列的訊息。請直接輸出那句話。

---海龜湯總問題：{puzzle_main_question}---
"""
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"# 我剛才的行動:\n- 我的問題: \"{user_question}\"\n- 裁判的回答: \"{ai_answer}\"\n\n# 請幫我（{current_user_name}）草擬訊息："}]
        # data = {"model": "gpt-4.1", "messages": messages, "temperature": 0.7}
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(api_url, headers=headers, json=data) as resp:
        #         if resp.status == 200:
        #             response_json = await resp.json()
        #             content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '我剛才確認到一個線索，我們可以一起討論。')
        #             return content.strip().strip('"')
        #         else: return "我剛才確認到一個線索，我們可以一起討論。"
        response_json = await self.call_openai_with_fallback(messages, "gpt-4.1", "gpt-4-turbo", 0.7)

        if response_json:
            content = response_json.get('choices', [{}])[0].get('message', {}).get('content', '我剛才確認到一個線索，我們可以一起討論。')
            return content.strip().strip('"')
        else:
            return "AI建議服務暫時不可用，請稍後再試。"

    @sync_to_async
    def update_suggestion_response(self, message_id, response_action):
        try:
            message = AIChatMessage.objects.get(id=message_id)
            message.suggestion_response = response_action
            message.save()
        except AIChatMessage.DoesNotExist:
            logger.warning(f"Could not find AIChatMessage with id {message_id} to update suggestion response.")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')

        if message_type == 'user_connect':
            messages = await sync_to_async(list)(ChatMessage.objects.filter(room_name=self.room_name).order_by('timestamp'))
            ai_messages = await sync_to_async(list)(AIChatMessage.objects.filter(room_name=self.room_name).order_by('timestamp'))
            for message in messages:
                await self.send(text_data=json.dumps({'type': 'chat', 'userName': message.user_name, 'message': message.message, 'replyText': message.reply_message, 'replyAuthor': message.reply_author, 'liked_by': message.liked_by, 'timestamp': message.timestamp.isoformat()}))
            for message in ai_messages:
                await self.send(text_data=json.dumps({'type': 'load_ai_chat', 'userName': message.user_name, 'user_message': message.message, 'ai_reply_content': message.ai_message, 'awareness_summary': message.awareness_summary or "", 'send_in_mode_c': ''}))
            await self.send(text_data=json.dumps({'type': 'game_info', 'puzzle_question': FIXED_PUZZLE['question']}))
            
        elif message_type == 'chat':
            chat_message = await sync_to_async(ChatMessage.objects.create)(room_name=self.room_name, user_name=text_data_json['userName'], message=text_data_json['message'], reply_message=text_data_json['replyText'], reply_author=text_data_json.get('replyAuthor', ''))
            await self.channel_layer.group_send(self.room_group_name, {'type': 'chat_message', 'message': chat_message.message, 'userName': chat_message.user_name, 'replyText': chat_message.reply_message, 'replyAuthor': chat_message.reply_author, 'liked_by': chat_message.liked_by, 'timestamp': chat_message.timestamp.isoformat()})
            
        elif message_type == 'ai_chat':
            user_name = text_data_json['userName']
            user_question = text_data_json['ai_message']
            mode = text_data_json.get('mode', 'A')

            ai_chat_history = await self.get_recent_ai_chat_history(user_name)
            evaluation_result = await self.evaluate_user_guess(FIXED_PUZZLE["question"], user_question, FIXED_PUZZLE["answer"], ai_chat_history)
            
            evaluation = evaluation_result.get("evaluation")
            ai_answer = evaluation_result.get("answer", "與此無關")

            awareness_summary = ""
            human_chat_history = await self.get_recent_human_chat_history(current_user_name=user_name)

            # ⭐ DEBUG: Printing the fetched chat history to the console.
            print(f"--- Debug: Chat History for User '{user_name}' ---")
            print(human_chat_history)
            print("-------------------------------------------------")
            
            if mode == 'A': # 基線條件
                awareness_summary = await self.get_baseline_suggestion(FIXED_PUZZLE["question"], user_question, ai_answer, human_chat_history, user_name)
            elif mode == 'B': # 過程導向的實驗條件
                awareness_summary = await self.get_process_oriented_suggestion(FIXED_PUZZLE["question"], user_question, ai_answer, human_chat_history, user_name)
            elif mode == 'C': # 高凝聚力序列的實驗條件
                awareness_summary = await self.get_cohesive_sequence_suggestion(FIXED_PUZZLE["question"], user_question, ai_answer, human_chat_history, user_name)
            
            ai_chat_message = await sync_to_async(AIChatMessage.objects.create)(
                room_name=self.room_name, 
                user_name=user_name, 
                message=user_question, 
                ai_message=ai_answer, 
                mode=mode, 
                awareness_summary=awareness_summary
            )

            if evaluation == "solved":
                await self.channel_layer.group_send(self.room_group_name, {'type': 'game_over', 'winner': user_name, 'final_answer': FIXED_PUZZLE["answer"]})
            else:
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'ai_chat_broadcast',
                    'payload': {
                        'type': 'ai_chat',
                        'userName': user_name,
                        'ai_reply_content': ai_answer,
                        'user_message': user_question,
                        'mode': mode
                    }
                })
                
                # 所有條件都會跳出建議
                if (mode == 'A' or mode == 'B' or mode == 'C') and awareness_summary:
                    await self.send(text_data=json.dumps({
                        'type': 'display_suggestion',
                        'suggestion': awareness_summary,
                        'ai_message_id': ai_chat_message.id
                    }))

        elif message_type == 'suggestion_sent':
            ai_message_id = text_data_json.get('ai_message_id')
            if ai_message_id:
                await self.update_suggestion_response(ai_message_id, 'sent')
        
        elif message_type == 'suggestion_dismissed':
            ai_message_id = text_data_json.get('ai_message_id')
            if ai_message_id:
                await self.update_suggestion_response(ai_message_id, 'dismissed')

        elif message_type == 'thumb_press':
            user_name = text_data_json['userName']
            message_index = int(text_data_json['index'])
            messages_in_room = await sync_to_async(list)(ChatMessage.objects.filter(room_name=self.room_name).order_by('timestamp'))
            if 0 <= message_index < len(messages_in_room):
                message = messages_in_room[message_index]
                if user_name in message.liked_by: message.liked_by.remove(user_name)
                else: message.liked_by.append(user_name)
                await sync_to_async(message.save)()
                await self.channel_layer.group_send(self.room_group_name, {'type': 'update_thumb_count', 'message_index': message_index, 'thumb_count': len(message.liked_by), 'likers': message.liked_by})
        
        elif message_type == 'typing':
            await self.channel_layer.group_send(self.room_group_name, {'type': 'notify_typing', 'typing_user': text_data_json['userName'], 'typing_message': text_data_json['typing_message']})
        
        elif message_type == 'stop_typing':
            await self.channel_layer.group_send(self.room_group_name, {'type': 'stop_typing', 'typing_user': text_data_json['userName']})

        elif message_type == 'mark_all_read':
            await self.channel_layer.group_send(self.room_group_name, {'type': 'notify_have_read', 'chatWith': text_data_json['userName']})

    # --- UNCHANGED CODE for remaining functions ---
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'userName': event['userName'],
            'replyText': event['replyText'],
            'replyAuthor': event['replyAuthor'],
            'liked_by': event['liked_by'],
            'timestamp': event['timestamp']
        }))
            
    async def ai_chat_broadcast(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    async def update_thumb_count(self, event):
        await self.send(text_data=json.dumps(event))

    async def notify_typing(self, event):
        if self.user_name != event['typing_user']:
            await self.send(text_data=json.dumps(event))

    async def stop_typing(self, event):
        if self.user_name != event['typing_user']:
            await self.send(text_data=json.dumps(event))

    async def notify_have_read(self, event):
        if self.user_name != event['chatWith']:
            await self.send(text_data=json.dumps(event))

    async def game_over(self, event):
        await self.send(text_data=json.dumps(event))
    
    @sync_to_async
    def get_recent_ai_chat_history(self, user_name, limit=10):
        messages = AIChatMessage.objects.filter(room_name=self.room_name, user_name=user_name).order_by('-timestamp')[:limit]
        history = []
        for msg in reversed(messages):
            history.append({"role": "user", "content": msg.message})
            if msg.ai_message:
                history.append({"role": "assistant", "content": msg.ai_message})
        return history
    
    async def evaluate_user_guess(self, puzzle_question, user_question, puzzle_full_story, chat_history):
        system_prompt = f"""
你是「海龜湯」遊戲的一位頂級遊戲主持人（Game Master）。你的最高原則是確保遊戲對玩家來說是「公平且有趣的」。你的輸出必須是一個 JSON 物件，包含三個 key：`reasoning`, `evaluation`, 和 `answer`。

# 判斷規則：
1.  **勝利 (Solved)**: 若玩家直接反問你，不可以回應他。除此之外，如果玩家的猜測已經親口完整說出了謎底的核心因果鏈，`evaluation` 為 "solved"。

3.  **是非回答 (Yes/No Answer)**: 如果問題清晰無歧義，且能以單一的是或否回答，`evaluation` 為 "query"，`answer` 為「是」或「否」。若玩家問是不是商業活動，須回答否。因為除了這頓晚餐外並無其他商業活動。
4.  **是也不是 (Yes and No)**: 如果玩家的提問內容，根據謎底故事，一部分為「是」而另一部分為「否」，導致無法用單一的是非回答，`evaluation` 為 "query"，`answer` 為「是也不是」。這提示玩家其假設部分正確，需要將問題拆分得更細緻。例如，若謎底是「他吃了一根冰糖葫蘆」，玩家問「他吃了水果嗎？」，因冰糖葫蘆是水果做成，但不是嚴格意義上的水果。又例如，玩家問「他要送老闆支票嗎？」，則也是回答「是也不是」，因為支票是他給的，但這張支票的價值在於名人寫的字。又例如，玩家問「他是美食評論家嗎？」則回答「是也不是」，因為謎底並沒有明示男子的身分，但「名人」確實也包含「知名的美食評論家」。若玩家問「是不是很貴的東西」，也回答「是也不是」，因為重點在收藏價值，而非金額。
5.  **無關回答 (Irrelevant)**: 如果問題是開放式問題、與謎底無關，或無法根據謎底判斷，`evaluation` 為 "query"，`answer` 為 "與此無關"。

**嚴格禁止**：
-   回答其他不屬於以上的內容。

---
# 謎題題目：{puzzle_question}
# 謎底完整故事（你的唯一判斷依據）：{puzzle_full_story}
---
"""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_question})
        # data = {"model": "gpt-4.1", "messages": messages, "temperature": 0.0, "response_format": {"type": "json_object"}}
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(api_url, headers=headers, json=data) as resp:
        #         if resp.status == 200:
        #             try:
        #                 response_data = await resp.json()
        #                 content_str = response_data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
        #                 full_evaluation = json.loads(content_str)
        #                 return { "evaluation": full_evaluation.get("evaluation", "query"), "answer": full_evaluation.get("answer", "與此無關") }
        #             except (json.JSONDecodeError, AttributeError, KeyError) as e:
        #                 logger.error(f"Error parsing AI JSON response: {e}")
        #                 return {"evaluation": "query", "answer": "與此無關"}
        #         else:
        #             logger.error(f"OpenAI API Error: {resp.status} - {await resp.text()}")
        #             return {"evaluation": "query", "answer": "與此無關"}
   
        response_json = await self.call_openai_with_fallback(messages, "gpt-4.1", "gpt-4-turbo", 0.0, {"type": "json_object"})

        if response_json:
            try:
                content_str = response_json.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                full_evaluation = json.loads(content_str)
                return { "evaluation": full_evaluation.get("evaluation", "query"), "answer": full_evaluation.get("answer", "與此無關") }
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                logger.error(f"Error parsing AI JSON response: {e}")
                return {"evaluation": "query", "answer": "與此無關"}
        else:
            return {"evaluation": "query", "answer": "裁判服務暫時不可用，請稍後再試"}
                

    # ⭐ FIXED: Added the 'current_user_name' parameter to the function definition.
    @sync_to_async
    def get_recent_human_chat_history(self, current_user_name, limit=10):
        messages = ChatMessage.objects.filter(room_name=self.room_name).order_by('-timestamp')[:limit]
        history_lines = []
        for msg in reversed(messages):
            speaker = "Me" if msg.user_name == current_user_name else "Partner"
            history_lines.append(f"{speaker}: {msg.message}")
        return "\n".join(history_lines)
