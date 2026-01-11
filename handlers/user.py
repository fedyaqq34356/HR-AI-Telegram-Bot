import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID, PHOTOS_MIN, PHOTOS_MAX, AI_CONFIDENCE_THRESHOLD, GROUP_ID
from states import UserStates
from keyboards import admin_answer_keyboard
from database import (
    get_user, create_user, update_user_status, save_message,
    save_photo, get_setting, save_ai_learning, save_pending_question,
    is_user_in_groups, add_user_to_groups
)
from utils.ai_handler import get_ai_response_with_retry
from handlers.reviews import is_review_request, send_reviews

router = Router()
logger = logging.getLogger(__name__)

photo_group_cache = {}

async def is_user_rejected(user_id):
    user = await get_user(user_id)
    return user and user['status'] == 'rejected'

def get_user_display_name(user_data):
    if user_data.get('username'):
        return f"@{user_data['username']}"
    return user_data.get('first_name', f"User {user_data['user_id']}")

async def check_group_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(GROUP_ID, user_id)
        in_group = member.status in ['member', 'administrator', 'creator']
        
        if in_group:
            await add_user_to_groups(user_id)
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking group membership for user {user_id}: {e}")
        return False

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        logger.info(f"Admin {user_id} tried to use /start, redirecting to /admin")
        from keyboards import admin_main_menu
        await message.answer("👋 Привет, администратор!\n\nИспользуй команду /admin для доступа к панели управления", reply_markup=admin_main_menu())
        return
    
    username = message.from_user.username or f"user_{user_id}"
    user = await get_user(user_id)
    
    is_in_group = await check_group_membership(bot, user_id)
    
    if user and user['status'] == 'rejected':
        logger.info(f"Rejected user {user_id} tried to start bot")
        return
    
    if not user:
        await create_user(user_id, username)
        
        if is_in_group:
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            await message.answer("Привет! Вижу ты уже с нами в группе 😊\nЧем могу помочь?")
            logger.info(f"Existing group member {user_id} started bot")
        else:
            await update_user_status(user_id, 'chatting')
            await state.set_state(UserStates.chatting)
            welcome_msg = await get_setting('welcome_message')
            await message.answer(welcome_msg)
            logger.info(f"New user {user_id} (@{username}) started bot")
    else:
        if is_in_group and user['status'] not in ['registered', 'approved']:
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            await message.answer("С возвращением! Вижу ты присоединилась к группе 😊")
        else:
            await message.answer("С возвращением! Чем могу помочь? 😊")
            status_to_state = {
                'chatting': UserStates.chatting,
                'asking_work_hours': UserStates.asking_work_hours,
                'asking_experience': UserStates.asking_experience,
                'pending_review': UserStates.pending_review,
                'waiting_screenshot': UserStates.waiting_screenshot,
                'registered': UserStates.registered,
                'helping_registration': UserStates.helping_registration,
                'waiting_admin': UserStates.waiting_admin,
            }
            new_state = status_to_state.get(user['status'], UserStates.chatting)
            await state.set_state(new_state)

@router.message(UserStates.chatting, F.photo)
async def handle_photo_in_chatting(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    user = await get_user(user_id)
    photos_count = user['photos_count']
    
    if photos_count >= PHOTOS_MAX:
        await message.answer(f"Максимум {PHOTOS_MAX} фото! У тебя уже загружено достаточно 👍")
        logger.info(f"User {user_id} tried to send more than {PHOTOS_MAX} photos")
        return
    
    media_group_id = message.media_group_id
    
    if media_group_id:
        if media_group_id not in photo_group_cache:
            photo_group_cache[media_group_id] = {
                'photos': [],
                'processed': False
            }
        
        if not photo_group_cache[media_group_id]['processed']:
            photo_group_cache[media_group_id]['photos'].append(message.photo[-1].file_id)
            logger.info(f"Added photo to group {media_group_id}, total: {len(photo_group_cache[media_group_id]['photos'])}")
            
            await asyncio.sleep(1.0)
            
            if media_group_id in photo_group_cache and not photo_group_cache[media_group_id]['processed']:
                photos_in_group = photo_group_cache[media_group_id]['photos']
                photo_group_cache[media_group_id]['processed'] = True
                
                current_count = (await get_user(user_id))['photos_count']
                total_photos = current_count + len(photos_in_group)
                
                if total_photos > PHOTOS_MAX:
                    await message.answer(f"Можно загрузить максимум {PHOTOS_MAX} фото! Отправь не больше {PHOTOS_MAX - current_count} фото.")
                    del photo_group_cache[media_group_id]
                    return
                
                for file_id in photos_in_group:
                    await save_photo(user_id, file_id)
                    logger.info(f"Saved photo for user {user_id}")
                
                del photo_group_cache[media_group_id]
                
                user = await get_user(user_id)
                photos_count = user['photos_count']
                
                if photos_count < PHOTOS_MIN:
                    remaining = PHOTOS_MIN - photos_count
                    await message.answer(f"Отлично! Нужно ещё минимум {remaining} фото 📸")
                elif photos_count >= PHOTOS_MIN:
                    await update_user_status(user_id, 'asking_work_hours')
                    await state.set_state(UserStates.asking_work_hours)
                    await message.answer("Отлично! Теперь несколько вопросов:\n\n1️⃣ Сколько времени в день ты готова уделять нашему приложению?\n(Ответь в свободной форме)")
                    logger.info(f"User {user_id} uploaded {photos_count} photos, moving to work hours question")
    else:
        file_id = message.photo[-1].file_id
        await save_photo(user_id, file_id)
        photos_count += 1
        logger.info(f"Saved single photo for user {user_id}, new count: {photos_count}")
        
        if photos_count < PHOTOS_MIN:
            remaining = PHOTOS_MIN - photos_count
            await message.answer(f"Отлично! Нужно ещё минимум {remaining} фото 📸")
        elif photos_count >= PHOTOS_MIN:
            await update_user_status(user_id, 'asking_work_hours')
            await state.set_state(UserStates.asking_work_hours)
            await message.answer("Отлично! Теперь несколько вопросов:\n\n1️⃣ Сколько времени в день ты готова уделять нашему приложению?\n(Ответь в свободной форме)")
            logger.info(f"User {user_id} uploaded {photos_count} photos, moving to work hours question")

@router.message(UserStates.asking_work_hours, F.text)
async def handle_work_hours(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return
    
    if await is_user_rejected(message.from_user.id):
        return
    
    await state.update_data(work_hours=message.text)
    await update_user_status(message.from_user.id, 'asking_experience')
    await state.set_state(UserStates.asking_experience)
    await message.answer("2️⃣ Был ли у тебя опыт работы в похожих приложениях или платформах?\n(Если да — опиши кратко. Если нет — так и напиши)")

@router.message(UserStates.asking_experience, F.text)
async def handle_experience(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    from database import create_application, get_photos
    
    data = await state.get_data()
    work_hours = data.get('work_hours')
    experience = message.text
    
    await create_application(user_id, work_hours, experience)
    await update_user_status(user_id, 'pending_review')
    await state.set_state(UserStates.pending_review)
    
    user = await get_user(user_id)
    photos = await get_photos(user_id)
    
    user_display = get_user_display_name({
        'username': user['username'],
        'first_name': message.from_user.first_name,
        'user_id': user_id
    })
    
    username = user['username']
    user_link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
    
    card_text = f"👤 {user_display}\n"
    card_text += f"🔗 {user_link}\n\n"
    card_text += f"⏰ Время: {work_hours}\n"
    card_text += f"💼 Опыт: {experience}\n\n"
    
    await bot.send_message(ADMIN_ID, card_text)
    
    from aiogram.types import InputMediaPhoto
    media_group = [InputMediaPhoto(media=photo['file_id']) for photo in photos]
    
    if media_group:
        await bot.send_media_group(ADMIN_ID, media=media_group)
    
    from keyboards import admin_review_keyboard
    await bot.send_message(
        ADMIN_ID,
        f"Принять решение по {user_display}:",
        reply_markup=admin_review_keyboard(user_id)
    )
    
    await message.answer("Спасибо! Твоя заявка отправлена на рассмотрение 😊")
    logger.info(f"Application submitted for user {user_id}")

@router.message(UserStates.helping_registration, F.text)
async def handle_registration_questions(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    question = message.text
    
    if is_review_request(question):
        await send_reviews(message)
        return
    
    await save_message(user_id, 'user', question)
    logger.info(f"Registration question from user {user_id}: {question[:50]}...")
    
    await bot.send_chat_action(user_id, "typing")
    
    import time
    start_time = time.time()
    
    ai_result = await get_ai_response_with_retry(user_id, question)
    
    elapsed = time.time() - start_time
    if elapsed < 1:
        await asyncio.sleep(1 - elapsed)
    
    if ai_result['escalate'] or ai_result['confidence'] < AI_CONFIDENCE_THRESHOLD:
        await save_pending_question(user_id, question)
        
        user = await get_user(user_id)
        user_display = get_user_display_name({
            'username': user['username'],
            'first_name': message.from_user.first_name,
            'user_id': user_id
        })
        
        await bot.send_message(
            ADMIN_ID,
            f"❓ Вопрос о регистрации от {user_display}:\n\n{question}",
            reply_markup=admin_answer_keyboard(user_id)
        )
        
        await message.answer("Передаю твой вопрос менеджеру, скоро получишь ответ! 😊")
        logger.info(f"Registration question escalated to admin for user {user_id}")
    else:
        answer = ai_result['answer']
        await message.answer(answer)
        await save_message(user_id, 'bot', answer)
        await save_ai_learning(question, answer, 'auto', ai_result['confidence'])
        logger.info(f"Auto-answered registration question for user {user_id} with confidence {ai_result['confidence']}")

@router.message(UserStates.helping_registration, F.photo)
async def handle_photo_during_registration(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    logger.info(f"User {user_id} sent photo during helping_registration, processing as screenshot")
    
    await update_user_status(user_id, 'waiting_screenshot')
    await state.set_state(UserStates.waiting_screenshot)
    
    from handlers.screenshot import handle_screenshot
    await handle_screenshot(message, message.bot, state)

@router.message(UserStates.waiting_admin, F.text)
async def handle_waiting_admin(message: Message, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    question = message.text
    
    if is_review_request(question):
        await send_reviews(message)
        return
    
    await save_message(user_id, 'user', question)
    
    await message.answer("Твой вопрос передан менеджеру, скоро тебе ответят! 😊")
    
    user = await get_user(user_id)
    user_display = get_user_display_name({
        'username': user['username'],
        'first_name': message.from_user.first_name,
        'user_id': user_id
    })
    
    await bot.send_message(
        ADMIN_ID,
        f"❓ Дополнительный вопрос от {user_display}:\n\n{question}",
        reply_markup=admin_answer_keyboard(user_id)
    )
    logger.info(f"Additional question from waiting user {user_id}: {question[:50]}...")

@router.message(UserStates.registered, F.text)
async def handle_registered_user(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    question = message.text
    
    if is_review_request(question):
        await send_reviews(message)
        return
    
    await save_message(user_id, 'user', question)
    logger.info(f"Question from registered user {user_id}: {question[:50]}...")
    
    in_groups = await is_user_in_groups(user_id)
    if not in_groups:
        in_groups = await check_group_membership(bot, user_id)
    
    await bot.send_chat_action(user_id, "typing")
    
    import time
    start_time = time.time()
    
    ai_result = await get_ai_response_with_retry(user_id, question, is_in_groups=in_groups)
    
    elapsed = time.time() - start_time
    if elapsed < 1:
        await asyncio.sleep(1 - elapsed)
    
    if ai_result['escalate'] or ai_result['confidence'] < AI_CONFIDENCE_THRESHOLD:
        await update_user_status(user_id, 'waiting_admin')
        await state.set_state(UserStates.waiting_admin)
        
        await save_pending_question(user_id, question)
        
        user = await get_user(user_id)
        user_display = get_user_display_name({
            'username': user['username'],
            'first_name': message.from_user.first_name,
            'user_id': user_id
        })
        
        await bot.send_message(
            ADMIN_ID,
            f"❓ Вопрос от {user_display}:\n\n{question}",
            reply_markup=admin_answer_keyboard(user_id)
        )
        
        await message.answer("Передаю твой вопрос менеджеру, скоро получишь ответ! 😊")
        logger.info(f"Question escalated to admin for registered user {user_id}")
    else:
        answer = ai_result['answer']
        await message.answer(answer)
        await save_message(user_id, 'bot', answer)
        await save_ai_learning(question, answer, 'auto', ai_result['confidence'])
        logger.info(f"Auto-answered for registered user {user_id} with confidence {ai_result['confidence']}")

@router.message(UserStates.registered, F.photo)
async def handle_screenshot_from_registered(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    logger.info(f"User {user_id} sent photo during registered state, processing as screenshot")
    
    await update_user_status(user_id, 'waiting_screenshot')
    await state.set_state(UserStates.waiting_screenshot)
    
    from handlers.screenshot import handle_screenshot
    await handle_screenshot(message, message.bot, state)

@router.message(UserStates.chatting, F.text)
async def handle_question(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        logger.info(f"Rejected user {user_id} tried to send message")
        return
    
    question = message.text
    
    if is_review_request(question):
        await send_reviews(message)
        return
    
    logger.info(f"Question from user {user_id}: {question[:50]}...")
    await save_message(user_id, 'user', question)
    logger.info(f"Message saved for user {user_id}")
    
    await bot.send_chat_action(user_id, "typing")
    logger.info(f"Typing action sent for user {user_id}")
    
    import time
    start_time = time.time()
    
    logger.info(f"Calling AI for user {user_id}")
    ai_result = await get_ai_response_with_retry(user_id, question)
    logger.info(f"AI responded for user {user_id} in {time.time() - start_time:.2f}s")
    
    elapsed = time.time() - start_time
    if elapsed < 1:
        wait_time = 1 - elapsed
        logger.info(f"Adding {wait_time:.2f}s delay for naturalness")
        await asyncio.sleep(wait_time)
    
    if ai_result['escalate'] or ai_result['confidence'] < AI_CONFIDENCE_THRESHOLD:
        logger.info(f"Escalating to admin for user {user_id}, confidence: {ai_result['confidence']}")
        await update_user_status(user_id, 'waiting_admin')
        await state.set_state(UserStates.waiting_admin)
        
        await save_pending_question(user_id, question)
        
        user = await get_user(user_id)
        user_display = get_user_display_name({
            'username': user['username'],
            'first_name': message.from_user.first_name,
            'user_id': user_id
        })
        
        await bot.send_message(
            ADMIN_ID,
            f"❓ Вопрос от {user_display}:\n\n{question}",
            reply_markup=admin_answer_keyboard(user_id)
        )
        
        await message.answer("Передаю твой вопрос менеджеру, скоро получишь ответ! 😊")
        logger.info(f"Question escalated to admin for user {user_id}")
    else:
        answer = ai_result['answer']
        logger.info(f"Sending auto-answer to user {user_id}: {answer[:50]}...")
        await message.answer(answer)
        await save_message(user_id, 'bot', answer)
        await save_ai_learning(question, answer, 'auto', ai_result['confidence'])
        logger.info(f"Auto-answered for user {user_id} with confidence {ai_result['confidence']}")

@router.message(F.text)
async def block_rejected_users(message: Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    if await is_user_rejected(message.from_user.id):
        logger.info(f"Blocked message from rejected user {message.from_user.id}")
        return