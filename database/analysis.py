import aiosqlite
from config import DB_PATH

async def save_analysis_text(message_id, text, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO analysis_text (message_id, text, filename)
            VALUES (?, ?, ?)
        ''', (message_id, text, filename))
        await db.commit()

async def save_analysis_audio(message_id, transcription, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO analysis_audio (message_id, transcription, filename)
            VALUES (?, ?, ?)
        ''', (message_id, transcription, filename))
        await db.commit()

async def save_analysis_video(message_id, transcription, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO analysis_video (message_id, transcription, filename)
            VALUES (?, ?, ?)
        ''', (message_id, transcription, filename))
        await db.commit()

async def save_analysis_sms(message_id, text, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO analysis_sms (message_id, text, filename)
            VALUES (?, ?, ?)
        ''', (message_id, text, filename))
        await db.commit()

async def get_all_analysis_texts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_text ORDER BY timestamp DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_analysis_audios():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_audio ORDER BY timestamp DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_analysis_videos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_video ORDER BY timestamp DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_analysis_sms():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_sms ORDER BY timestamp DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def clear_analysis_data():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM analysis_text')
        await db.execute('DELETE FROM analysis_audio')
        await db.execute('DELETE FROM analysis_video')
        await db.execute('DELETE FROM analysis_sms')
        await db.commit()