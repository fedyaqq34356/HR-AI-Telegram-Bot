import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from states import UserStates
from database import get_user, update_user_status
from utils.ocr_handler import extract_id

router = Router()
logger = logging.getLogger(__name__)

async def is_user_rejected(user_id):
    user = await get_user(user_id)
    return user and user['status'] == 'rejected'

@router.message(UserStates.waiting_screenshot, F.photo)
async def handle_screenshot(message: Message, bot, state: FSMContext):
    user_id = message.from_user.id
    
    logger.info(f"Screenshot received from user {user_id}")
    
    if await is_user_rejected(user_id):
        logger.info(f"User {user_id} is rejected, ignoring screenshot")
        return
    
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        logger.info(f"Got file info for user {user_id}: {file.file_path}")
        
        file_bytes = await bot.download_file(file.file_path)
        logger.info(f"Downloaded file for user {user_id}")
        
        extracted_id = extract_id(file_bytes.read())
        logger.info(f"Extracted ID for user {user_id}: {extracted_id}")
        
        user_data = await get_user(user_id)
        username = user_data['username']
        
        caption_text = message.caption.strip() if message.caption else ""
        logger.info(f"Caption from user {user_id}: '{caption_text}'")
        
        if extracted_id:
            logger.info(f"ID extracted successfully for user {user_id}: {extracted_id}")
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"📸 Скриншот\n🆔 ID: {extracted_id}\n👤 @{username}\n🔗 https://t.me/{username}"
            )
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            await message.answer("Отлично! Твоя заявка отправлена в офис. На следующий будний день твой аккаунт активируют ✅\n\nЧтобы бот продолжал с вами коммуницировать пропишите /start")
            logger.info(f"Screenshot processed successfully for user {user_id}, ID: {extracted_id}")
            
        elif caption_text and caption_text.isdigit() and 6 <= len(caption_text) <= 15:
            logger.info(f"Using caption as ID for user {user_id}: {caption_text}")
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"📸 Скриншот\n🆔 ID (из подписи): {caption_text}\n👤 @{username}\n🔗 https://t.me/{username}"
            )
            await update_user_status(user_id, 'registered')
            await state.set_state(UserStates.registered)
            await message.answer("Отлично! Твоя заявка отправлена в офис. На следующий будний день твой аккаунт активируют ✅\n\nЧтобы бот продолжал с вами коммуницировать пропишите /start")
            logger.info(f"Screenshot with caption processed for user {user_id}: {caption_text}")
            
        else:
            logger.warning(f"Could not extract ID from screenshot for user {user_id}")
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"📸 Скриншот\n👤 @{username}\n🔗 https://t.me/{username}\n\n⚠️ ID не распознан"
            )
            await message.answer("Не могу распознать ID на скриншоте. Пожалуйста, пришли его вручную текстом (только цифры).")
            logger.info(f"Sent manual ID request to user {user_id}")
            
    except Exception as e:
        logger.error(f"Error processing screenshot for user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке скриншота. Попробуй ещё раз или напиши ID вручную.")

@router.message(UserStates.waiting_screenshot, F.text)
async def handle_manual_id(message: Message, bot, state: FSMContext):
    user_id = message.from_user.id
    
    logger.info(f"Manual ID text received from user {user_id}: '{message.text}'")
    
    if await is_user_rejected(user_id):
        logger.info(f"User {user_id} is rejected, ignoring manual ID")
        return
    
    manual_id = message.text.strip()
    
    if not manual_id.isdigit():
        logger.info(f"Manual ID from user {user_id} is not digits: '{manual_id}'")
        return
    
    if len(manual_id) < 6 or len(manual_id) > 15:
        logger.info(f"Manual ID from user {user_id} has invalid length: {len(manual_id)}")
        return
    
    user_data = await get_user(user_id)
    
    logger.info(f"Valid manual ID received from user {user_id}: {manual_id}")
    
    await bot.send_message(
        ADMIN_ID,
        f"🆔 ID (вручную): {manual_id}\n👤 @{user_data['username']}\n🔗 https://t.me/{user_data['username']}"
    )
    
    await update_user_status(user_id, 'registered')
    await state.set_state(UserStates.registered)
    await message.answer("Отлично! Твоя заявка отправлена в офис. На следующий будний день твой аккаунт активируют ✅\n\nЧтобы бот продолжал с вами коммуницировать пропишите /start")
    logger.info(f"Manual ID processed successfully for user {user_id}: {manual_id}")