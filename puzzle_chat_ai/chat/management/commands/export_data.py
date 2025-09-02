# chat/management/commands/export_data.py

import csv
import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db.models import CharField # 引入 CharField 檢查字段類型

class Command(BaseCommand):
    help = 'Exports data from specified models or all models in the chat app to CSV files, optionally filtering by room_name.' # 修改幫助信息

    def add_arguments(self, parser):
        # 參數：可以指定一個或多個模型名稱來單獨匯出
        parser.add_argument(
            '--model',
            nargs='*', # 允許接收多個模型名稱
            type=str,
            help='The name(s) of the model(s) to export (e.g., ChatMessage AIChatMessage). Exports all if not specified.'
        )
        # 參數：指定輸出的資料夾路徑
        parser.add_argument(
            '--output_dir',
            type=str,
            help='The directory where CSV files will be saved.',
            default='.' # 預設為當前目錄
        )
        # 新增參數：指定 room_name 來篩選資料
        parser.add_argument(
            '--room_name',
            type=str,
            help='Filter data by a specific room_name (only applies to models with a "room_name" field).',
            required=False # 非必需參數
        )

    def handle(self, *args, **options):
        app_name = 'chat' #
        model_names_to_export = options['model'] #
        output_dir = options['output_dir'] #
        room_name_filter = options['room_name'] # 獲取 room_name 參數值

        # 確保輸出目錄存在
        os.makedirs(output_dir, exist_ok=True) #

        # 列出所有我們想要匯出的模型
        all_models = [
            'ChatMessage',
            'ChatMessageSummary',
            'AIChatMessage',
            'AIChatMessageSummary',
        ] #

        # 如果使用者沒有指定模型，就匯出全部
        if not model_names_to_export: #
            models_to_process = all_models #
        else:
            # 檢查使用者指定的模型是否存在
            for model_name in model_names_to_export: #
                if model_name not in all_models: #
                    raise CommandError(f"Model '{model_name}' not found or not supported for export.") #
            models_to_process = model_names_to_export #

        self.stdout.write(self.style.SUCCESS(f"Starting export for models: {', '.join(models_to_process)}")) #
        if room_name_filter: #
            self.stdout.write(self.style.SUCCESS(f"Filtering by room_name: '{room_name_filter}'")) #

        # 循環處理每一個需要匯出的模型
        for model_name in models_to_process: #
            try:
                model = apps.get_model(app_label=app_name, model_name=model_name) #
                self.export_model_to_csv(model, output_dir, room_name_filter) # 傳遞 room_name_filter
            except LookupError: #
                self.stderr.write(self.style.ERROR(f"Model '{model_name}' not found in app '{app_name}'.")) #
            except Exception as e: #
                self.stderr.write(self.style.ERROR(f"An error occurred while exporting '{model_name}': {e}")) #

    def export_model_to_csv(self, model, output_dir, room_name_filter=None): # 接收 room_name_filter 參數，並設為 None 預設值
        model_name = model._meta.model_name #
        file_path = os.path.join(output_dir, f"{model_name}_export.csv") #

        self.stdout.write(f"  - Exporting model '{model_name}' to '{file_path}'...") #

        # 自動獲取模型的所有欄位名稱
        field_names = [field.name for field in model._meta.get_fields() if not field.is_relation] #

        # 查詢資料庫獲取所有資料
        queryset = model.objects.all() #

        # 判斷模型是否有 'room_name' 字段，並應用過濾器
        if room_name_filter: #
            # 檢查模型是否有 room_name 字段
            has_room_name_field = False #
            for field in model._meta.get_fields(): #
                if field.name == 'room_name' and isinstance(field, CharField): # 確保字段存在且是 CharField
                    has_room_name_field = True #
                    break #

            if has_room_name_field: #
                queryset = queryset.filter(room_name=room_name_filter) # 應用過濾
                self.stdout.write(self.style.SUCCESS(f"    - Applied room_name filter for '{room_name_filter}' on model '{model_name}'.")) #
            else:
                self.stdout.write(self.style.WARNING(f"    - Warning: Model '{model_name}' does not have a 'room_name' field or it's not a CharField. Room name filter will be ignored for this model.")) #

        if not queryset.exists(): #
            self.stdout.write(self.style.WARNING(f"    - Model '{model_name}' has no data to export (or no data matching the filter). Skipping.")) # 修改提示信息
            return #

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile: #
            writer = csv.writer(csvfile) #

            # 寫入標頭
            writer.writerow(field_names) #

            # 寫入資料
            for instance in queryset: #
                row = [] #
                for field in field_names: #
                    value = getattr(instance, field) #
                    # 對特殊類型進行處理
                    if hasattr(value, 'isoformat'): # 處理 datetime
                        value = value.isoformat() #
                    elif isinstance(value, dict) or isinstance(value, list): # 處理 JSONField
                        value = json.dumps(value, ensure_ascii=False) #
                    row.append(value) #
                writer.writerow(row) #

        self.stdout.write(self.style.SUCCESS(f"    - Successfully exported {queryset.count()} records.")) #