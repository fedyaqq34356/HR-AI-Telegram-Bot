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
    forbidden_topics_keyboard
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
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer("🔧 Админ-панель", reply_markup=admin_main_menu())

@router.message(F.text == "📝 Изменить приветствие")
async def edit_welcome_menu(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.set_state(AdminStates.editing_welcome)
    await message.answer("Отправь новый текст приветствия:")

@router.message(AdminStates.editing_welcome, F.text)
async def save_new_welcome(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await set_setting('welcome_message', message.text)
    await message.answer("✅ Приветственное сообщение обновлено", reply_markup=admin_main_menu())
    await state.clear()
    logger.info("Welcome message updated by admin")

@router.message(F.text == "📊 Статистика")
async def show_stats_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
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
async def show_conversations_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    users = await get_all_users_list()
    
    if not users:
        await message.answer("Пока нет пользователей", reply_markup=admin_main_menu())
        return
    
    await message.answer(
        "💬 Выберите пользователя для просмотра переписки:",
        reply_markup=users_list_keyboard(users)
    )

@router.message(F.text == "📋 Логи")
async def send_logs_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
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
async def show_forbidden_topics_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
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
async def export_conversations_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
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
    
    user_id = int(callback.data.split("_")[1])
    
    logger.info(f"Admin clicked answer button for user {user_id}")
    await state.update_data(answering_user_id=user_id)
    await state.set_state(AdminStates.answering_question)
    logger.info(f"State set to answering_question for admin, target user: {user_id}")
    
    await callback.message.answer(f"Напиши ответ для пользователя {user_id}:")
    await callback.answer()

@router.message(AdminStates.answering_question, F.text)
async def admin_answer_text(message: Message, state: FSMContext, bot):
    from aiogram.fsm.storage.base import StorageKey
    
    if message.from_user.id != ADMIN_ID:
        logger.warning(f"Non-admin user {message.from_user.id} tried to answer question")
        return
    
    logger.info(f"Admin is answering a question, message: {message.text}")
    data = await state.get_data()
    user_id = data.get('answering_user_id')
    logger.info(f"Answering user_id from state: {user_id}")
    answer = message.text
    
    question = await get_pending_question(user_id)
    if question:
        await save_ai_learning(question, answer, 'admin', 100)
        await delete_pending_question(user_id)
        logger.info(f"Admin answered question for user {user_id}")
    
    try:
        await bot.send_message(user_id, answer)
        await save_message(user_id, 'bot', answer)
        
        user = await get_user(user_id)
        
        user_state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        user_state = FSMContext(storage=state.storage, key=user_state_key)
        
        if user['status'] in ['registered', 'waiting_screenshot']:
            await update_user_status(user_id, 'registered')
            await user_state.set_state(UserStates.registered)
        else:
            await update_user_status(user_id, 'chatting')
            await user_state.set_state(UserStates.chatting)
        
        await message.answer("✅ Ответ отправлен пользователю", reply_markup=admin_main_menu())
        logger.info(f"Admin successfully sent answer to user {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}", reply_markup=admin_main_menu())
        logger.error(f"Error sending admin answer to user {user_id}: {e}")
    
    await state.clear()

@router.callback_query(F.data.startswith("view_conv_"))
async def view_conversation(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    user_id = int(callback.data.split("_")[2])
    
    messages = await get_user_conversations(user_id)
    user = await get_user(user_id)
    
    if not messages:
        await callback.message.answer(
            f"У пользователя @{user['username']} пока нет сообщений",
            reply_markup=conversation_keyboard(user_id)
        )
        await callback.answer()
        return
    
    conv_text = f"💬 Переписка с @{user['username']} (статус: {user['status']}):\n\n"
    
    for msg in messages[-20:]:
        role_emoji = "👤" if msg['role'] == 'user' else "🤖"
        conv_text += f"{role_emoji} {msg['role']}: {msg['content'][:100]}\n\n"
    
    if len(conv_text) > 4000:
        conv_text = conv_text[:4000] + "...\n\n(показаны последние сообщения)"
    
    await callback.message.answer(
        conv_text,
        reply_markup=conversation_keyboard(user_id)
    )
    await callback.answer()

@router.callback_query(F.data == "conversations")
async def back_to_conversations(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
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
    
    await state.set_state(AdminStates.adding_forbidden_topic)
    await callback.message.answer("Введите название запретной темы (например: политика, религия):")
    await callback.answer()

@router.message(AdminStates.adding_forbidden_topic, F.text)
async def add_forbidden_topic_name(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await state.update_data(topic_name=message.text)
    await state.set_state(AdminStates.adding_forbidden_keywords)
    await message.answer("Введите ключевые слова через запятую (например: война, выборы, президент):")

@router.message(AdminStates.adding_forbidden_keywords, F.text)
async def add_forbidden_topic_keywords(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
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
async def delete_forbidden_topic_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    topic_id = int(callback.data.split("_")[2])
    
    await delete_forbidden_topic(topic_id)
    
    topics = await get_forbidden_topics_from_db()
    
    await callback.message.edit_text(
        "🚫 Запретные темы (обновлено):",
        reply_markup=forbidden_topics_keyboard(topics)
    )
    await callback.answer("Тема удалена")
    logger.info(f"Admin deleted forbidden topic: {topic_id}")