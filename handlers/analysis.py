# handlers/analysis.py
import os
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID, ANALYSIS_TEXT_DIR, ANALYSIS_AUDIO_DIR, ANALYSIS_VIDEO_DIR

router = Router()
logger = logging.getLogger(__name__)

for directory in [ANALYSIS_TEXT_DIR, ANALYSIS_AUDIO_DIR, ANALYSIS_VIDEO_DIR]:
    os.makedirs(directory, exist_ok=True)

@router.message(F.text, F.chat.type.in_({'group', 'supergroup', 'channel'}))
async def capture_group_text(message: Message):
    logger.info(f"Received text from chat_id={message.chat.id}, type={message.chat.type}")

    if message.text and message.text.startswith('/'):
        logger.info(f"Skipping command: {message.text}")
        return

    from database.group_messages import save_group_message
    username = message.from_user.username if message.from_user else 'Unknown'

    await save_group_message(
        message_id=message.message_id,
        message_type='text',
        content=message.text,
        username=username
    )
    logger.info(f"✅ Captured text message {message.message_id} from group {message.chat.id}")

@router.message(F.voice | F.audio, F.chat.type.in_({'group', 'supergroup', 'channel'}))
async def capture_group_audio(message: Message):
    logger.info(f"Received audio from chat_id={message.chat.id}, type={message.chat.type}")

    from database.group_messages import save_group_message
    username = message.from_user.username if message.from_user else 'Unknown'
    audio = message.voice or message.audio
    await save_group_message(
        message_id=message.message_id,
        message_type='audio',
        file_id=audio.file_id,
        username=username
    )
    logger.info(f"✅ Captured audio message {message.message_id} from group {message.chat.id}")

@router.message(F.video | F.video_note, F.chat.type.in_({'group', 'supergroup', 'channel'}))
async def capture_group_video(message: Message):
    logger.info(f"Received video from chat_id={message.chat.id}, type={message.chat.type}")

    from database.group_messages import save_group_message
    username = message.from_user.username if message.from_user else 'Unknown'
    video = message.video or message.video_note
    await save_group_message(
        message_id=message.message_id,
        message_type='video',
        file_id=video.file_id,
        username=username
    )
    logger.info(f"✅ Captured video message {message.message_id} from group {message.chat.id}")

async def process_analysis_task(message: Message, bot):
    from database.analysis import save_analysis_text, save_analysis_audio, save_analysis_video, clear_analysis_data
    from database.group_messages import get_unprocessed_messages, mark_message_processed
    from utils.audio_transcription import transcribe_audio
    from utils.translator import translate_ru_to_uk_en

    await clear_analysis_data()

    messages = await get_unprocessed_messages()

    if not messages:
        await message.answer("❌ Нет новых сообщений для обработки.")
        return

    text_count = 0
    audio_count = 0
    video_count = 0

    try:
        await message.answer("📝 Обрабатываю текстовые сообщения с переводом...")

        for msg in messages:
            if msg['message_type'] == 'text':
                text_count += 1
                
                logger.info(f"📝 Translating text {msg['message_id']}: RU → UK, EN")
                translations = await translate_ru_to_uk_en(msg['content'])
                logger.info(f"✅ Translation complete for text {msg['message_id']}")

                filename_base = f"text_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                filepath_ru = os.path.join(ANALYSIS_TEXT_DIR, f"{filename_base}_ru.txt")
                with open(filepath_ru, 'w', encoding='utf-8') as f:
                    f.write(f"Message ID: {msg['message_id']}\n")
                    f.write(f"Date: {msg['timestamp']}\n")
                    f.write(f"From: {msg['username']}\n")
                    f.write(f"Language: Russian\n\n")
                    f.write(msg['content'])

                if translations['uk']:
                    filepath_uk = os.path.join(ANALYSIS_TEXT_DIR, f"{filename_base}_uk.txt")
                    with open(filepath_uk, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg['message_id']}\n")
                        f.write(f"Date: {msg['timestamp']}\n")
                        f.write(f"From: {msg['username']}\n")
                        f.write(f"Language: Ukrainian\n\n")
                        f.write(translations['uk'])

                if translations['en']:
                    filepath_en = os.path.join(ANALYSIS_TEXT_DIR, f"{filename_base}_en.txt")
                    with open(filepath_en, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg['message_id']}\n")
                        f.write(f"Date: {msg['timestamp']}\n")
                        f.write(f"From: {msg['username']}\n")
                        f.write(f"Language: English\n\n")
                        f.write(translations['en'])

                await save_analysis_text(
                    msg['message_id'],
                    msg['content'],
                    filename_base,
                    text_ru=msg['content'],
                    text_uk=translations['uk'],
                    text_en=translations['en']
                )
                await mark_message_processed(msg['message_id'])

                if text_count % 5 == 0:
                    await message.answer(f"📝 Обработано текстов: {text_count}")

        await message.answer(f"✅ Тексты обработаны: {text_count}\n\n🎤 Обрабатываю аудио с переводом...")

        for msg in messages:
            if msg['message_type'] == 'audio':
                audio_count += 1
                temp_filename = f"temp_audio_{msg['message_id']}.ogg"

                try:
                    file = await bot.get_file(msg['file_id'])

                    if file.file_size and file.file_size > 20 * 1024 * 1024:
                        logger.warning(f"Audio {msg['message_id']} too big, skipping")
                        await mark_message_processed(msg['message_id'])
                        continue

                    await bot.download_file(file.file_path, temp_filename)
                    transcription = await transcribe_audio(temp_filename)

                    logger.info(f"🎤 Translating audio {msg['message_id']}: RU → UK, EN")
                    translations = await translate_ru_to_uk_en(transcription)
                    logger.info(f"✅ Translation complete for audio {msg['message_id']}")

                    filename_base = f"audio_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    filepath_ru = os.path.join(ANALYSIS_AUDIO_DIR, f"{filename_base}_ru.txt")
                    with open(filepath_ru, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg['message_id']}\n")
                        f.write(f"Date: {msg['timestamp']}\n")
                        f.write(f"From: {msg['username']}\n")
                        f.write(f"Language: Russian\n\n")
                        f.write(transcription)

                    if translations['uk']:
                        filepath_uk = os.path.join(ANALYSIS_AUDIO_DIR, f"{filename_base}_uk.txt")
                        with open(filepath_uk, 'w', encoding='utf-8') as f:
                            f.write(f"Message ID: {msg['message_id']}\n")
                            f.write(f"Date: {msg['timestamp']}\n")
                            f.write(f"From: {msg['username']}\n")
                            f.write(f"Language: Ukrainian\n\n")
                            f.write(translations['uk'])

                    if translations['en']:
                        filepath_en = os.path.join(ANALYSIS_AUDIO_DIR, f"{filename_base}_en.txt")
                        with open(filepath_en, 'w', encoding='utf-8') as f:
                            f.write(f"Message ID: {msg['message_id']}\n")
                            f.write(f"Date: {msg['timestamp']}\n")
                            f.write(f"From: {msg['username']}\n")
                            f.write(f"Language: English\n\n")
                            f.write(translations['en'])

                    await save_analysis_audio(
                        msg['message_id'],
                        transcription,
                        filename_base,
                        transcription_ru=transcription,
                        transcription_uk=translations['uk'],
                        transcription_en=translations['en']
                    )
                    await mark_message_processed(msg['message_id'])

                    if audio_count % 3 == 0:
                        await message.answer(f"🎤 Обработано аудио: {audio_count}")

                except Exception as e:
                    logger.error(f"Error processing audio {msg['message_id']}: {e}")
                    await mark_message_processed(msg['message_id'])
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

        await message.answer(f"✅ Аудио обработаны: {audio_count}\n\n🎥 Обрабатываю видео с переводом...")

        for msg in messages:
            if msg['message_type'] == 'video':
                video_count += 1
                temp_filename = f"temp_video_{msg['message_id']}.mp4"

                try:
                    file = await bot.get_file(msg['file_id'])

                    if file.file_size and file.file_size > 20 * 1024 * 1024:
                        logger.warning(f"Video {msg['message_id']} too big, skipping")
                        await mark_message_processed(msg['message_id'])
                        continue

                    await bot.download_file(file.file_path, temp_filename)
                    transcription = await transcribe_audio(temp_filename)

                    logger.info(f"🎥 Translating video {msg['message_id']}: RU → UK, EN")
                    translations = await translate_ru_to_uk_en(transcription)
                    logger.info(f"✅ Translation complete for video {msg['message_id']}")

                    filename_base = f"video_{msg['message_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    filepath_ru = os.path.join(ANALYSIS_VIDEO_DIR, f"{filename_base}_ru.txt")
                    with open(filepath_ru, 'w', encoding='utf-8') as f:
                        f.write(f"Message ID: {msg['message_id']}\n")
                        f.write(f"Date: {msg['timestamp']}\n")
                        f.write(f"From: {msg['username']}\n")
                        f.write(f"Language: Russian\n\n")
                        f.write(transcription)

                    if translations['uk']:
                        filepath_uk = os.path.join(ANALYSIS_VIDEO_DIR, f"{filename_base}_uk.txt")
                        with open(filepath_uk, 'w', encoding='utf-8') as f:
                            f.write(f"Message ID: {msg['message_id']}\n")
                            f.write(f"Date: {msg['timestamp']}\n")
                            f.write(f"From: {msg['username']}\n")
                            f.write(f"Language: Ukrainian\n\n")
                            f.write(translations['uk'])

                    if translations['en']:
                        filepath_en = os.path.join(ANALYSIS_VIDEO_DIR, f"{filename_base}_en.txt")
                        with open(filepath_en, 'w', encoding='utf-8') as f:
                            f.write(f"Message ID: {msg['message_id']}\n")
                            f.write(f"Date: {msg['timestamp']}\n")
                            f.write(f"From: {msg['username']}\n")
                            f.write(f"Language: English\n\n")
                            f.write(translations['en'])

                    await save_analysis_video(
                        msg['message_id'],
                        transcription,
                        filename_base,
                        transcription_ru=transcription,
                        transcription_uk=translations['uk'],
                        transcription_en=translations['en']
                    )
                    await mark_message_processed(msg['message_id'])

                    if video_count % 3 == 0:
                        await message.answer(f"🎥 Обработано видео: {video_count}")

                except Exception as e:
                    logger.error(f"Error processing video {msg['message_id']}: {e}")
                    await mark_message_processed(msg['message_id'])
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

        await message.answer(f"✅ Анализ завершен!\n\n📊 Итого:\n📝 Тексты: {text_count}\n🎤 Аудио: {audio_count}\n🎥 Видео: {video_count}\n\nВсе материалы переведены на украинский и английский языки.")

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при анализе: {e}")

@router.message(Command("startanal"))
async def cmd_start_analysis(message: Message, bot):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer("🔍 Начинаю анализ в фоновом режиме. Бот продолжит работать.")
    
    import asyncio
    asyncio.create_task(process_analysis_task(message, bot))

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
        f"Your ID: {message.from_user.id}"
    )