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
    get_user, create_user, update_user_status, save_message, update_user_language,
    save_photo, get_setting, save_ai_learning, save_pending_question,
    is_user_in_groups, add_user_to_groups, unhide_user_on_activity, has_bot_responded
)
from utils.ai_handler import get_ai_response_with_retry
from handlers.reviews import is_review_request, send_reviews
from utils.language_detector import detect_language_request, detect_language

router = Router()
logger = logging.getLogger(__name__)

photo_group_cache = {}

REGISTRATION_INTENT_PATTERNS = [
    'зарегистрироваться', 'зарегистрироваться', 'зарегстрироваться',
    'зарегістрироваться', 'зарегістрироваться', 'хочу зарегист',
    'хочу зарегіст', 'want to register', 'i want to register',
    'реєстрація', 'регистрация', 'зарегіс', 'зарегис',
    'sign up', 'signup',
]

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

def is_registration_intent(text):
    text_lower = text.lower().strip()
    return any(pattern in text_lower for pattern in REGISTRATION_INTENT_PATTERNS)

def get_already_registered_text(user_lang):
    texts = {
        'ru': "Ты уже зарегистрирована! Если есть вопросы по работе — просто спрашивай 😊",
        'uk': "Ти вже зарегістрована! Якщо є питання по роботі — просто питай 😊",
        'en': "You're already registered! If you have any work questions — just ask 😊"
    }
    return texts.get(user_lang, texts['ru'])

async def auto_detect_and_update_language(user_id, text):
    detected = detect_language(text)
    user = await get_user(user_id)
    current_lang = user['language'] or 'ru'
    if detected != current_lang:
        await update_user_language(user_id, detected)
        logger.info(f"Auto-detected language '{detected}' for user {user_id} (was '{current_lang}')")
    return detected

async def handle_language_switch(message: Message, user_id: int):
    requested_lang = detect_language_request(message.text)
    
    if requested_lang:
        await update_user_language(user_id, requested_lang)
        
        confirm_texts = {
            'ru': "✅ Переключаюсь на русский язык",
            'uk': "✅ Переключаюсь на українську мову",
            'en': "✅ Switching to English"
        }
        
        welcome_msg = await get_setting(f'welcome_message_{requested_lang}')
        if not welcome_msg:
            welcome_msg = await get_setting('welcome_message_ru')
        
        confirm_text = confirm_texts.get(requested_lang, confirm_texts['ru'])
        await message.answer(confirm_text)
        await save_message(user_id, 'bot', confirm_text)
        
        await message.answer(welcome_msg)
        await save_message(user_id, 'bot', welcome_msg)
        
        logger.info(f"User {user_id} switched language to {requested_lang}")
        return True
    
    return False

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        from keyboards import admin_main_menu
        admin_text = "👋 Привет, администратор!\n\nИспользуй команду /admin для доступа к панели управления"
        await message.answer(admin_text, reply_markup=admin_main_menu())
        return
    
    await unhide_user_on_activity(user_id)
    
    username = message.from_user.username or f"user_{user_id}"
    user = await get_user(user_id)
    
    is_in_group = await check_group_membership(bot, user_id)
    
    if user and user['status'] == 'rejected':
        return
    
    if not user:
        await create_user(user_id, username, language='ru')
        
        if is_in_group:
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            
            return_texts = {
                'ru': "Привет! Чем могу помочь? 😊",
                'uk': "Привіт! Чим можу допомогти? 😊",
                'en': "Hi! How can I help? 😊"
            }
            return_text = return_texts.get('ru', return_texts['ru'])
            await message.answer(return_text)
            await save_message(user_id, 'bot', return_text)
        else:
            await update_user_status(user_id, 'chatting')
            await state.set_state(UserStates.chatting)
            
            welcome_msg = await get_setting('welcome_message_ru')
            await message.answer(welcome_msg)
            await save_message(user_id, 'bot', welcome_msg)
    else:
        if is_in_group and user['status'] not in ['registered', 'approved']:
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
        
        user_lang = user['language'] or 'ru'
        
        if is_in_group:
            return_texts = {
                'ru': "Привет! Чем могу помочь? 😊",
                'uk': "Привіт! Чим можу допомогти? 😊",
                'en': "Hi! How can I help? 😊"
            }
        else:
            return_texts = {
                'ru': "С возвращением! Чем могу помочь? 😊",
                'uk': "З поверненням! Чим можу допомогти? 😊",
                'en': "Welcome back! How can I help? 😊"
            }
        
        return_text = return_texts.get(user_lang, return_texts['ru'])
        await message.answer(return_text)
        await save_message(user_id, 'bot', return_text)
        
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
    
    await unhide_user_on_activity(user_id)
    
    user = await get_user(user_id)
    
    if user['status'] not in ['new', 'chatting', 'waiting_photos']:
        logger.info(f"User {user_id} sent photo but in status {user['status']}, ignoring")
        return
    
    photos_count = user['photos_count']
    
    if photos_count >= PHOTOS_MAX:
        user_lang = user['language'] or 'ru'
        max_texts = {
            'ru': f"Максимум {PHOTOS_MAX} фото! У тебя уже загружено достаточно 👍",
            'uk': f"Максимум {PHOTOS_MAX} фото! У тебе вже завантажено достатньо 👍",
            'en': f"Maximum {PHOTOS_MAX} photos! You've already uploaded enough 👍"
        }
        max_text = max_texts.get(user_lang, max_texts['ru'])
        await message.answer(max_text)
        await save_message(user_id, 'bot', max_text)
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
            
            await asyncio.sleep(1.0)
            
            if media_group_id in photo_group_cache and not photo_group_cache[media_group_id]['processed']:
                photos_in_group = photo_group_cache[media_group_id]['photos']
                photo_group_cache[media_group_id]['processed'] = True
                
                current_count = (await get_user(user_id))['photos_count']
                total_photos = current_count + len(photos_in_group)
                
                if total_photos > PHOTOS_MAX:
                    user_lang = user['language'] or 'ru'
                    limit_texts = {
                        'ru': f"Можно загрузить максимум {PHOTOS_MAX} фото! Отправь не больше {PHOTOS_MAX - current_count} фото.",
                        'uk': f"Можна завантажити максимум {PHOTOS_MAX} фото! Надішли не більше {PHOTOS_MAX - current_count} фото.",
                        'en': f"You can upload maximum {PHOTOS_MAX} photos! Send no more than {PHOTOS_MAX - current_count} photos."
                    }
                    limit_text = limit_texts.get(user_lang, limit_texts['ru'])
                    await message.answer(limit_text)
                    await save_message(user_id, 'bot', limit_text)
                    del photo_group_cache[media_group_id]
                    return
                
                for file_id in photos_in_group:
                    await save_photo(user_id, file_id)
                
                await save_message(user_id, 'user', f'[Отправлено {len(photos_in_group)} фото]')
                
                del photo_group_cache[media_group_id]
                
                user = await get_user(user_id)
                photos_count = user['photos_count']
                
                if photos_count < PHOTOS_MIN:
                    remaining = PHOTOS_MIN - photos_count
                    user_lang = user['language'] or 'ru'
                    remaining_texts = {
                        'ru': f"Отлично! Нужно ещё минимум {remaining} фото 📸",
                        'uk': f"Чудово! Потрібно ще мінімум {remaining} фото 📸",
                        'en': f"Great! Need at least {remaining} more photo(s) 📸"
                    }
                    remaining_text = remaining_texts.get(user_lang, remaining_texts['ru'])
                    await message.answer(remaining_text)
                    await save_message(user_id, 'bot', remaining_text)
                elif photos_count >= PHOTOS_MIN:
                    await update_user_status(user_id, 'asking_work_hours')
                    await state.set_state(UserStates.asking_work_hours)
                    user_lang = user['language'] or 'ru'
                    question_texts = {
                        'ru': "Отлично! Теперь несколько вопросов:\n\n1️⃣ Сколько времени в день ты готова уделять нашему приложению?\n(Ответь в свободной форме)",
                        'uk': "Чудово! Тепер декілька питань:\n\n1️⃣ Скільки часу на день ти готова приділяти нашому застосунку?\n(Відповідь у вільній формі)",
                        'en': "Great! Now a few questions:\n\n1️⃣ How much time per day are you ready to dedicate to our app?\n(Answer in free form)"
                    }
                    question_text = question_texts.get(user_lang, question_texts['ru'])
                    await message.answer(question_text)
                    await save_message(user_id, 'bot', question_text)
    else:
        file_id = message.photo[-1].file_id
        await save_photo(user_id, file_id)
        await save_message(user_id, 'user', '[Отправлено фото]')
        photos_count += 1
        
        if photos_count < PHOTOS_MIN:
            remaining = PHOTOS_MIN - photos_count
            user_lang = user['language'] or 'ru'
            remaining_texts = {
                'ru': f"Отлично! Нужно ещё минимум {remaining} фото 📸",
                'uk': f"Чудово! Потрібно ще мінімум {remaining} фото 📸",
                'en': f"Great! Need at least {remaining} more photo(s) 📸"
            }
            remaining_text = remaining_texts.get(user_lang, remaining_texts['ru'])
            await message.answer(remaining_text)
            await save_message(user_id, 'bot', remaining_text)
        elif photos_count >= PHOTOS_MIN:
            await update_user_status(user_id, 'asking_work_hours')
            await state.set_state(UserStates.asking_work_hours)
            user_lang = user['language'] or 'ru'
            question_texts = {
                'ru': "Отлично! Теперь несколько вопросов:\n\n1️⃣ Сколько времени в день ты готова уделять нашему приложению?\n(Ответь в свободной форме)",
                'uk': "Чудово! Тепер декілька питань:\n\n1️⃣ Скільки часу на день ти готова приділяти нашому застосунку?\n(Відповідь у вільній формі)",
                'en': "Great! Now a few questions:\n\n1️⃣ How much time per day are you ready to dedicate to our app?\n(Answer in free form)"
            }
            question_text = question_texts.get(user_lang, question_texts['ru'])
            await message.answer(question_text)
            await save_message(user_id, 'bot', question_text)

@router.message(UserStates.asking_work_hours, F.text)
async def handle_work_hours(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return
    
    if await is_user_rejected(message.from_user.id):
        return
    
    user_id = message.from_user.id
    await unhide_user_on_activity(user_id)
    
    if await handle_language_switch(message, user_id):
        return
    
    await auto_detect_and_update_language(user_id, message.text)
    
    await save_message(user_id, 'user', message.text)
    
    await state.update_data(work_hours=message.text)
    await update_user_status(user_id, 'asking_experience')
    await state.set_state(UserStates.asking_experience)
    
    user = await get_user(user_id)
    user_lang = user['language'] or 'ru'
    question_texts = {
        'ru': "2️⃣ Был ли у тебя опыт работы в похожих приложениях или платформах?\n(Если да — опиши кратко. Если нет — так и напиши)",
        'uk': "2️⃣ Чи був у тебе досвід роботи в подібних застосунках або платформах?\n(Якщо так — опиши коротко. Якщо ні — так і напиши)",
        'en': "2️⃣ Have you had experience working in similar apps or platforms?\n(If yes — describe briefly. If no — just say so)"
    }
    question_text = question_texts.get(user_lang, question_texts['ru'])
    await message.answer(question_text)
    await save_message(user_id, 'bot', question_text)

@router.message(UserStates.asking_experience, F.text)
async def handle_experience(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    from database import create_application, get_photos
    
    await unhide_user_on_activity(user_id)
    
    if await handle_language_switch(message, user_id):
        return
    
    await auto_detect_and_update_language(user_id, message.text)
    
    await save_message(user_id, 'user', message.text)
    
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
    
    user_lang = user['language'] or 'ru'
    response_texts = {
        'ru': "Спасибо! Твоя заявка отправлена на рассмотрение 😊",
        'uk': "Дякую! Твоя заявка надіслана на розгляд 😊",
        'en': "Thank you! Your application has been submitted for review 😊"
    }
    response_text = response_texts.get(user_lang, response_texts['ru'])
    await message.answer(response_text)
    await save_message(user_id, 'bot', response_text)

@router.message(UserStates.helping_registration, F.text)
async def handle_registration_questions(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    await unhide_user_on_activity(user_id)
    
    if await handle_language_switch(message, user_id):
        return
    
    await auto_detect_and_update_language(user_id, message.text)
    
    question = message.text
    user = await get_user(user_id)
    user_lang = user['language'] or 'ru'
    
    if is_review_request(question):
        await send_reviews(message, user_lang)
        return
    
    await save_message(user_id, 'user', question)
    
    await bot.send_chat_action(user_id, "typing")
    
    import time
    start_time = time.time()
    
    ai_result = await get_ai_response_with_retry(user_id, question)
    
    elapsed = time.time() - start_time
    if elapsed < 1:
        await asyncio.sleep(1 - elapsed)
    
    if ai_result['escalate'] or ai_result['confidence'] < AI_CONFIDENCE_THRESHOLD:
        await save_pending_question(user_id, question)
        
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
        
        escalate_texts = {
            'ru': "Передаю твой вопрос менеджеру, скоро получишь ответ! 😊",
            'uk': "Передаю твоє питання менеджеру, скоро отримаєш відповідь! 😊",
            'en': "Forwarding your question to the manager, you'll get an answer soon! 😊"
        }
        escalate_text = escalate_texts.get(user_lang, escalate_texts['ru'])
        await message.answer(escalate_text)
        await save_message(user_id, 'bot', escalate_text)
    else:
        answer = ai_result['answer']
        await message.answer(answer)
        await save_message(user_id, 'bot', answer)
        await save_ai_learning(question, answer, 'auto', ai_result['confidence'])

@router.message(UserStates.helping_registration, F.photo)
async def handle_photo_during_registration(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    await unhide_user_on_activity(user_id)
    
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
    
    await unhide_user_on_activity(user_id)
    
    if await handle_language_switch(message, user_id):
        return
    
    await auto_detect_and_update_language(user_id, message.text)
    
    question = message.text
    user = await get_user(user_id)
    user_lang = user['language'] or 'ru'
    
    if is_review_request(question):
        await send_reviews(message, user_lang)
        return
    
    await save_message(user_id, 'user', question)
    
    wait_texts = {
        'ru': "Твой вопрос передан менеджеру, скоро тебе ответят! 😊",
        'uk': "Твоє питання передане менеджеру, скоро тобі відповідять! 😊",
        'en': "Your question has been forwarded to the manager, you'll get an answer soon! 😊"
    }
    wait_text = wait_texts.get(user_lang, wait_texts['ru'])
    await message.answer(wait_text)
    await save_message(user_id, 'bot', wait_text)
    
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

@router.message(UserStates.registered, F.text)
async def handle_registered_user(message: Message, state: FSMContext, bot):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    await unhide_user_on_activity(user_id)
    
    if await handle_language_switch(message, user_id):
        return
    
    await auto_detect_and_update_language(user_id, message.text)
    
    question = message.text
    user = await get_user(user_id)
    user_lang = user['language'] or 'ru'
    
    if is_registration_intent(question):
        already_text = get_already_registered_text(user_lang)
        await message.answer(already_text)
        await save_message(user_id, 'bot', already_text)
        return
    
    if is_review_request(question):
        await send_reviews(message, user_lang)
        return
    
    await save_message(user_id, 'user', question)
    
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
        
        escalate_texts = {
            'ru': "Передаю твой вопрос менеджеру, скоро получишь ответ! 😊",
            'uk': "Передаю твоє питання менеджеру, скоро отримаєш відповідь! 😊",
            'en': "Forwarding your question to the manager, you'll get an answer soon! 😊"
        }
        escalate_text = escalate_texts.get(user_lang, escalate_texts['ru'])
        await message.answer(escalate_text)
        await save_message(user_id, 'bot', escalate_text)
    else:
        answer = ai_result['answer']
        await message.answer(answer)
        await save_message(user_id, 'bot', answer)
        await save_ai_learning(question, answer, 'auto', ai_result['confidence'])

@router.message(UserStates.registered, F.photo)
async def handle_screenshot_from_registered(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        return
    
    if await is_user_rejected(user_id):
        return
    
    await unhide_user_on_activity(user_id)
    
    user = await get_user(user_id)
    
    if user['status'] in ['registered', 'approved']:
        user_lang = user['language'] or 'ru'
        already_texts = {
            'ru': "Ты уже прошла регистрацию! Если у тебя есть вопросы по работе — просто спрашивай 😊",
            'uk': "Ти вже пройшла реєстрацію! Якщо у тебе є питання по роботі — просто питай 😊",
            'en': "You've already completed registration! If you have work-related questions — just ask 😊"
        }
        await message.answer(already_texts.get(user_lang, already_texts['ru']))
        return
    
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
        return
    
    await unhide_user_on_activity(user_id)
    
    if await handle_language_switch(message, user_id):
        return
    
    await auto_detect_and_update_language(user_id, message.text)
    
    question = message.text
    user = await get_user(user_id)
    user_lang = user['language'] or 'ru'
    
    if is_review_request(question):
        await send_reviews(message, user_lang)
        return
    
    await save_message(user_id, 'user', question)
    
    await bot.send_chat_action(user_id, "typing")
    
    import time
    start_time = time.time()
    
    ai_result = await get_ai_response_with_retry(user_id, question)
    
    elapsed = time.time() - start_time
    if elapsed < 1:
        await asyncio.sleep(1 - elapsed)
    
    if ai_result['escalate'] or ai_result['confidence'] < AI_CONFIDENCE_THRESHOLD:
        await update_user_status(user_id, 'waiting_admin')
        await state.set_state(UserStates.waiting_admin)
        
        await save_pending_question(user_id, question)
        
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
        
        escalate_texts = {
            'ru': "Передаю твой вопрос менеджеру, скоро получишь ответ! 😊",
            'uk': "Передаю твоє питання менеджеру, скоро отримаєш відповідь! 😊",
            'en': "Forwarding your question to the manager, you'll get an answer soon! 😊"
        }
        escalate_text = escalate_texts.get(user_lang, escalate_texts['ru'])
        await message.answer(escalate_text)
        await save_message(user_id, 'bot', escalate_text)
    else:
        answer = ai_result['answer']
        await message.answer(answer)
        await save_message(user_id, 'bot', answer)
        await save_ai_learning(question, answer, 'auto', ai_result['confidence'])

@router.message(F.text)
async def block_rejected_users(message: Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    if await is_user_rejected(message.from_user.id):
        return