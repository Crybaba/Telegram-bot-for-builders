from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.user_service import UserService
from services.tool_request_service import ToolRequestService
from services.inventory_check_service import InventoryCheckService
from database.connection import SessionLocal
from database.models import User, Object, Tool, ToolRequest, InventoryCheck
from aiogram import Bot
from datetime import datetime
import xml.etree.ElementTree as ET
from services.qr_service import QRCodeService
from services.inventory_report_service import InventoryReportService
from bot import handle_empty_data

async def send_notification_safely(bot: Bot, user: any, message: str) -> bool:
    """
    Безопасно отправляет уведомление пользователю.
    
    Args:
        bot: Экземпляр бота
        user: Объект пользователя из базы данных
        message: Текст сообщения
        
    Returns:
        bool: True если сообщение отправлено успешно, False в противном случае
    """
    try:
        # Сначала пытаемся отправить по chat_id
        if hasattr(user, 'chat_id') and user.chat_id:
            await bot.send_message(user.chat_id, message)
            return True
        
        # Если нет chat_id, пытаемся по username
        if hasattr(user, 'username') and user.username:
            username = str(user.username)
            # Убираем @ если есть
            if username.startswith('@'):
                username = username[1:]
            
            # Пытаемся отправить сообщение
            await bot.send_message(username, message)
            return True
            
        return False
    except Exception as e:
        error_message = str(e).lower()
        if "chat not found" in error_message or "user not found" in error_message:
            print(f"Пользователь {getattr(user, 'username', 'Unknown')} не найден или не начал диалог с ботом")
        elif "blocked" in error_message:
            print(f"Пользователь {getattr(user, 'username', 'Unknown')} заблокировал бота")
        else:
            print(f"Ошибка отправки уведомления пользователю {getattr(user, 'username', 'Unknown')}: {e}")
        return False

router = Router()

# === Message Constants ===
MSG_FOREMAN_MENU = "Меню бригадира:"
MSG_NO_OBJECT = "❌ Не удалось определить ваш объект."
MSG_NO_REGISTRATIONS = "Нет новых заявок на регистрацию на ваш объект."
MSG_REG_REQUEST = "Заявка на регистрацию: {username} ({name})"
MSG_REG_APPROVED = "Регистрация подтверждена!"
MSG_REG_APPROVED_USER = "🎉 Ваша заявка на регистрацию одобрена! Вы назначены на объект: {object_name}"
MSG_REG_REJECTED = "Регистрация отклонена!"
MSG_REG_REJECTED_USER = "❌ Ваша заявка на регистрацию отклонена. Попробуйте зарегистрироваться снова."
MSG_REG_APPROVE_ERROR = "❌ Ошибка при подтверждении регистрации"
MSG_REG_REJECT_ERROR = "❌ Ошибка при отклонении регистрации"
MSG_NO_TOOLS = "🔧 На вашем объекте нет инструментов."
MSG_TOOLS_LIST = "🔧 Инструменты на вашем объекте:\n"
MSG_NO_TOOL_REQUESTS = "Нет заявок на передачу инструментов."
MSG_TOOL_REQUEST = "Заявка: {tool_name} (инв. №{inv_num}) для {to_object}"
MSG_TOOL_REQUEST_APPROVED = "Заявка одобрена, инструмент передан!"
MSG_TOOL_REQUEST_REJECTED = "Заявка отклонена!"
MSG_INVENTORY_PHOTO_PROMPT = "Отправьте фотографии QR-кодов всех инструментов на объекте одним или несколькими сообщениями."
MSG_INVENTORY_PHOTO_RECEIVED = "Фото получено. Отправьте ещё или нажмите 'Подтвердить'."
MSG_INVENTORY_DONE = "Инвентаризация завершена! Вот XML для 1C:"
MSG_NO_WORKERS = "На вашем объекте нет рабочих."
MSG_WORKERS_LIST = "👷 Рабочие на объекте:\n"
MSG_TOOL_REQUEST_APPROVED = "✅ Ваша заявка на инструмент '{tool_name}' (инв. №{inventory_number}) одобрена! Инструмент передан на объект '{object_name}'."
MSG_TOOL_REQUEST_REJECTED = "❌ Ваша заявка на инструмент '{tool_name}' (инв. №{inventory_number}) отклонена."

# Главное меню для бригадира
def get_foreman_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Регистрации на объект", callback_data="registrations")
    builder.button(text="👷 Рабочие на объекте", callback_data="object_workers")
    builder.button(text="🔧 Инструменты на объекте", callback_data="foreman_tools")
    builder.button(text="📦 Заявки на инструменты", callback_data="foreman_requests")
    builder.button(text="📋 Провести инвентаризацию", callback_data="start_inventory")
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command("foreman"))
async def cmd_foreman_menu(message: Message):
    await message.answer(MSG_FOREMAN_MENU, reply_markup=get_foreman_menu())

# Просмотр регистраций на объект
@router.callback_query(F.data == "registrations")
async def show_registrations(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    db = SessionLocal()
    try:
        registrations = db.query(User).filter(
            User.object_id == user.object.id, 
            User.role_id == 1
        ).all()
    finally:
        db.close()
    if not registrations:
        await handle_empty_data(callback, "Нет новых заявок на регистрацию на ваш объект.", "back_to_menu")
        return
    for reg in registrations:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data=f"approve_reg_{reg.id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_reg_{reg.id}")
        await callback.message.edit_text(f"Заявка на регистрацию: {reg.username} ({reg.name or 'Без имени'})", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("approve_reg_"))
async def approve_registration(callback: CallbackQuery):
    reg_id = int(callback.data.removeprefix("approve_reg_"))
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    foreman = UserService.get_user_by_username(username)
    if not foreman or not foreman.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    if UserService.approve_user(reg_id, foreman.object.id):
        await callback.message.edit_text("Регистрация подтверждена!", reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
        user = UserService.get_user_by_id(reg_id)
        if user and callback.bot:
            await send_notification_safely(
                callback.bot,
                user,
                MSG_REG_APPROVED_USER.format(object_name=foreman.object.name)
            )
    else:
        await callback.answer(MSG_REG_APPROVE_ERROR, show_alert=True)

@router.callback_query(F.data.startswith("reject_reg_"))
async def reject_registration(callback: CallbackQuery):
    reg_id = int(callback.data.removeprefix("reject_reg_"))
    if UserService.reject_user(reg_id):
        await callback.message.edit_text("Регистрация отклонена!", reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
        user = UserService.get_user_by_id(reg_id)
        if user and callback.bot:
            await send_notification_safely(
                callback.bot,
                user,
                MSG_REG_REJECTED_USER
            )
    else:
        await callback.answer(MSG_REG_REJECT_ERROR, show_alert=True)

# Просмотр инструментов на объекте
@router.callback_query(F.data == "foreman_tools")
async def show_foreman_tools(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    
    # Перезагружаем объект в текущей сессии с загрузкой связанных данных
    db = SessionLocal()
    try:
        object_with_tools = db.query(Object).filter(Object.id == user.object.id).first()
        if not object_with_tools:
            await callback.answer(MSG_NO_OBJECT, show_alert=True)
            return
        
        # Загружаем инструменты с их связанными данными
        tools = db.query(Tool).filter(Tool.current_object_id == user.object.id).all()
        
        # Предзагружаем связанные данные для каждого инструмента
        for tool in tools:
            _ = tool.tool_name.name  # Загружаем tool_name
            _ = tool.status.name     # Загружаем status
            _ = tool.inventory_number  # Загружаем inventory_number
    finally:
        db.close()
    
    if not tools:
        await callback.message.edit_text(MSG_NO_TOOLS, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
        return
    text = MSG_TOOLS_LIST
    for tool in tools:
        text += f"• {tool.tool_name.name} (инв. №{tool.inventory_number}) — {tool.status.name}\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())

# Просмотр и обработка заявок на инструменты
@router.callback_query(F.data == "foreman_requests")
async def show_foreman_requests(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    db = SessionLocal()
    try:
        # Показываем только заявки, которые еще не выполнены (не имеют статус "Выполнено")
        requests = db.query(ToolRequest).filter(
            ToolRequest.from_object_id == user.object.id,
            ToolRequest.status_id != 2  # 2 = "Выполнено"
        ).all()
        
        # Предзагружаем связанные данные в текущей сессии
        request_data = []
        for req in requests:
            tool_name = req.tool.tool_name.name if req.tool and req.tool.tool_name else "Неизвестный инструмент"
            inventory_number = req.tool.inventory_number if req.tool else "Без номера"
            to_object_name = req.to_object.name if req.to_object else "Неизвестный объект"
            requester_name = req.requester.name if req.requester else "Неизвестный пользователь"
            requester_username = req.requester.username if req.requester else "Без username"
            request_data.append({
                'id': req.id,
                'tool_name': tool_name,
                'inventory_number': inventory_number,
                'to_object_name': to_object_name,
                'requester_name': requester_name,
                'requester_username': requester_username
            })
    finally:
        db.close()
    
    if not request_data:
        await handle_empty_data(callback, "Нет заявок на передачу инструментов.", "back_to_menu")
        return
    
    # Отправляем каждую заявку отдельным сообщением
    for req_data in request_data:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Одобрить", callback_data=f"approve_req_{req_data['id']}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_req_{req_data['id']}")
        builder.adjust(2)
        
        message_text = f"📋 Заявка на инструмент\n\n"
        message_text += f"🔧 Инструмент: {req_data['tool_name']}\n"
        message_text += f"📝 Инв. номер: {req_data['inventory_number']}\n"
        message_text += f"🏗️ Объект назначения: {req_data['to_object_name']}\n"
        message_text += f"👤 Отправитель: {req_data['requester_name']} ({req_data['requester_username']})"
        
        await callback.message.answer(message_text, reply_markup=builder.as_markup())
    
    # Отправляем сообщение с кнопкой "Назад"
    await callback.message.answer("📋 Все заявки на инструменты:", reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())

@router.callback_query(F.data.startswith("approve_req_"))
async def approve_tool_request(callback: CallbackQuery):
    req_id = int(callback.data.removeprefix("approve_req_"))
    
    # Получаем пользователя, который обрабатывает заявку
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    approver = UserService.get_user_by_username(username)
    if not approver:
        await callback.answer("❌ Не удалось определить пользователя!", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        req = db.query(ToolRequest).filter(ToolRequest.id == req_id).first()
        if req:
            # Меняем статус на "Выполнено" (id = 2)
            req.status_id = 2
            # Устанавливаем approver_id
            req.approver_id = approver.id
            # Перемещаем инструмент на новый объект
            req.tool.current_object_id = req.to_object_id
            db.commit()
            
            # Удаляем сообщение с заявкой
            await callback.message.delete()
            # Отправляем уведомление
            await callback.answer("✅ Заявка обработана, инструмент передан!", show_alert=True)
            
            # Отправляем уведомление пользователю, который подал заявку
            if req.requester and callback.bot:
                tool_name = req.tool.tool_name.name if req.tool and req.tool.tool_name else "инструмент"
                inventory_number = req.tool.inventory_number if req.tool else "Без номера"
                object_name = req.to_object.name if req.to_object else "неизвестный объект"
                notification_message = MSG_TOOL_REQUEST_APPROVED.format(
                    tool_name=tool_name,
                    inventory_number=inventory_number,
                    object_name=object_name
                )
                await send_notification_safely(callback.bot, req.requester, notification_message)
        else:
            await callback.answer("❌ Заявка не найдена!", show_alert=True)
    except Exception as e:
        print(f"Ошибка при обработке заявки: {e}")
        await callback.answer("❌ Ошибка при обработке заявки!", show_alert=True)
    finally:
        db.close()

@router.callback_query(F.data.startswith("reject_req_"))
async def reject_tool_request(callback: CallbackQuery):
    req_id = int(callback.data.removeprefix("reject_req_"))
    
    # Получаем пользователя, который обрабатывает заявку
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    approver = UserService.get_user_by_username(username)
    if not approver:
        await callback.answer("❌ Не удалось определить пользователя!", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        req = db.query(ToolRequest).filter(ToolRequest.id == req_id).first()
        if req:
            # Меняем статус на "Выполнено" (id = 2)
            req.status_id = 2
            # Устанавливаем approver_id
            req.approver_id = approver.id
            db.commit()
            
            # Удаляем сообщение с заявкой
            await callback.message.delete()
            # Отправляем уведомление
            await callback.answer("✅ Заявка обработана!", show_alert=True)
            
            # Отправляем уведомление пользователю, который подал заявку
            if req.requester and callback.bot:
                tool_name = req.tool.tool_name.name if req.tool and req.tool.tool_name else "инструмент"
                inventory_number = req.tool.inventory_number if req.tool else "Без номера"
                notification_message = MSG_TOOL_REQUEST_REJECTED.format(
                    tool_name=tool_name,
                    inventory_number=inventory_number
                )
                await send_notification_safely(callback.bot, req.requester, notification_message)
        else:
            await callback.answer("❌ Заявка не найдена!", show_alert=True)
    except Exception as e:
        print(f"Ошибка при обработке заявки: {e}")
        await callback.answer("❌ Ошибка при обработке заявки!", show_alert=True)
    finally:
        db.close()

# Инвентаризация: FSM для сбора фото QR-кодов
from aiogram.fsm.state import State, StatesGroup

class InventoryStates(StatesGroup):
    waiting_for_photos = State()
    confirm = State()

@router.callback_query(F.data == "start_inventory")
async def start_inventory(callback: CallbackQuery, state: FSMContext):
    await state.set_state(InventoryStates.waiting_for_photos)
    # Сохраняем ID сообщения для последующего редактирования
    await state.update_data(message_id=callback.message.message_id)
    await callback.message.edit_text("Отправьте фотографии QR-кодов всех инструментов на объекте одним или несколькими сообщениями.\n\n📸 Фотографий получено: 0", reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())

@router.message(InventoryStates.waiting_for_photos)
async def receive_photos(message: Message, state: FSMContext):
    photos = (await state.get_data()).get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    
    # Получаем ID сообщения для редактирования
    data = await state.get_data()
    message_id = data.get("message_id")
    
    # Создаем клавиатуру с кнопкой "Подтвердить" только если есть фотографии
    builder = InlineKeyboardBuilder()
    if len(photos) > 0:
        builder.button(text="✅ Подтвердить", callback_data="confirm_inventory")
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    builder.adjust(1)
    
    # Редактируем исходное сообщение
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=f"Отправьте фотографии QR-кодов всех инструментов на объекте одним или несколькими сообщениями.\n\n📸 Фотографий получено: {len(photos)}",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")

@router.callback_query(F.data == "confirm_inventory")
async def confirm_inventory(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    
    # Показываем сообщение о начале обработки
    await callback.message.edit_text("🔍 Обрабатываю фотографии и распознаю QR-коды...", reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
    
    try:
        # Обрабатываем фотографии и получаем результаты
        found_tools, missing_tools = await QRCodeService.process_inventory_photos(
            photos, user.object.id, callback.bot
        )
        
        # Обновляем статусы инструментов в базе данных
        QRCodeService.update_inventory_statuses(found_tools, missing_tools)
        
        # Создаем запись об инвентаризации
        check = InventoryCheckService.create_check(
            user_id=user.id, 
            object_id=user.object.id, 
            date=datetime.utcnow()
        )
        
        # Генерируем отчет
        total_tools = len(found_tools) + len(missing_tools)
        xml_report = InventoryReportService.generate_inventory_xml(
            object_name=user.object.name,
            user_name=user.username,
            date=check.date,
            found_tools=found_tools,
            missing_tools=missing_tools,
            total_tools=total_tools
        )
        
        # Генерируем текстовое резюме
        summary_text = InventoryReportService.generate_summary_text(
            object_name=user.object.name,
            found_tools=found_tools,
            missing_tools=missing_tools,
            total_tools=total_tools
        )
        
        # Отправляем результаты
        await callback.message.edit_text(
            summary_text,
            reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup()
        )
        
        # Отправляем XML-отчет как файл
        import tempfile
        import os
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(xml_report)
            temp_file_path = temp_file.name
        
        try:
            # Отправляем файл
            await callback.message.answer_document(
                document=FSInputFile(
                    path=temp_file_path,
                    filename=f"inventory_report_{user.object.name}_{check.date.strftime('%Y%m%d_%H%M%S')}.xml"
                ),
                caption=f"📄 XML-отчет инвентаризации объекта '{user.object.name}' от {check.date.strftime('%d.%m.%Y %H:%M')}"
            )
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except Exception as e:
        print(f"Ошибка при обработке инвентаризации: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при обработке инвентаризации: {str(e)}",
            reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup()
        )
    
    await state.clear()

@router.callback_query(F.data == "object_workers")
async def show_object_workers(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    db = SessionLocal()
    try:
        workers = db.query(User).filter(User.object_id == user.object.id, User.role_id == 3).all()
    finally:
        db.close()
    if not workers:
        await callback.message.edit_text("На вашем объекте нет рабочих.", reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
        return
    text = "👷 Рабочие на объекте:\n"
    for w in workers:
        text += f"• {w.username} ({w.name or 'Без имени'})\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())

# Обработчик кнопки "Назад" - возврат в главное меню
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if user and user.role and user.role.name == "прораб объекта":
        await callback.message.edit_text(MSG_FOREMAN_MENU, reply_markup=get_foreman_menu())
    else:
        await callback.message.edit_text("✅ Вы уже зарегистрированы!", reply_markup=get_worker_menu()) 