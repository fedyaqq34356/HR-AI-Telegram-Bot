import os
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID, GROUP_ID, SMS_GROUP_ID, ANALYSIS_TEXT_DIR, ANALYSIS_AUDIO_DIR, ANALYSIS_VIDEO_DIR, ANALYSIS_SMS_DIR

router = Router()
logger = logging.getLogger(__name__)

for directory in [ANALYSIS_TEXT_DIR, ANALYSIS_AUDIO_DIR, ANALYSIS_VIDEO_DIR, ANALYSIS_SMS_DIR]:
    os.makedirs(directory, exist_ok=True)

@router.message(F.text, F.chat.type.in_({'group', 'supergroup', 'channel'}))
async def capture_group_text(message: Message):
    logger.info(f"Received text from chat_id={message.chat.id}, type={message.chat.type}, GROUP_ID={GROUP_ID}, SMS_GROUP_ID={SMS_GROUP_ID}")
    
    if message.chat.id not in [GROUP_ID, SMS_GROUP_ID]:
        logger.info(f"Skipping message from chat {message.chat.id}")
        return
    
    if message.text and message.text.startswith('/'):
        logger.info(f"Skipping command: {message.text}")
        return
    
    from database.group_messages import save_group_message
    username = message.from_user.username if message.from_user else 'Unknown'
    
    message_type = 'sms' if message.chat.id == SMS_GROUP_ID else 'text'
    
    await save_group_message(
        message_id=message.message_id,
        message_type=message_type,
        content=message.text,
        username=username
    )
    logger.info(f"✅ Captured {message_type} message {message.message_id} from group")

@router.message(F.voice | F.audio, F.chat.type.in_({'group', 'supergroup', 'channel'}))
async def capture_group_audio(message: Message):
    logger.info(f"Received audio from chat_id={message.chat.id}, type={message.chat.type}")
    
    if message.chat.id not in [GROUP_ID, SMS_GROUP_ID]:
        return
    
    from database.group_messages import save_group_message
    username = message.from_user.username if message.from_user else 'Unknown'
    audio = message.voice or message.audio
    await save_group_message(
        message_id=message.message_id,
        message_type='audio',
        file_id=audio.file_id,
        username=username
    )
    logger.info(f"✅ Captured audio message {message.message_id} from group")

@router.message(F.video | F.video_note, F.chat.type.in_({'group', 'supergroup', 'channel'}))
async def capture_group_video(message: Message):
    logger.info(f"Received video from chat_id={message.chat.id}, type={message.chat.type}")
    
    if message.chat.id not in [GROUP_ID, SMS_GROUP_ID]:
        return
    
    from database.group_messages import save_group_message
    username = message.from_user.username if message.from_user else 'Unknown'
    video = message.video or message.video_note
    await save_group_message(
        message_id=message.message_id,
        message_type='video',
        file_id=video.file_id,
        username=username
    )
    logger.info(f"✅ Captured video message {message.message_id} from group")

@router.message(Command("startanal"))
async def cmd_start_analysis(message: Message, bot):
    if message.from_user.id != ADMIN_ID:
        return
    
    from database.analysis import save_analysis_text, save_analysis_audio, save_analysis_video, save_analysis_sms, clear_analysis_data
    from database.group_messages import get_unprocessed_messages, mark_message_processed
    from utils.audio_transcription import transcribe_audio
    
    await clear_analysis_data()
    
    await message.answer("🔍 Начинаю анализ сохраненных сообщений из групп...")
    
    messages = await get_unprocessed_messages()
    
    if not messages:
        await message.answer("❌ Нет новых сообщений для обработки. Бот должен быть добавлен в группы для автоматического сбора сообщений.")
        return
    
    text_count = 0
    sms_count = 0
    audio_count = 0
    video_count = 0
    
    try:
        for msg in messages:
            if msg['message_type'] == 'text':
                text_count += 1
                filename = f"text_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filepath = os.path.join(ANALYSIS_TEXT_DIR, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Message ID: {msg['message_id']}\n")
                    f.write(f"Date: {msg['timestamp']}\n")
                    f.write(f"From: {msg['username']}\n\n")
                    f.write(msg['content'])
                
                await save_analysis_text(msg['message_id'], msg['content'], filename)
                await mark_message_processed(msg['message_id'])
                
                if text_count % 10 == 0:
                    await message.answer(f"📝 Обработано текстовых сообщений: {text_count}")
            
            elif msg['message_type'] == 'sms':
                sms_count += 1
                filename = f"sms_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filepath = os.path.join(ANALYSIS_SMS_DIR, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Message ID: {msg['message_id']}\n")
                    f.write(f"Date: {msg['timestamp']}\n")
                    f.write(f"From: {msg['username']}\n\n")
                    f.write(msg['content'])
                
                await save_analysis_sms(msg['message_id'], msg['content'], filename)
                await mark_message_processed(msg['message_id'])
                
                if sms_count % 10 == 0:
                    await message.answer(f"💬 Обработано SMS сообщений: {sms_count}")
        
        await message.answer(f"✅ Текстовые сообщения обработаны: {text_count}\n✅ SMS сообщения обработаны: {sms_count}\n\n🎤 Обрабатываю аудио...")
        
        for msg in messages:
            if msg['message_type'] == 'audio':
                audio_count += 1
                
                temp_filename = f"temp_audio_{msg['message_id']}.ogg"
                file = await bot.get_file(msg['file_id'])
                await bot.download_file(file.file_path, temp_filename)
                
                try:
                    transcription = await transcribe_audio(temp_filename)
                    
                    filename = f"audio_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    filepath = os.path.join(ANALYSIS_AUDIO_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg['message_id']}\n")
                        f.write(f"Date: {msg['timestamp']}\n")
                        f.write(f"From: {msg['username']}\n\n")
                        f.write(transcription)
                    
                    await save_analysis_audio(msg['message_id'], transcription, filename)
                    await mark_message_processed(msg['message_id'])
                    
                    if audio_count % 5 == 0:
                        await message.answer(f"🎤 Обработано аудио: {audio_count}")
                    
                except Exception as e:
                    logger.error(f"Error transcribing audio {msg['message_id']}: {e}")
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
        
        await message.answer(f"✅ Аудио обработаны: {audio_count}\n\n🎥 Обрабатываю видео...")
        
        for msg in messages:
            if msg['message_type'] == 'video':
                video_count += 1
                
                temp_filename = f"temp_video_{msg['message_id']}.mp4"
                file = await bot.get_file(msg['file_id'])
                await bot.download_file(file.file_path, temp_filename)
                
                try:
                    transcription = await transcribe_audio(temp_filename)
                    
                    filename = f"video_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    filepath = os.path.join(ANALYSIS_VIDEO_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg['message_id']}\n")
                        f.write(f"Date: {msg['timestamp']}\n")
                        f.write(f"From: {msg['username']}\n\n")
                        f.write(transcription)
                    
                    await save_analysis_video(msg['message_id'], transcription, filename)
                    await mark_message_processed(msg['message_id'])
                    
                    if video_count % 5 == 0:
                        await message.answer(f"🎥 Обработано видео: {video_count}")
                    
                except Exception as e:
                    logger.error(f"Error transcribing video {msg['message_id']}: {e}")
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
        
        await message.answer(f"✅ Видео обработаны: {video_count}\n\n🎉 Анализ завершен!\n\n📊 Итого:\n📝 Тексты: {text_count}\n💬 SMS: {sms_count}\n🎤 Аудио: {audio_count}\n🎥 Видео: {video_count}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при анализе: {e}")

@router.message(Command("clearanal"))
async def cmd_clear_analysis(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    from database.group_messages import clear_group_messages
    from database.analysis import clear_analysis_data
    
    await clear_group_messages()
    await clear_analysis_data()
    await message.answer("✅ Все сохраненные сообщения и анализы очищены")

@router.message(Command("chatid"))
async def cmd_chat_id(message: Message):
    await message.answer(
        f"📊 Информация о чате:\n\n"
        f"Chat ID: `{message.chat.id}`\n"
        f"Chat Type: {message.chat.type}\n"
        f"Chat Title: {message.chat.title or 'N/A'}\n"
        f"Your ID: {message.from_user.id}\n\n"
        f"GROUP_ID в config: {GROUP_ID}\n"
        f"SMS_GROUP_ID в config: {SMS_GROUP_ID}"
    )