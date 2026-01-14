import os
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID, GROUP_ID, ANALYSIS_TEXT_DIR, ANALYSIS_AUDIO_DIR, ANALYSIS_VIDEO_DIR
from database.analysis import save_analysis_text, save_analysis_audio, save_analysis_video, clear_analysis_data
from utils.audio_transcription import transcribe_audio

router = Router()
logger = logging.getLogger(__name__)

for directory in [ANALYSIS_TEXT_DIR, ANALYSIS_AUDIO_DIR, ANALYSIS_VIDEO_DIR]:
    os.makedirs(directory, exist_ok=True)

@router.message(Command("startanal"))
async def cmd_start_analysis(message: Message, bot):
    if message.from_user.id != ADMIN_ID:
        return
    
    await clear_analysis_data()
    
    await message.answer("🔍 Начинаю анализ группы...\n\n📝 Обрабатываю текстовые сообщения...")
    
    text_count = 0
    audio_count = 0
    video_count = 0
    
    try:
        async for msg in bot.iter_history(GROUP_ID):
            if msg.text:
                text_count += 1
                filename = f"text_{msg.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filepath = os.path.join(ANALYSIS_TEXT_DIR, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Message ID: {msg.message_id}\n")
                    f.write(f"Date: {msg.date}\n")
                    f.write(f"From: {msg.from_user.username if msg.from_user else 'Unknown'}\n\n")
                    f.write(msg.text)
                
                await save_analysis_text(msg.message_id, msg.text, filename)
                
                if text_count % 10 == 0:
                    await message.answer(f"📝 Обработано текстовых сообщений: {text_count}")
        
        await message.answer(f"✅ Текстовые сообщения обработаны: {text_count}\n\n🎤 Обрабатываю аудио...")
        
        async for msg in bot.iter_history(GROUP_ID):
            if msg.voice or msg.audio:
                audio_count += 1
                
                audio_file = msg.voice or msg.audio
                file = await bot.get_file(audio_file.file_id)
                
                temp_filename = f"temp_audio_{msg.message_id}.ogg"
                await bot.download_file(file.file_path, temp_filename)
                
                try:
                    transcription = await transcribe_audio(temp_filename)
                    
                    filename = f"audio_{msg.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    filepath = os.path.join(ANALYSIS_AUDIO_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg.message_id}\n")
                        f.write(f"Date: {msg.date}\n")
                        f.write(f"From: {msg.from_user.username if msg.from_user else 'Unknown'}\n\n")
                        f.write(transcription)
                    
                    await save_analysis_audio(msg.message_id, transcription, filename)
                    
                    if audio_count % 5 == 0:
                        await message.answer(f"🎤 Обработано аудио: {audio_count}")
                    
                except Exception as e:
                    logger.error(f"Error transcribing audio {msg.message_id}: {e}")
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
        
        await message.answer(f"✅ Аудио обработаны: {audio_count}\n\n🎥 Обрабатываю видео...")
        
        async for msg in bot.iter_history(GROUP_ID):
            if msg.video or msg.video_note:
                video_count += 1
                
                video_file = msg.video or msg.video_note
                file = await bot.get_file(video_file.file_id)
                
                temp_filename = f"temp_video_{msg.message_id}.mp4"
                await bot.download_file(file.file_path, temp_filename)
                
                try:
                    transcription = await transcribe_audio(temp_filename)
                    
                    filename = f"video_{msg.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    filepath = os.path.join(ANALYSIS_VIDEO_DIR, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg.message_id}\n")
                        f.write(f"Date: {msg.date}\n")
                        f.write(f"From: {msg.from_user.username if msg.from_user else 'Unknown'}\n\n")
                        f.write(transcription)
                    
                    await save_analysis_video(msg.message_id, transcription, filename)
                    
                    if video_count % 5 == 0:
                        await message.answer(f"🎥 Обработано видео: {video_count}")
                    
                except Exception as e:
                    logger.error(f"Error transcribing video {msg.message_id}: {e}")
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
        
        await message.answer(f"✅ Видео обработаны: {video_count}\n\n🎉 Анализ завершен!\n\n📊 Итого:\n📝 Тексты: {text_count}\n🎤 Аудио: {audio_count}\n🎥 Видео: {video_count}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при анализе: {e}")