# Bot package 
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

async def handle_empty_data(
    callback: CallbackQuery, 
    message_text: str, 
    back_callback_data: str,
    additional_buttons: list | None = None
) -> None:
    """
    Обрабатывает случай отсутствия данных с возможностью редактирования или отправки нового сообщения.
    
    Args:
        callback: CallbackQuery объект
        message_text: Текст сообщения
        back_callback_data: callback_data для кнопки "Назад"
        additional_buttons: Список дополнительных кнопок в формате [{"text": "...", "callback_data": "..."}]
    """
    builder = InlineKeyboardBuilder()
    
    # Добавляем дополнительные кнопки, если они есть
    if additional_buttons:
        for button in additional_buttons:
            builder.button(text=button["text"], callback_data=button["callback_data"])
    
    # Добавляем кнопку "Назад"
    builder.button(text="🔙 Назад", callback_data=back_callback_data)
    
    # Настраиваем расположение кнопок
    if additional_buttons:
        builder.adjust(len(additional_buttons), 1)
    else:
        builder.adjust(1)
    
    # Пытаемся отредактировать сообщение, если это возможно
    if callback.message:
        try:
            await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
        except Exception:
            # Если редактирование не удалось, отправляем новое сообщение
            await callback.message.answer(message_text, reply_markup=builder.as_markup())
    else:
        # Если нет сообщения для редактирования, отправляем новое
        await callback.answer(message_text, reply_markup=builder.as_markup()) 