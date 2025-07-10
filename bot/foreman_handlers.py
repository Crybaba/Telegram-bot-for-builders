from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
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
        # Показываем только пользователей с ролью 1 (в обработке) на данном объекте
        registrations = db.query(User).filter(
            User.object_id == user.object.id, 
            User.role_id == 1  # Только "в обработке"
        ).all()
    finally:
        db.close()
    if not registrations:
        await callback.message.answer(MSG_NO_REGISTRATIONS)
        return
    for reg in registrations:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data=f"approve_reg_{reg.id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_reg_{reg.id}")
        await callback.message.answer(MSG_REG_REQUEST.format(username=reg.username, name=reg.name or 'Без имени'), reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("approve_reg_"))
async def approve_registration(callback: CallbackQuery):
    reg_id = int(callback.data.removeprefix("approve_reg_"))
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    foreman = UserService.get_user_by_username(username)
    if not foreman or not foreman.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    if UserService.approve_user(reg_id, foreman.object.id):
        await callback.message.answer(MSG_REG_APPROVED)
        # Уведомляем пользователя
        user = UserService.get_user_by_id(reg_id)
        if user:
            try:
                await callback.bot.send_message(
                    user.username,
                    MSG_REG_APPROVED_USER.format(object_name=foreman.object.name)
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
    else:
        await callback.answer(MSG_REG_APPROVE_ERROR, show_alert=True)

@router.callback_query(F.data.startswith("reject_reg_"))
async def reject_registration(callback: CallbackQuery):
    reg_id = int(callback.data.removeprefix("reject_reg_"))
    if UserService.reject_user(reg_id):
        await callback.message.answer(MSG_REG_REJECTED)
        # Уведомляем пользователя
        user = UserService.get_user_by_id(reg_id)
        if user:
            try:
                await callback.bot.send_message(
                    user.username,
                    MSG_REG_REJECTED_USER
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
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
    tools = user.object.tools
    if not tools:
        await callback.message.answer(MSG_NO_TOOLS)
        return
    text = MSG_TOOLS_LIST
    for tool in tools:
        text += f"• {tool.tool_name.name} (инв. №{tool.inventory_number}) — {tool.status.name}\n"
    await callback.message.answer(text)

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
        requests = db.query(ToolRequest).filter(ToolRequest.from_object_id == user.object.id).all()
    finally:
        db.close()
    if not requests:
        await callback.message.answer(MSG_NO_TOOL_REQUESTS)
        return
    for req in requests:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Одобрить", callback_data=f"approve_req_{req.id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_req_{req.id}")
        await callback.message.answer(MSG_TOOL_REQUEST.format(tool_name=req.tool.tool_name.name, inv_num=req.tool.inventory_number, to_object=req.to_object.name), reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("approve_req_"))
async def approve_tool_request(callback: CallbackQuery):
    req_id = int(callback.data.removeprefix("approve_req_"))
    db = SessionLocal()
    try:
        req = db.query(ToolRequest).filter(ToolRequest.id == req_id).first()
        if req:
            req.status_id = 2  # Одобрено
            req.tool.current_object_id = req.to_object_id
            db.commit()
    finally:
        db.close()
    await callback.message.answer(MSG_TOOL_REQUEST_APPROVED)

@router.callback_query(F.data.startswith("reject_req_"))
async def reject_tool_request(callback: CallbackQuery):
    req_id = int(callback.data.removeprefix("reject_req_"))
    db = SessionLocal()
    try:
        req = db.query(ToolRequest).filter(ToolRequest.id == req_id).first()
        if req:
            req.status_id = 3  # Отклонено
            db.commit()
    finally:
        db.close()
    await callback.message.answer(MSG_TOOL_REQUEST_REJECTED)

# Инвентаризация: FSM для сбора фото QR-кодов
from aiogram.fsm.state import State, StatesGroup

class InventoryStates(StatesGroup):
    waiting_for_photos = State()
    confirm = State()

@router.callback_query(F.data == "start_inventory")
async def start_inventory(callback: CallbackQuery, state: FSMContext):
    await state.set_state(InventoryStates.waiting_for_photos)
    await callback.message.answer(MSG_INVENTORY_PHOTO_PROMPT)

@router.message(InventoryStates.waiting_for_photos)
async def receive_photos(message: Message, state: FSMContext):
    photos = (await state.get_data()).get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(MSG_INVENTORY_PHOTO_RECEIVED, reply_markup=InlineKeyboardBuilder().button(text="Подтвердить", callback_data="confirm_inventory").as_markup())

@router.callback_query(F.data == "confirm_inventory")
async def confirm_inventory(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    # Сохраняем инвентаризацию
    check = InventoryCheckService.create_check(user_id=user.id, object_id=user.object.id, date=datetime.utcnow())
    # Генерируем XML для 1C
    root = ET.Element("InventoryCheck")
    ET.SubElement(root, "Object").text = user.object.name
    ET.SubElement(root, "Date").text = check.date.strftime("%Y-%m-%d %H:%M:%S")
    ET.SubElement(root, "User").text = user.username
    photos_elem = ET.SubElement(root, "Photos")
    for file_id in photos:
        ET.SubElement(photos_elem, "Photo").text = file_id
    xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
    # Отправляем отчёт и XML
    await callback.message.answer(MSG_INVENTORY_DONE)
    await callback.message.answer(f"<pre>{xml_str}</pre>", parse_mode="HTML")
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
        await callback.message.answer(MSG_NO_WORKERS)
        return
    text = MSG_WORKERS_LIST
    for w in workers:
        text += f"• {w.username} ({w.name or 'Без имени'})\n"
    await callback.message.answer(text) 