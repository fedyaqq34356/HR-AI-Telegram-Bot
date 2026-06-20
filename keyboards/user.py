from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database import get_setting

async def groups_keyboard():
    training_link = await get_setting('training_group_link') or "https://t.me/+7crlJXEcRAk0YTUy"
    chat_link = await get_setting('chat_group_link') or "https://t.me/+GnKecVUalic2OTBi"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Группа с обучением", url=training_link)
    )
    builder.row(
        InlineKeyboardButton(text="Чат с девочками", url=chat_link)
    )
    return builder.as_markup()
