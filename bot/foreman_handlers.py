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
    await message.answer("Меню бригадира:", reply_markup=get_foreman_menu())

# Просмотр регистраций на объект
@router.callback_query(F.data == "registrations")
async def show_registrations(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
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
        await callback.message.answer("Нет новых заявок на регистрацию на ваш объект.")
        return
    for reg in registrations:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data=f"approve_reg_{reg.id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_reg_{reg.id}")
        await callback.message.answer(f"Заявка на регистрацию: {reg.username} ({reg.name or 'Без имени'})", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("approve_reg_"))
async def approve_registration(callback: CallbackQuery):
    reg_id = int(callback.data.removeprefix("approve_reg_"))
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    foreman = UserService.get_user_by_username(username)
    if not foreman or not foreman.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    if UserService.approve_user(reg_id, foreman.object.id):
        await callback.message.answer("Регистрация подтверждена!")
        # Уведомляем пользователя
        user = UserService.get_user_by_id(reg_id)
        if user:
            try:
                await callback.bot.send_message(
                    user.username,
                    f"🎉 Ваша заявка на регистрацию одобрена! Вы назначены на объект: {foreman.object.name}"
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
    else:
        await callback.answer("❌ Ошибка при подтверждении регистрации", show_alert=True)

@router.callback_query(F.data.startswith("reject_reg_"))
async def reject_registration(callback: CallbackQuery):
    reg_id = int(callback.data.removeprefix("reject_reg_"))
    if UserService.reject_user(reg_id):
        await callback.message.answer("Регистрация отклонена!")
        # Уведомляем пользователя
        user = UserService.get_user_by_id(reg_id)
        if user:
            try:
                await callback.bot.send_message(
                    user.username,
                    "❌ Ваша заявка на регистрацию отклонена. Попробуйте зарегистрироваться снова."
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
    else:
        await callback.answer("❌ Ошибка при отклонении регистрации", show_alert=True)

# Просмотр инструментов на объекте
@router.callback_query(F.data == "foreman_tools")
async def show_foreman_tools(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    tools = user.object.tools
    if not tools:
        await callback.message.answer("🔧 На вашем объекте нет инструментов.")
        return
    text = "🔧 Инструменты на вашем объекте:\n"
    for tool in tools:
        text += f"• {tool.tool_name.name} (инв. №{tool.inventory_number}) — {tool.status.name}\n"
    await callback.message.answer(text)

# Просмотр и обработка заявок на инструменты
@router.callback_query(F.data == "foreman_requests")
async def show_foreman_requests(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    db = SessionLocal()
    try:
        requests = db.query(ToolRequest).filter(ToolRequest.from_object_id == user.object.id).all()
    finally:
        db.close()
    if not requests:
        await callback.message.answer("Нет заявок на передачу инструментов.")
        return
    for req in requests:
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Одобрить", callback_data=f"approve_req_{req.id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_req_{req.id}")
        await callback.message.answer(f"Заявка: {req.tool.tool_name.name} (инв. №{req.tool.inventory_number}) для {req.to_object.name}", reply_markup=builder.as_markup())

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
    await callback.message.answer("Заявка одобрена, инструмент передан!")

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
    await callback.message.answer("Заявка отклонена!")

# Инвентаризация: FSM для сбора фото QR-кодов
from aiogram.fsm.state import State, StatesGroup

class InventoryStates(StatesGroup):
    waiting_for_photos = State()
    confirm = State()

@router.callback_query(F.data == "start_inventory")
async def start_inventory(callback: CallbackQuery, state: FSMContext):
    await state.set_state(InventoryStates.waiting_for_photos)
    await callback.message.answer("Отправьте фотографии QR-кодов всех инструментов на объекте одним или несколькими сообщениями.")

@router.message(InventoryStates.waiting_for_photos)
async def receive_photos(message: Message, state: FSMContext):
    photos = (await state.get_data()).get("photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer("Фото получено. Отправьте ещё или нажмите 'Подтвердить'.", reply_markup=InlineKeyboardBuilder().button(text="Подтвердить", callback_data="confirm_inventory").as_markup())

@router.callback_query(F.data == "confirm_inventory")
async def confirm_inventory(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
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
    await callback.message.answer("Инвентаризация завершена! Вот XML для 1C:")
    await callback.message.answer(f"<pre>{xml_str}</pre>", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "object_workers")
async def show_object_workers(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    db = SessionLocal()
    try:
        workers = db.query(User).filter(User.object_id == user.object.id, User.role_id == 3).all()
    finally:
        db.close()
    if not workers:
        await callback.message.answer("На вашем объекте нет рабочих.")
        return
    text = "👷 Рабочие на объекте:\n"
    for w in workers:
        text += f"• {w.username} ({w.name or 'Без имени'})\n"
    await callback.message.answer(text) 