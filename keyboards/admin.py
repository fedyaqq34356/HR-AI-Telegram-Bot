from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

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
        KeyboardButton(text="📋 Логи")
    )
    builder.row(
        KeyboardButton(text="🚫 Запретные темы"),
        KeyboardButton(text="📥 Экспорт переписок")
    )
    return builder.as_markup(resize_keyboard=True)

def admin_panel_keyboard():
    return admin_main_menu()

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

def users_list_keyboard(users):
    builder = InlineKeyboardBuilder()
    for user in users[:20]:
        status_emoji = {
            'new': '🆕',
            'chatting': '💬',
            'pending_review': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'registered': '📝',
            'waiting_screenshot': '📸'
        }.get(user['status'], '❓')
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} @{user['username']} ({user['status']})",
                callback_data=f"view_conv_{user['user_id']}"
            )
        )
    return builder.as_markup()

def conversation_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="conversations")
    )
    return builder.as_markup()