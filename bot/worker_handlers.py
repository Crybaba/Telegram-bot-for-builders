from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.user_service import UserService
from services.tool_request_service import ToolRequestService
from database.connection import get_db, SessionLocal
from database.models import User, Object, Tool, RequestStatus, Status
from aiogram import Bot
from services.inventory_check_service import InventoryCheckService
from sqlalchemy.orm import Session
from aiogram.fsm.state import State, StatesGroup
from bot.foreman_handlers import get_foreman_menu
from bot import handle_empty_data
from bot.foreman_handlers import send_notification_safely

router = Router()

# === Message Constants ===
MSG_NEED_USERNAME = "❌ Для регистрации необходимо установить username в настройках Telegram."
MSG_FOREMAN_MENU = "Меню бригадира:"
MSG_WELCOME_REGISTER = "👋 Добро пожаловать! Для продолжения регистрации нажмите кнопку ниже:"
MSG_CONTINUE_REGISTER = "👋 Для продолжения регистрации нажмите кнопку ниже:"
MSG_ALREADY_REGISTERED = "✅ Вы уже зарегистрированы!"
MSG_NO_OBJECT = "❌ Не удалось определить ваш объект."
MSG_NO_TOOLS = "🔧 На вашем объекте нет инструментов."
MSG_TOOLS_LIST = "🔧 Инструменты на вашем объекте:\n"
MSG_NO_OTHER_OBJECTS = "Нет других объектов для запроса инструментов."
MSG_SELECT_DONOR_OBJECT = "Выберите объект, с которого хотите запросить инструмент:"
MSG_OBJECT_NOT_FOUND = "❌ Объект не найден."
MSG_NO_TOOLS_ON_OBJECT = "На выбранном объекте нет доступных инструментов."
MSG_SELECT_TOOL = "Выберите инструмент для запроса:"
MSG_REQUEST_SENT = "Заявка на инструмент отправлена! Ожидайте решения."
MSG_ENTER_NAME = "Пожалуйста, введите ваше полное имя:"
MSG_NO_OBJECTS_FOR_REG = "Нет доступных объектов для регистрации. Обратитесь к администратору."
MSG_SELECT_OBJECT = "Выберите объект, на котором вы работаете:"
MSG_REG_ERROR = "❌ Ошибка регистрации. Попробуйте снова."
MSG_REG_SENT = "Спасибо, {name}! Ваша заявка на регистрацию отправлена бригадиру."
MSG_REG_CANCELLED = "Регистрация отменена."
MSG_REQUEST_STATUS = "Ваша заявка на инструмент '{tool_name}' {status}!"

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_object = State()

# Главное меню для рабочего
def get_worker_menu(foreman_username=None):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔧 Инструменты на объекте", callback_data="my_tools")
    builder.button(text="📦 Запросить инструмент", callback_data="request_tool")
    builder.adjust(1)
    return builder.as_markup()

# /start - регистрация
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    username = message.from_user.username
    if not username:
        await message.answer(MSG_NEED_USERNAME)
        return
    username = f"@{username}"
    user = UserService.get_user_by_username(username)
    if user and user.role and user.role.name == "прораб объекта":
        await message.answer(MSG_FOREMAN_MENU, reply_markup=get_foreman_menu())
        return
    if not user:
        UserService.create_user(username)
        await message.answer(
            MSG_WELCOME_REGISTER,
            reply_markup=InlineKeyboardBuilder().button(text="📝 Зарегистрироваться", callback_data="register").as_markup()
        )
        return
    if user.role.name == "в обработке" or not getattr(user, 'name', None) or not getattr(user, 'object', None):
        await message.answer(
            MSG_CONTINUE_REGISTER,
            reply_markup=InlineKeyboardBuilder().button(text="📝 Зарегистрироваться", callback_data="register").as_markup()
        )
        return
    # Получаем информацию о бригадире объекта
    db = SessionLocal()
    try:
        foreman = db.query(User).filter(
            User.object_id == user.object.id,
            User.role_id == 2  # 2 = "прораб объекта"
        ).first()
        foreman_username = foreman.username if foreman else None
    finally:
        db.close()
    
    # Формируем сообщение с информацией о бригадире
    menu_text = MSG_ALREADY_REGISTERED
    if foreman_username:
        menu_text += f"\n\n👷 Ваш бригадир: {foreman_username}"
    else:
        menu_text += f"\n\n👷 Бригадир не назначен"
    
    await message.answer(
        menu_text,
        reply_markup=get_worker_menu()
    )

# Просмотр инструментов на объекте
@router.callback_query(F.data == "my_tools")
async def show_my_tools(callback: CallbackQuery):
    username = callback.from_user.username
    if not username:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    username = f"@{username}"
    user = UserService.get_user_by_username(username)
    if not user or not getattr(user, 'object', None):
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
        await handle_empty_data(callback, MSG_NO_TOOLS, "back_to_menu")
        return
    text = MSG_TOOLS_LIST
    for tool in tools:
        text += f"• {tool.tool_name.name} (инв. №{tool.inventory_number}) — {tool.status.name}\n"
    if callback.message:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
    else:
        await callback.message.answer(text, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())

# Запросить инструмент с другого объекта
@router.callback_query(F.data == "request_tool")
async def request_tool(callback: CallbackQuery, state: FSMContext):
    username = callback.from_user.username
    if not username:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    username = f"@{username}"
    user = UserService.get_user_by_username(username)
    if not user or not getattr(user, 'object', None):
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    db = SessionLocal()
    try:
        objects = db.query(Object).filter(Object.id != user.object.id).all()
    finally:
        db.close()
    if not objects:
        await handle_empty_data(callback, MSG_NO_OTHER_OBJECTS, "back_to_menu")
        return
    builder = InlineKeyboardBuilder()
    for obj in objects:
        builder.button(text=f"🏗️ {obj.name}", callback_data=f"select_donor_{obj.id}")
    builder.button(text="🔙 Назад", callback_data="back_to_menu")
    builder.adjust(1)
    if callback.message:
        await callback.message.edit_text(MSG_SELECT_DONOR_OBJECT, reply_markup=builder.as_markup())
    else:
        await callback.message.answer(MSG_SELECT_DONOR_OBJECT, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("select_donor_"))
async def select_donor_object(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("select_donor_"):
        await callback.answer(MSG_OBJECT_NOT_FOUND, show_alert=True)
        return
    donor_object_id = int(data.removeprefix("select_donor_"))
    db = SessionLocal()
    try:
        donor_object = db.query(Object).filter(Object.id == donor_object_id).first()
        
        # Получаем статус "В наличии"
        available_status = db.query(Status).filter(Status.name == "В наличии").first()
        if not available_status:
            await callback.answer("❌ Статус 'В наличии' не найден в базе данных!", show_alert=True)
            return
        
        # Загружаем только инструменты со статусом "В наличии"
        tools = db.query(Tool).filter(
            Tool.current_object_id == donor_object_id,
            Tool.status_id == available_status.id
        ).all()
        
        # Предзагружаем связанные данные в текущей сессии
        tool_data = []
        for tool in tools:
            tool_name = tool.tool_name.name if tool.tool_name else "Неизвестный инструмент"
            inventory_number = tool.inventory_number or "Без номера"
            tool_data.append({
                'id': tool.id,
                'name': tool_name,
                'inventory_number': inventory_number
            })
    finally:
        db.close()
    
    if not donor_object:
        await callback.answer(MSG_OBJECT_NOT_FOUND, show_alert=True)
        return
    if not tool_data:
        await handle_empty_data(callback, MSG_NO_TOOLS_ON_OBJECT, "request_tool")
        return
    
    builder = InlineKeyboardBuilder()
    for tool in tool_data:
        builder.button(text=f"{tool['name']} (инв. №{tool['inventory_number']})", callback_data=f"request_tool_{tool['id']}_{donor_object_id}")
    builder.button(text="🔙 Назад", callback_data="request_tool")
    builder.adjust(1)
    if callback.message:
        await callback.message.edit_text(MSG_SELECT_TOOL, reply_markup=builder.as_markup())
    else:
        await callback.message.answer(MSG_SELECT_TOOL, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("request_tool_"))
async def confirm_tool_request(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("request_tool_"):
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    parts = data.split("_")
    if len(parts) < 4:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    tool_id = int(parts[2])
    from_object_id = int(parts[3])
    username = callback.from_user.username
    if not username:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    username = f"@{username}"
    user = UserService.get_user_by_username(username)
    if not user or not getattr(user, 'object', None):
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    # Корректно получаем int id
    user_id = user.id
    if hasattr(user_id, 'value'):
        user_id = user_id.value
    try:
        user_id_int = int(user_id)
    except Exception:
        user_id_int = None
    if user_id_int is None:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    ToolRequestService.create_request(
        tool_id=tool_id,
        requester_id=user_id_int,
        from_object_id=from_object_id,
        to_object_id=user.object.id
    )
    if callback.message:
        await callback.message.edit_text(MSG_REQUEST_SENT, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())
    else:
        await callback.message.answer(MSG_REQUEST_SENT, reply_markup=InlineKeyboardBuilder().button(text="🔙 Назад", callback_data="back_to_menu").as_markup())

# Уведомления о статусе заявки (пример функции для отправки уведомления)
async def notify_user_about_request(bot: Bot, user_id: int, status: str, tool_name: str):
    user = UserService.get_user_by_id(user_id)
    if not user:
        return
    username = getattr(user, 'username', None)
    if not username:
        return
    text = MSG_REQUEST_STATUS.format(tool_name=tool_name, status=status.lower())
    await send_notification_safely(bot, str(username), text)

@router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.answer(MSG_ENTER_NAME)

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    db = SessionLocal()
    try:
        objects = db.query(Object).all()
    finally:
        db.close()
    if not objects:
        await message.answer(MSG_NO_OBJECTS_FOR_REG)
        await state.clear()
        return
    builder = InlineKeyboardBuilder()
    for obj in objects:
        builder.button(text=f"🏗️ {obj.name}", callback_data=f"select_object_{obj.id}")
    builder.button(text="🔙 Отмена", callback_data="cancel_registration")
    builder.adjust(1)
    await state.set_state(RegistrationStates.waiting_for_object)
    await message.answer(MSG_SELECT_OBJECT, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("select_object_"), RegistrationStates.waiting_for_object)
async def process_object_selection(callback: CallbackQuery, state: FSMContext):
    data = callback.data or ""
    if not data.startswith("select_object_"):
        if callback.message:
            await callback.message.answer(MSG_REG_ERROR)
        await state.clear()
        return
    object_id = int(data.removeprefix("select_object_"))
    data_state = await state.get_data()
    name = data_state.get("name")
    username = callback.from_user.username
    if not name or not username:
        if callback.message:
            await callback.message.answer(MSG_REG_ERROR)
        await state.clear()
        return
    username = f"@{username}"
    user = UserService.get_user_by_username(username)
    if user:
        user_id = user.id
        if hasattr(user_id, 'value'):
            user_id = user_id.value
        try:
            user_id_int = int(user_id)
        except Exception:
            user_id_int = None
        if user_id_int is not None:
            UserService.update_user(user_id_int, name=name, object_id=object_id)
    if callback.message:
        await callback.message.answer(MSG_REG_SENT.format(name=name))
    await state.clear()

@router.callback_query(F.data == "cancel_registration", RegistrationStates.waiting_for_object)
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(MSG_REG_CANCELLED) 

# Обработчик кнопки "Назад" - возврат в главное меню
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    username = callback.from_user.username
    if not username:
        await callback.answer(MSG_NO_OBJECT, show_alert=True)
        return
    username = f"@{username}"
    user = UserService.get_user_by_username(username)
    if user and user.role and user.role.name == "прораб объекта":
        if callback.message:
            await callback.message.edit_text(MSG_FOREMAN_MENU, reply_markup=get_foreman_menu())
        else:
            await callback.message.answer(MSG_FOREMAN_MENU, reply_markup=get_foreman_menu())
    else:
        # Получаем информацию о бригадире объекта
        db = SessionLocal()
        try:
            foreman = db.query(User).filter(
                User.object_id == user.object.id,
                User.role_id == 2  # 2 = "прораб объекта"
            ).first()
            foreman_username = foreman.username if foreman else None
        finally:
            db.close()
        
        # Формируем сообщение с информацией о бригадире
        menu_text = MSG_ALREADY_REGISTERED
        if foreman_username:
            menu_text += f"\n\n👷 Ваш бригадир: {foreman_username}"
        else:
            menu_text += f"\n\n👷 Бригадир не назначен"
        
        if callback.message:
            await callback.message.edit_text(menu_text, reply_markup=get_worker_menu())
        else:
            await callback.message.answer(menu_text, reply_markup=get_worker_menu()) 