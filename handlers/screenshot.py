import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from states import UserStates
from keyboards import groups_keyboard
from database import get_user, update_user_status, get_setting
from utils.ocr_handler import extract_id

router = Router()
logger = logging.getLogger(__name__)

async def is_user_rejected(user_id):
    user = await get_user(user_id)
    return user and user['status'] == 'rejected'

def get_user_display_name(user_data):
    if user_data.get('username'):
        return f"@{user_data['username']}"
    return user_data.get('first_name', f"User {user_data['user_id']}")

@router.message(UserStates.waiting_screenshot, F.photo)
async def handle_screenshot(message: Message, bot, state: FSMContext):
    user_id = message.from_user.id
    
    logger.info(f"Screenshot received from user {user_id}")
    
    if await is_user_rejected(user_id):
        logger.info(f"User {user_id} is rejected, ignoring screenshot")
        return
    
    current_state = await state.get_state()
    logger.info(f"Current state for user {user_id}: {current_state}")
    
    if current_state != UserStates.waiting_screenshot.state:
        logger.warning(f"User {user_id} sent photo but not in waiting_screenshot state, current: {current_state}")
        await update_user_status(user_id, 'waiting_screenshot')
        await state.set_state(UserStates.waiting_screenshot)
        logger.info(f"Force set state to waiting_screenshot for user {user_id}")
    
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        logger.info(f"Got file info for user {user_id}: {file.file_path}")
        
        file_bytes = await bot.download_file(file.file_path)
        logger.info(f"Downloaded file for user {user_id}")
        
        extracted_id = extract_id(file_bytes.read())
        logger.info(f"Extracted ID for user {user_id}: {extracted_id}")
        
        user_data = await get_user(user_id)
        user_display = get_user_display_name({
            'username': user_data['username'],
            'first_name': message.from_user.first_name,
            'user_id': user_id
        })
        
        username = user_data['username']
        user_link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
        
        caption_text = message.caption.strip() if message.caption else ""
        logger.info(f"Caption from user {user_id}: '{caption_text}'")
        
        if extracted_id:
            logger.info(f"ID extracted successfully for user {user_id}: {extracted_id}")
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"📸 Скриншот\n🆔 ID: {extracted_id}\n👤 {user_display}\n🔗 {user_link}"
            )
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            
            user_lang = user_data['language'] or 'ru'
            
            approval_msg = await get_setting('approval_message')
            
            if user_lang == 'en':
                await message.answer(approval_msg)
                await message.answer("Great! Your application has been sent to the office. Your account will be activated on the next business day ✅")
                
                training_text = """Review the training

After registering:
- Visit the website
- Our website has posts and videos with comprehensive information.
- Be sure to read them!

If you have any questions, please write to me. I am always available and happy to help 😊

https://trainingforhost.wordpress.com"""
                
                await message.answer(training_text)
            else:
                await message.answer(approval_msg, reply_markup=groups_keyboard())
                await message.answer("Отлично! Твоя заявка отправлена в офис. На следующий будний день твой аккаунт активируют ✅")
            
            logger.info(f"Screenshot processed successfully for user {user_id}, ID: {extracted_id}")
            
        elif caption_text and caption_text.isdigit() and 6 <= len(caption_text) <= 15:
            logger.info(f"Using caption as ID for user {user_id}: {caption_text}")
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"📸 Скриншот\n🆔 ID (из подписи): {caption_text}\n👤 {user_display}\n🔗 {user_link}"
            )
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            
            user_lang = user_data['language'] or 'ru'
            
            approval_msg = await get_setting('approval_message')
            
            if user_lang == 'en':
                await message.answer(approval_msg)
                await message.answer("Great! Your application has been sent to the office. Your account will be activated on the next business day ✅")
                
                training_text = """Review the training

After registering:
- Visit the website
- Our website has posts and videos with comprehensive information.
- Be sure to read them!

If you have any questions, please write to me. I am always available and happy to help 😊

https://trainingforhost.wordpress.com"""
                
                await message.answer(training_text)
            else:
                await message.answer(approval_msg, reply_markup=groups_keyboard())
                await message.answer("Отлично! Твоя заявка отправлена в офис. На следующий будний день твой аккаунт активируют ✅")
            
            logger.info(f"Screenshot with caption processed for user {user_id}: {caption_text}")
            
        else:
            logger.warning(f"Could not extract ID from screenshot for user {user_id}")
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"📸 Скриншот\n👤 {user_display}\n🔗 {user_link}\n\n⚠️ ID не распознан"
            )
            
            user_lang = user_data['language'] or 'ru'
            not_recognized_texts = {
                'ru': "Не могу распознать ID на скриншоте. Пожалуйста, пришли его вручную текстом (только цифры).",
                'uk': "Не можу розпізнати ID на скріншоті. Будь ласка, надішли його вручну текстом (тільки цифри).",
                'en': "Cannot recognize ID on screenshot. Please send it manually as text (digits only)."
            }
            await message.answer(not_recognized_texts.get(user_lang, not_recognized_texts['ru']))
            logger.info(f"Sent manual ID request to user {user_id}")
            
    except Exception as e:
        logger.error(f"Error processing screenshot for user {user_id}: {e}", exc_info=True)
        
        user_data = await get_user(user_id)
        user_lang = user_data['language'] if user_data else 'ru'
        error_texts = {
            'ru': "Произошла ошибка при обработке скриншота. Попробуй ещё раз или напиши ID вручную.",
            'uk': "Сталася помилка при обробці скріншота. Спробуй ще раз або напиши ID вручну.",
            'en': "An error occurred while processing the screenshot. Try again or send the ID manually."
        }
        await message.answer(error_texts.get(user_lang, error_texts['ru']))

@router.message(UserStates.waiting_screenshot, F.text)
async def handle_manual_id(message: Message, bot, state: FSMContext):
    user_id = message.from_user.id
    
    logger.info(f"Manual ID text received from user {user_id}: '{message.text}'")
    
    if await is_user_rejected(user_id):
        logger.info(f"User {user_id} is rejected, ignoring manual ID")
        return
    
    manual_id = message.text.strip()
    
    user_data = await get_user(user_id)
    user_lang = user_data['language'] or 'ru'
    
    if not manual_id.isdigit():
        logger.info(f"Manual ID from user {user_id} is not digits: '{manual_id}'")
        invalid_texts = {
            'ru': "Пожалуйста, пришли только цифры ID (например: 351681973)",
            'uk': "Будь ласка, надішли тільки цифри ID (наприклад: 351681973)",
            'en': "Please send only ID digits (for example: 351681973)"
        }
        await message.answer(invalid_texts.get(user_lang, invalid_texts['ru']))
        return
    
    if len(manual_id) < 6 or len(manual_id) > 15:
        logger.info(f"Manual ID from user {user_id} has invalid length: {len(manual_id)}")
        length_texts = {
            'ru': "ID должен содержать от 6 до 15 цифр. Проверь и отправь ещё раз.",
            'uk': "ID повинен містити від 6 до 15 цифр. Перевір і надішли ще раз.",
            'en': "ID must contain from 6 to 15 digits. Check and send again."
        }
        await message.answer(length_texts.get(user_lang, length_texts['ru']))
        return
    
    user_display = get_user_display_name({
        'username': user_data['username'],
        'first_name': message.from_user.first_name,
        'user_id': user_id
    })
    
    username = user_data['username']
    user_link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
    
    logger.info(f"Valid manual ID received from user {user_id}: {manual_id}")
    
    await bot.send_message(
        ADMIN_ID,
        f"🆔 ID (вручную): {manual_id}\n👤 {user_display}\n🔗 {user_link}"
    )
    
    await update_user_status(user_id, 'registered')
    await state.set_state(UserStates.registered)
    
    approval_msg = await get_setting('approval_message')
    
    if user_lang == 'en':
        await message.answer(approval_msg)
        await message.answer("Great! Your application has been sent to the office. Your account will be activated on the next business day ✅")
        
        training_text = """Review the training

After registering:
- Visit the website
- Our website has posts and videos with comprehensive information.
- Be sure to read them!

If you have any questions, please write to me. I am always available and happy to help 😊

https://trainingforhost.wordpress.com"""
        
        await message.answer(training_text)
    else:
        await message.answer(approval_msg, reply_markup=groups_keyboard())
        await message.answer("Отлично! Твоя заявка отправлена в офис. На следующий будний день твой аккаунт активируют ✅")
    
    logger.info(f"Manual ID processed successfully for user {user_id}: {manual_id}")