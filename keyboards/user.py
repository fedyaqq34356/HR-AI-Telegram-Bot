from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def groups_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Группа с обучением", url="https://t.me/+7crlJXEcRAk0YTUy")
    )
    builder.row(
        InlineKeyboardButton(text="Чат с девочками", url="https://t.me/+GnKecVUalic2OTBi")
    )
    return builder.as_markup()