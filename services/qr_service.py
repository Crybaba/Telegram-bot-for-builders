import cv2
import numpy as np
from pyzbar import pyzbar
from PIL import Image
import io
import aiohttp
import asyncio
from typing import List, Optional, Tuple
from database.models import Tool, Status
from database.connection import SessionLocal

class QRCodeService:
    @staticmethod
    async def download_photo(file_id: str, bot) -> Optional[bytes]:
        """Скачивает фото по file_id"""
        try:
            file = await bot.get_file(file_id)
            file_path = file.file_path
            
            # Скачиваем файл
            file_data = await bot.download_file(file_path)
            return file_data.read()
        except Exception as e:
            print(f"Ошибка скачивания фото: {e}")
            return None

    @staticmethod
    def decode_qr_codes(image_data: bytes) -> List[str]:
        """Декодирует QR-коды из изображения"""
        try:
            # Конвертируем bytes в numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Находим QR-коды
            qr_codes = pyzbar.decode(image)
            
            # Извлекаем данные из QR-кодов
            decoded_codes = []
            for qr in qr_codes:
                decoded_data = qr.data.decode('utf-8')
                decoded_codes.append(decoded_data)
            
            return decoded_codes
        except Exception as e:
            print(f"Ошибка декодирования QR-кода: {e}")
            return []

    @staticmethod
    def get_tools_by_qr_codes(qr_codes: List[str], object_id: int) -> List[Tool]:
        """Получает инструменты по QR-кодам для конкретного объекта"""
        db = SessionLocal()
        try:
            tools = db.query(Tool).filter(
                Tool.qr_code_value.in_(qr_codes),
                Tool.current_object_id == object_id
            ).all()
            
            # Предзагружаем связанные данные для каждого инструмента
            for tool in tools:
                _ = tool.tool_name.name  # Загружаем tool_name
                _ = tool.status.name     # Загружаем status
                _ = tool.inventory_number  # Загружаем inventory_number
                _ = tool.qr_code_value   # Загружаем qr_code_value
            
            return tools
        finally:
            db.close()

    @staticmethod
    def get_all_tools_on_object(object_id: int) -> List[Tool]:
        """Получает все инструменты на объекте"""
        db = SessionLocal()
        try:
            tools = db.query(Tool).filter(Tool.current_object_id == object_id).all()
            
            # Предзагружаем связанные данные для каждого инструмента
            for tool in tools:
                _ = tool.tool_name.name  # Загружаем tool_name
                _ = tool.status.name     # Загружаем status
                _ = tool.inventory_number  # Загружаем inventory_number
                _ = tool.qr_code_value   # Загружаем qr_code_value
            
            return tools
        finally:
            db.close()

    @staticmethod
    def update_tool_status(tool_id: int, status_name: str):
        """Обновляет статус инструмента"""
        db = SessionLocal()
        try:
            # Получаем статус по названию
            status = db.query(Status).filter(Status.name == status_name).first()
            if not status:
                print(f"Статус '{status_name}' не найден")
                return False
            
            # Обновляем статус инструмента
            tool = db.query(Tool).filter(Tool.id == tool_id).first()
            if tool:
                tool.status_id = status.id
                db.commit()
                return True
            return False
        finally:
            db.close()

    @staticmethod
    async def process_inventory_photos(photo_file_ids: List[str], object_id: int, bot) -> Tuple[List[Tool], List[Tool]]:
        """Обрабатывает фотографии инвентаризации и возвращает найденные и отсутствующие инструменты"""
        found_tools = []
        all_qr_codes = []
        
        # Обрабатываем все фотографии
        for file_id in photo_file_ids:
            # Скачиваем фото
            image_data = await QRCodeService.download_photo(file_id, bot)
            if not image_data:
                continue
            
            # Декодируем QR-коды
            qr_codes = QRCodeService.decode_qr_codes(image_data)
            all_qr_codes.extend(qr_codes)
        
        # Получаем инструменты по найденным QR-кодам
        found_tools = QRCodeService.get_tools_by_qr_codes(all_qr_codes, object_id)
        
        # Получаем все инструменты на объекте
        all_tools = QRCodeService.get_all_tools_on_object(object_id)
        
        # Находим отсутствующие инструменты
        found_tool_ids = {tool.id for tool in found_tools}
        missing_tools = [tool for tool in all_tools if tool.id not in found_tool_ids]
        
        return found_tools, missing_tools

    @staticmethod
    def update_inventory_statuses(found_tools: List[Tool], missing_tools: List[Tool]):
        """Обновляет статусы инструментов по результатам инвентаризации"""
        # Обновляем статус найденных инструментов на "В наличии"
        for tool in found_tools:
            tool_id = tool.id
            if hasattr(tool_id, 'value'):
                tool_id = tool_id.value
            try:
                tool_id_int = int(tool_id) if tool_id is not None else None
                if tool_id_int is not None:
                    QRCodeService.update_tool_status(tool_id_int, "В наличии")
            except Exception as e:
                print(f"Ошибка обновления статуса инструмента {tool_id}: {e}")
        
        # Обновляем статус отсутствующих инструментов на "Утерян"
        for tool in missing_tools:
            tool_id = tool.id
            if hasattr(tool_id, 'value'):
                tool_id = tool_id.value
            try:
                tool_id_int = int(tool_id) if tool_id is not None else None
                if tool_id_int is not None:
                    QRCodeService.update_tool_status(tool_id_int, "Утерян")
            except Exception as e:
                print(f"Ошибка обновления статуса инструмента {tool_id}: {e}")
        
        print(f"Обновлено статусов: {len(found_tools)} найдено, {len(missing_tools)} утеряно") 