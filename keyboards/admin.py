from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from database.users import has_bot_responded

def admin_review_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{user_id}")
    )
    return builder.as_markup()

def admin_answer_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Ответить", callback_data=f"answer_{user_id}")
    )
    return builder.as_markup()

def admin_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Изменить приветствие"),
        KeyboardButton(text="📊 Статистика")
    )
    builder.row(
        KeyboardButton(text="💬 Переписки"),
        KeyboardButton(text="✉️ Написать девушке")
    )
    builder.row(
        KeyboardButton(text="🔗 Ссылки на группы"),
        KeyboardButton(text="📋 Логи")
    )
    builder.row(
        KeyboardButton(text="🚫 Запретные темы"),
        KeyboardButton(text="📥 Экспорт переписок")
    )
    return builder.as_markup(resize_keyboard=True)

def admin_panel_keyboard():
    return admin_main_menu()

def cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔙 Отмена"))
    return builder.as_markup(resize_keyboard=True)

def group_links_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 Группа с обучением", callback_data="edit_training_link")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Чат с девочками", callback_data="edit_chat_link")
    )
    return builder.as_markup()

def forbidden_topics_keyboard(topics):
    builder = InlineKeyboardBuilder()
    for topic in topics:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {topic['topic']}",
                callback_data=f"delete_topic_{topic['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить тему", callback_data="add_forbidden_topic")
    )
    return builder.as_markup()

def conversations_action_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁 Посмотреть переписки", callback_data="view_conversations")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить переписки", callback_data="delete_conversations_menu")
    )
    return builder.as_markup()

async def users_list_keyboard(users, action='view', page=1, total_pages=1):
    builder = InlineKeyboardBuilder()

    status_emojis = {
        'new': '🆕',
        'chatting': '💬',
        'pending_review': '⏳',
        'approved': '✅',
        'rejected': '❌',
        'registered': '📝',
        'waiting_screenshot': '📸',
        'helping_registration': '📋',
        'waiting_admin': '⏳',
    }

    for user in users:
        status_emoji = status_emojis.get(user['status'], '❓')
        bot_responded = await has_bot_responded(user['user_id'])
        bot_indicator = ' 🔵' if bot_responded else ''

        username_display = f"@{user['username']}" if user['username'] else f"User {user['user_id']}"

        callback_prefix = 'write' if action == 'write' else 'view_conv' if action == 'view' else 'delete_conv'

        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji}{bot_indicator} {username_display}",
                callback_data=f"{callback_prefix}_{user['user_id']}"
            )
        )
    
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{action}_{page-1}")
        )
    if page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page_{action}_{page+1}")
        )
    
    if navigation_buttons:
        builder.row(*navigation_buttons)
    
    builder.row(
        InlineKeyboardButton(text="◀️ К меню", callback_data="conversations_menu")
    )
    
    return builder.as_markup()

def conversation_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Скрыть из списка", callback_data=f"hide_user_{user_id}"),
        InlineKeyboardButton(text="◀️ К списку", callback_data="view_conversations")
    )
    return builder.as_markup()

def delete_conversation_confirm_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{user_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="delete_conversations_menu")
    )
    return builder.as_markup()