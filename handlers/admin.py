import logging
import json
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from states import AdminStates, UserStates
from keyboards import (
    admin_main_menu, users_list_keyboard, conversation_keyboard,
    forbidden_topics_keyboard, cancel_keyboard
)
from database import (
    get_setting, set_setting, save_ai_learning,
    get_pending_question, delete_pending_question, get_stats,
    get_user_conversations, get_all_users_list, get_user,
    get_forbidden_topics_from_db, add_forbidden_topic, delete_forbidden_topic,
    save_message, update_user_status
)

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    await message.answer("🔧 Админ-панель", reply_markup=admin_main_menu())

@router.message(F.text == "🔙 Отмена")
async def cancel_action(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=admin_main_menu())

@router.message(F.text == "📝 Изменить приветствие")
async def edit_welcome_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    await state.set_state(AdminStates.editing_welcome)
    await message.answer("Отправь новый текст приветствия:", reply_markup=cancel_keyboard())

@router.message(AdminStates.editing_welcome, F.text)
async def save_new_welcome(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.text in ["📝 Изменить приветствие", "📊 Статистика", "💬 Переписки", 
                         "✉️ Написать девушке", "📋 Логи", "🚫 Запретные темы", 
                         "📥 Экспорт переписок", "🔙 Отмена"]:
        await state.clear()
        if message.text == "🔙 Отмена":
            await message.answer("❌ Действие отменено", reply_markup=admin_main_menu())
        else:
            await message.answer("❌ Изменение приветствия отменено", reply_markup=admin_main_menu())
        return
    
    await set_setting('welcome_message', message.text)
    await message.answer("✅ Приветственное сообщение обновлено", reply_markup=admin_main_menu())
    await state.clear()
    logger.info("Welcome message updated by admin")

@router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    stats = await get_stats()
    
    ai_efficiency = 0
    if stats['admin_answers'] + stats['auto_answers'] > 0:
        ai_efficiency = round(stats['auto_answers'] / (stats['admin_answers'] + stats['auto_answers']) * 100)
    
    stats_text = f"""📊 Статистика бота:

👥 Всего пользователей: {stats['total']}
✅ Одобрено: {stats['approved']}
❌ Отказано: {stats['rejected']}
⏳ На рассмотрении: {stats['pending']}
📝 Зарегистрировано: {stats['registered']}

🤖 Эффективность ИИ:
▫️ Самостоятельных ответов: {stats['auto_answers']}
▫️ Ответов админа: {stats['admin_answers']}
▫️ Процент автономности: {ai_efficiency}%
▫️ Средний confidence: {stats['avg_confidence']}%"""
    
    await message.answer(stats_text, reply_markup=admin_main_menu())

@router.message(F.text == "💬 Переписки")
async def show_conversations_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    users = await get_all_users_list()
    
    logger.info(f"Loading conversations, found {len(users)} users")
    
    if not users:
        await message.answer("Пока нет пользователей", reply_markup=admin_main_menu())
        return
    
    try:
        keyboard = users_list_keyboard(users)
        await message.answer(
            "💬 Выберите пользователя для просмотра переписки:",
            reply_markup=keyboard
        )
        logger.info(f"Sent conversations menu with {len(users)} users")
    except Exception as e:
        logger.error(f"Error showing conversations menu: {e}", exc_info=True)
        await message.answer(f"Ошибка при загрузке списка: {e}", reply_markup=admin_main_menu())

@router.message(F.text == "✉️ Написать девушке")
async def write_to_user_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    users = await get_all_users_list()
    
    logger.info(f"Loading users for writing, found {len(users)} users")
    
    if not users:
        await message.answer("Пока нет пользователей", reply_markup=admin_main_menu())
        return
    
    try:
        keyboard = users_list_keyboard(users, action='write')
        await message.answer(
            "✉️ Выберите пользователя для отправки сообщения:",
            reply_markup=keyboard
        )
        logger.info(f"Sent write menu with {len(users)} users")
    except Exception as e:
        logger.error(f"Error showing write menu: {e}", exc_info=True)
        await message.answer(f"Ошибка при загрузке списка: {e}", reply_markup=admin_main_menu())

@router.message(F.text == "📋 Логи")
async def send_logs_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    try:
        log_file = FSInputFile('bot.log')
        await message.answer_document(
            log_file,
            caption="📋 Логи бота",
            reply_markup=admin_main_menu()
        )
    except FileNotFoundError:
        await message.answer("Файл логов не найден", reply_markup=admin_main_menu())
    except Exception as e:
        await message.answer(f"Ошибка при отправке логов: {e}", reply_markup=admin_main_menu())

@router.message(F.text == "🚫 Запретные темы")
async def show_forbidden_topics_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    topics = await get_forbidden_topics_from_db()
    
    if not topics:
        await message.answer(
            "Запретных тем пока нет",
            reply_markup=forbidden_topics_keyboard([])
        )
        return
    
    topics_text = "🚫 Запретные темы:\n\n"
    for topic in topics:
        keywords = json.loads(topic['keywords'])
        topics_text += f"• {topic['topic']}: {', '.join(keywords[:3])}...\n"
    
    await message.answer(
        topics_text,
        reply_markup=forbidden_topics_keyboard(topics)
    )

@router.message(F.text == "📥 Экспорт переписок")
async def export_conversations_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    try:
        users = await get_all_users_list()
        
        if not users:
            await message.answer("Нет пользователей для экспорта", reply_markup=admin_main_menu())
            return
        
        export_text = f"Экспорт переписок - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        export_text += "=" * 80 + "\n\n"
        
        for user in users:
            messages = await get_user_conversations(user['user_id'])
            
            if not messages:
                continue
            
            export_text += f"\n{'='*80}\n"
            export_text += f"Пользователь: @{user['username']}\n"
            export_text += f"Статус: {user['status']}\n"
            export_text += f"{'='*80}\n\n"
            
            for msg in messages:
                role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                export_text += f"{role_emoji} {msg['role']} [{msg['timestamp']}]:\n{msg['content']}\n\n"
        
        filename = f"conversations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(export_text)
        
        export_file = FSInputFile(filename)
        await message.answer_document(
            export_file,
            caption="📥 Экспорт всех переписок",
            reply_markup=admin_main_menu()
        )
        
        import os
        os.remove(filename)
        
        logger.info("Admin exported conversations")
        
    except Exception as e:
        await message.answer(f"Ошибка при экспорте: {e}", reply_markup=admin_main_menu())
        logger.error(f"Export error: {e}")

@router.callback_query(F.data.startswith("answer_"))
async def admin_answer_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    user_id = int(callback.data.split("_")[1])
    
    logger.info(f"Admin clicked answer button for user {user_id}")
    await state.update_data(answering_user_id=user_id)
    await state.set_state(AdminStates.answering_question)
    logger.info(f"State set to answering_question for admin, target user: {user_id}")
    
    await callback.message.answer(
        f"Напиши ответ для пользователя {user_id} или перешли сообщение/файл:",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("write_"))
async def admin_write_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    user_id = int(callback.data.split("_")[1])
    
    logger.info(f"Admin wants to write to user {user_id}")
    await state.update_data(writing_user_id=user_id)
    await state.set_state(AdminStates.answering_question)
    
    user = await get_user(user_id)
    user_display = f"@{user['username']}" if user['username'] else user_id
    
    await callback.message.answer(
        f"Напиши сообщение для {user_display} или перешли контент:",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()

@router.message(AdminStates.answering_question)
async def admin_answer_any(message: Message, state: FSMContext, bot):
    from aiogram.fsm.storage.base import StorageKey
    
    if message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin user {message.from_user.id} tried to answer question")
        return
    
    if message.text in ["📝 Изменить приветствие", "📊 Статистика", "💬 Переписки", 
                         "✉️ Написать девушке", "📋 Логи", "🚫 Запретные темы", 
                         "📥 Экспорт переписок", "🔙 Отмена"]:
        await state.clear()
        if message.text == "🔙 Отмена":
            await message.answer("❌ Действие отменено", reply_markup=admin_main_menu())
        else:
            await message.answer("❌ Отправка сообщения отменена", reply_markup=admin_main_menu())
        return
    
    logger.info(f"Admin is sending response")
    data = await state.get_data()
    user_id = data.get('answering_user_id') or data.get('writing_user_id')
    logger.info(f"Target user_id from state: {user_id}")
    
    if not user_id:
        await message.answer("❌ Ошибка: не найден пользователь для ответа", reply_markup=admin_main_menu())
        await state.clear()
        return
    
    question = await get_pending_question(user_id)
    
    try:
        if message.text:
            answer = message.text
            await bot.send_message(user_id, answer)
            await save_message(user_id, 'bot', answer)
            
            if question:
                await save_ai_learning(question, answer, 'admin', 100)
                await delete_pending_question(user_id)
                logger.info(f"Admin answered question for user {user_id}")
        
        elif message.photo:
            caption = message.caption if message.caption else ""
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=caption)
            if caption:
                await save_message(user_id, 'bot', f"[Фото] {caption}")
            logger.info(f"Admin sent photo to user {user_id}")
        
        elif message.document:
            caption = message.caption if message.caption else ""
            await bot.send_document(user_id, message.document.file_id, caption=caption)
            if caption:
                await save_message(user_id, 'bot', f"[Документ] {caption}")
            logger.info(f"Admin sent document to user {user_id}")
        
        elif message.video:
            caption = message.caption if message.caption else ""
            await bot.send_video(user_id, message.video.file_id, caption=caption)
            if caption:
                await save_message(user_id, 'bot', f"[Видео] {caption}")
            logger.info(f"Admin sent video to user {user_id}")
        
        elif message.audio:
            caption = message.caption if message.caption else ""
            await bot.send_audio(user_id, message.audio.file_id, caption=caption)
            if caption:
                await save_message(user_id, 'bot', f"[Аудио] {caption}")
            logger.info(f"Admin sent audio to user {user_id}")
        
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id)
            logger.info(f"Admin sent voice to user {user_id}")
        
        elif message.video_note:
            await bot.send_video_note(user_id, message.video_note.file_id)
            logger.info(f"Admin sent video note to user {user_id}")
        
        else:
            await message.answer("❌ Неподдерживаемый тип сообщения", reply_markup=admin_main_menu())
            await state.clear()
            return
        
        user = await get_user(user_id)
        
        user_state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        user_state = FSMContext(storage=state.storage, key=user_state_key)
        
        if user['status'] in ['registered', 'waiting_screenshot', 'helping_registration']:
            await update_user_status(user_id, 'registered')
            await user_state.set_state(UserStates.registered)
        else:
            await update_user_status(user_id, 'chatting')
            await user_state.set_state(UserStates.chatting)
        
        await message.answer("✅ Сообщение отправлено пользователю", reply_markup=admin_main_menu())
        logger.info(f"Admin successfully sent message to user {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}", reply_markup=admin_main_menu())
        logger.error(f"Error sending admin message to user {user_id}: {e}")
    
    await state.clear()

@router.callback_query(F.data.startswith("view_conv_"))
async def view_conversation(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    try:
        user_id = int(callback.data.split("_")[2])
        logger.info(f"Admin viewing conversation for user {user_id}")
    except Exception as e:
        logger.error(f"Error parsing user_id from callback: {e}")
        await callback.answer("Ошибка при обработке")
        return
    
    try:
        messages = await get_user_conversations(user_id)
        user = await get_user(user_id)
        
        if not user:
            await callback.message.answer("Пользователь не найден")
            await callback.answer()
            return
        
        logger.info(f"Found {len(messages)} messages for user {user_id}")
        
        if not messages:
            username_display = f"@{user['username']}" if user['username'] else f"ID{user_id}"
            await callback.message.answer(
                f"У пользователя {username_display} пока нет сообщений",
                reply_markup=conversation_keyboard(user_id)
            )
            await callback.answer()
            return
        
        username_display = f"@{user['username']}" if user['username'] else f"ID{user_id}"
        conv_text = f"💬 Переписка с {username_display} (статус: {user['status']}):\n\n"
        
        for msg in messages[-20:]:
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            content_preview = msg['content'][:100] if msg['content'] else ""
            conv_text += f"{role_emoji} {msg['role']}: {content_preview}\n\n"
        
        if len(conv_text) > 4000:
            conv_text = conv_text[:4000] + "...\n\n(показаны последние сообщения)"
        
        await callback.message.answer(
            conv_text,
            reply_markup=conversation_keyboard(user_id)
        )
        await callback.answer()
        logger.info(f"Sent conversation for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error viewing conversation for user {user_id}: {e}", exc_info=True)
        await callback.message.answer(f"Ошибка при загрузке переписки: {e}")
        await callback.answer()

@router.callback_query(F.data == "conversations")
async def back_to_conversations(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    users = await get_all_users_list()
    
    if not users:
        await callback.message.answer("Пока нет пользователей")
        await callback.answer()
        return
    
    await callback.message.answer(
        "💬 Выберите пользователя для просмотра переписки:",
        reply_markup=users_list_keyboard(users)
    )
    await callback.answer()

@router.callback_query(F.data == "add_forbidden_topic")
async def add_forbidden_topic_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    await state.set_state(AdminStates.adding_forbidden_topic)
    
    await callback.message.answer(
        "Введите название запретной темы (например: политика, религия):",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()

@router.message(AdminStates.adding_forbidden_topic, F.text)
async def add_forbidden_topic_name(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.text in ["📝 Изменить приветствие", "📊 Статистика", "💬 Переписки", 
                         "✉️ Написать девушке", "📋 Логи", "🚫 Запретные темы", 
                         "📥 Экспорт переписок", "🔙 Отмена"]:
        await state.clear()
        if message.text == "🔙 Отмена":
            await message.answer("❌ Действие отменено", reply_markup=admin_main_menu())
        else:
            await message.answer("❌ Добавление темы отменено", reply_markup=admin_main_menu())
        return
    
    await state.update_data(topic_name=message.text)
    await state.set_state(AdminStates.adding_forbidden_keywords)
    
    await message.answer(
        "Введите ключевые слова через запятую (например: война, выборы, президент):",
        reply_markup=cancel_keyboard()
    )

@router.message(AdminStates.adding_forbidden_keywords, F.text)
async def add_forbidden_topic_keywords(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.text in ["📝 Изменить приветствие", "📊 Статистика", "💬 Переписки", 
                         "✉️ Написать девушке", "📋 Логи", "🚫 Запретные темы", 
                         "📥 Экспорт переписок", "🔙 Отмена"]:
        await state.clear()
        if message.text == "🔙 Отмена":
            await message.answer("❌ Действие отменено", reply_markup=admin_main_menu())
        else:
            await message.answer("❌ Добавление темы отменено", reply_markup=admin_main_menu())
        return
    
    data = await state.get_data()
    topic_name = data.get('topic_name')
    
    keywords = [k.strip() for k in message.text.split(',')]
    keywords_json = json.dumps(keywords)
    
    await add_forbidden_topic(topic_name, keywords_json)
    
    await message.answer(
        f"✅ Запретная тема '{topic_name}' добавлена с ключевыми словами: {', '.join(keywords)}",
        reply_markup=admin_main_menu()
    )
    await state.clear()
    logger.info(f"Admin added forbidden topic: {topic_name}")

@router.callback_query(F.data.startswith("delete_topic_"))
async def delete_forbidden_topic_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    
    await state.clear()
    
    topic_id = int(callback.data.split("_")[2])
    
    await delete_forbidden_topic(topic_id)
    
    topics = await get_forbidden_topics_from_db()
    
    await callback.message.edit_text(
        "🚫 Запретные темы (обновлено):",
        reply_markup=forbidden_topics_keyboard(topics)
    )
    await callback.answer("Тема удалена")
    logger.info(f"Admin deleted forbidden topic: {topic_id}")