# chat/management/commands/delete_room_data.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
# ⭐ 導入您所有與房間相關的模型
from chat.models import ChatMessage, ai_ChatMessage, chatMessage_summary, ai_ChatMessage_summary

class Command(BaseCommand):
    help = 'Deletes all data associated with a specific room name from all relevant models.'

    def add_arguments(self, parser):
        # 定義 --room 參數，這是必須提供的
        parser.add_argument(
            '--room',
            type=str,
            help='The name of the room to delete data from.',
            required=True
        )

    def handle(self, *args, **options):
        room_name = options['room']
        
        # ⭐ 列出所有需要被清理的模型
        models_to_clean = [
            ChatMessage, 
            ai_ChatMessage, 
            chatMessage_summary, 
            ai_ChatMessage_summary
        ]

        self.stdout.write(self.style.WARNING(f"--- PRE-DELETION CHECK FOR ROOM: '{room_name}' ---"))
        self.stdout.write("This command will permanently delete data. Please review the counts below.")

        total_records_to_delete = 0
        records_count_per_model = {}

        # 步驟一：檢查並計算將要刪除的紀錄數量
        for model in models_to_clean:
            model_name = model._meta.model_name
            # 檢查模型是否有 room_name 欄位
            if hasattr(model, 'room_name'):
                queryset = model.objects.filter(room_name=room_name)
                count = queryset.count()
                records_count_per_model[model_name] = count
                total_records_to_delete += count
                self.stdout.write(f"Found {count} records in '{model_name}' for room '{room_name}'.")
        
        if total_records_to_delete == 0:
            self.stdout.write(self.style.SUCCESS("No data found for this room. Nothing to delete."))
            return

        # 步驟二：要求使用者進行最終確認
        self.stdout.write(self.style.ERROR_OUTPUT(f"\nWARNING: You are about to delete a total of {total_records_to_delete} records from room '{room_name}'.\nThis action CANNOT be undone."))
        
        confirmation = input("Are you sure you want to proceed? Type 'yes' to continue: ")

        if confirmation.lower() != 'yes':
            self.stdout.write(self.style.NOTICE("Deletion cancelled by user."))
            return

        # 步驟三：在確認後，執行刪除操作
        try:
            # 使用 transaction.atomic 確保所有刪除操作要麼全部成功，要麼全部失敗
            with transaction.atomic():
                for model_name, count in records_count_per_model.items():
                    if count > 0:
                        model = next(m for m in models_to_clean if m._meta.model_name == model_name)
                        self.stdout.write(f"Deleting {count} records from '{model_name}'...")
                        model.objects.filter(room_name=room_name).delete()
            
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully deleted all data for room '{room_name}'."))

        except Exception as e:
            raise CommandError(f'An error occurred during deletion. The operation was rolled back. Error: {e}')