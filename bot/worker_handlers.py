from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.user_service import UserService
from services.tool_request_service import ToolRequestService
from database.connection import get_db, SessionLocal
from database.models import User, Object, Tool, RequestStatus
from aiogram import Bot
from services.inventory_check_service import InventoryCheckService
from sqlalchemy.orm import Session
from aiogram.fsm.state import State, StatesGroup
from bot.foreman_handlers import get_foreman_menu

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_object = State()

# Главное меню для рабочего
def get_worker_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔧 Инструменты на объекте", callback_data="my_tools")
    builder.button(text="📦 Запросить инструмент", callback_data="request_tool")
    builder.adjust(1)
    return builder.as_markup()

# /start - регистрация
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    username = f"@{message.from_user.username}" if message.from_user.username else None
    if not username:
        await message.answer(
            "❌ Для регистрации необходимо установить username в настройках Telegram."
        )
        return
    user = UserService.get_user_by_username(username)
    if user and user.role and user.role.name == "прораб объекта":
        await message.answer("Меню бригадира:", reply_markup=get_foreman_menu())
        return
    if not user:
        UserService.create_user(username)
        await message.answer(
            "👋 Добро пожаловать! Для продолжения регистрации нажмите кнопку ниже:",
            reply_markup=InlineKeyboardBuilder().button(text="📝 Зарегистрироваться", callback_data="register").as_markup()
        )
        return
    if user.role.name == "в обработке" or not user.name or not user.object:
        await message.answer(
            "👋 Для продолжения регистрации нажмите кнопку ниже:",
            reply_markup=InlineKeyboardBuilder().button(text="📝 Зарегистрироваться", callback_data="register").as_markup()
        )
        return
    await message.answer(
        "✅ Вы уже зарегистрированы!",
        reply_markup=get_worker_menu()
    )

# Просмотр инструментов на объекте
@router.callback_query(F.data == "my_tools")
async def show_my_tools(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    tools = user.object.tools
    if not tools:
        await callback.message.edit_text("🔧 На вашем объекте нет инструментов.")
        return
    text = "🔧 Инструменты на вашем объекте:\n"
    for tool in tools:
        text += f"• {tool.tool_name.name} (инв. №{tool.inventory_number}) — {tool.status.name}\n"
    await callback.message.edit_text(text)

# Запросить инструмент с другого объекта
@router.callback_query(F.data == "request_tool")
async def request_tool(callback: CallbackQuery, state: FSMContext):
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    # Получаем все объекты, кроме своего
    db = SessionLocal()
    try:
        objects = db.query(Object).filter(Object.id != user.object.id).all()
    finally:
        db.close()
    if not objects:
        await callback.message.answer("Нет других объектов для запроса инструментов.")
        return
    builder = InlineKeyboardBuilder()
    for obj in objects:
        builder.button(text=f"🏗️ {obj.name}", callback_data=f"select_donor_{obj.id}")
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    builder.adjust(1)
    await callback.message.answer("Выберите объект, с которого хотите запросить инструмент:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("select_donor_"))
async def select_donor_object(callback: CallbackQuery, state: FSMContext):
    donor_object_id = int(callback.data.removeprefix("select_donor_"))
    db = SessionLocal()
    try:
        donor_object = db.query(Object).filter(Object.id == donor_object_id).first()
        tools = db.query(Tool).filter(Tool.current_object_id == donor_object_id).all()
    finally:
        db.close()
    if not donor_object:
        await callback.answer("❌ Объект не найден.", show_alert=True)
        return
    if not tools:
        await callback.message.answer("На выбранном объекте нет доступных инструментов.")
        return
    builder = InlineKeyboardBuilder()
    for tool in tools:
        builder.button(text=f"{tool.tool_name_id} (инв. №{tool.inventory_number})", callback_data=f"request_tool_{tool.id}_{donor_object_id}")
    builder.button(text="🔙 Назад", callback_data="request_tool")
    builder.adjust(1)
    await callback.message.answer("Выберите инструмент для запроса:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("request_tool_"))
async def confirm_tool_request(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    tool_id = int(parts[2])
    from_object_id = int(parts[3])
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    user = UserService.get_user_by_username(username)
    if not user or not user.object:
        await callback.answer("❌ Не удалось определить ваш объект.", show_alert=True)
        return
    ToolRequestService.create_request(
        tool_id=tool_id,
        requester_id=user.id,
        from_object_id=from_object_id,
        to_object_id=user.object.id
    )
    await callback.message.answer("Заявка на инструмент отправлена! Ожидайте решения.")

# Уведомления о статусе заявки (пример функции для отправки уведомления)
async def notify_user_about_request(bot: Bot, user_id: int, status: str, tool_name: str):
    user = UserService.get_user_by_id(user_id)
    if not user:
        return
    username = user.username
    text = f"Ваша заявка на инструмент '{tool_name}' {status.lower()}!"
    try:
        await bot.send_message(username, text)
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")

@router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.answer("Пожалуйста, введите ваше полное имя:")

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    db = SessionLocal()
    try:
        objects = db.query(Object).all()
    finally:
        db.close()
    if not objects:
        await message.answer("Нет доступных объектов для регистрации. Обратитесь к администратору.")
        await state.clear()
        return
    builder = InlineKeyboardBuilder()
    for obj in objects:
        builder.button(text=f"🏗️ {obj.name}", callback_data=f"select_object_{obj.id}")
    builder.button(text="🔙 Отмена", callback_data="cancel_registration")
    builder.adjust(1)
    await state.set_state(RegistrationStates.waiting_for_object)
    await message.answer("Выберите объект, на котором вы работаете:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("select_object_"), RegistrationStates.waiting_for_object)
async def process_object_selection(callback: CallbackQuery, state: FSMContext):
    object_id = int(callback.data.removeprefix("select_object_"))
    data = await state.get_data()
    name = data.get("name")
    username = f"@{callback.from_user.username}" if callback.from_user.username else None
    if not name or not username:
        await callback.answer("❌ Ошибка регистрации. Попробуйте снова.", show_alert=True)
        await state.clear()
        return
    user = UserService.get_user_by_username(username)
    if user:
        UserService.update_user(user.id, name=name, object_id=object_id)
    await callback.message.answer(f"Спасибо, {name}! Ваша заявка на регистрацию отправлена бригадиру.")
    await state.clear()

@router.callback_query(F.data == "cancel_registration", RegistrationStates.waiting_for_object)
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Регистрация отменена.") 