import xml.etree.ElementTree as ET
from typing import List
from database.models import Tool, Object, User
from datetime import datetime
import re

class InventoryReportService:
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        """Экранирует символы для Telegram MarkdownV2"""
        # Символы, которые нужно экранировать в MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text

    @staticmethod
    def generate_inventory_xml(
        object_name: str,
        user_name: str,
        date: datetime,
        found_tools: List[Tool],
        missing_tools: List[Tool],
        total_tools: int
    ) -> str:
        """Генерирует XML-отчет по инвентаризации"""
        
        # Создаем корневой элемент
        root = ET.Element("InventoryReport")
        
        # Добавляем метаданные
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "Object").text = object_name
        ET.SubElement(metadata, "User").text = user_name
        ET.SubElement(metadata, "Date").text = date.strftime("%Y-%m-%d %H:%M:%S")
        ET.SubElement(metadata, "TotalTools").text = str(total_tools)
        ET.SubElement(metadata, "FoundTools").text = str(len(found_tools))
        ET.SubElement(metadata, "MissingTools").text = str(len(missing_tools))
        
        # Добавляем найденные инструменты
        found_section = ET.SubElement(root, "FoundTools")
        for tool in found_tools:
            tool_elem = ET.SubElement(found_section, "Tool")
            ET.SubElement(tool_elem, "InventoryNumber").text = str(tool.inventory_number or "")
            ET.SubElement(tool_elem, "Name").text = str(tool.tool_name.name if tool.tool_name else "")
            ET.SubElement(tool_elem, "QRCode").text = str(tool.qr_code_value or "")
            ET.SubElement(tool_elem, "Status").text = "В наличии"
        
        # Добавляем отсутствующие инструменты
        missing_section = ET.SubElement(root, "MissingTools")
        for tool in missing_tools:
            tool_elem = ET.SubElement(missing_section, "Tool")
            ET.SubElement(tool_elem, "InventoryNumber").text = str(tool.inventory_number or "")
            ET.SubElement(tool_elem, "Name").text = str(tool.tool_name.name if tool.tool_name else "")
            ET.SubElement(tool_elem, "QRCode").text = str(tool.qr_code_value or "")
            ET.SubElement(tool_elem, "Status").text = "Утерян"
        
        # Конвертируем в строку
        xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        return xml_str

    @staticmethod
    def generate_summary_text(
        object_name: str,
        found_tools: List[Tool],
        missing_tools: List[Tool],
        total_tools: int
    ) -> str:
        """Генерирует текстовое резюме инвентаризации"""
        
        summary = f"📋 Результаты инвентаризации объекта '{object_name}'\n\n"
        summary += f"📊 Общая статистика:\n"
        summary += f"• Всего инструментов: {total_tools}\n"
        summary += f"• Найдено: {len(found_tools)} ✅\n"
        summary += f"• Утеряно: {len(missing_tools)} ❌\n\n"
        
        if found_tools:
            summary += f"✅ Найденные инструменты:\n"
            for tool in found_tools:
                tool_name = tool.tool_name.name if tool.tool_name else "Неизвестный инструмент"
                inventory_number = tool.inventory_number or "Без номера"
                summary += f"• {tool_name} (инв. №{inventory_number})\n"
            summary += "\n"
        
        if missing_tools:
            summary += f"❌ Утерянные инструменты:\n"
            for tool in missing_tools:
                tool_name = tool.tool_name.name if tool.tool_name else "Неизвестный инструмент"
                inventory_number = tool.inventory_number or "Без номера"
                summary += f"• {tool_name} (инв. №{inventory_number})\n"
        
        return summary 