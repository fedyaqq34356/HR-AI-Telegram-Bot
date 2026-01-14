import aiosqlite
from config import DB_PATH

async def save_analysis_text(message_id, text, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO analysis_texts (message_id, text, filename) VALUES (?, ?, ?)',
            (message_id, text, filename)
        )
        await db.commit()

async def save_analysis_audio(message_id, transcription, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO analysis_audios (message_id, transcription, filename) VALUES (?, ?, ?)',
            (message_id, transcription, filename)
        )
        await db.commit()

async def save_analysis_video(message_id, transcription, filename):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO analysis_videos (message_id, transcription, filename) VALUES (?, ?, ?)',
            (message_id, transcription, filename)
        )
        await db.commit()

async def get_all_analysis_texts():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_texts ORDER BY timestamp') as cursor:
            return await cursor.fetchall()

async def get_all_analysis_audios():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_audios ORDER BY timestamp') as cursor:
            return await cursor.fetchall()

async def get_all_analysis_videos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM analysis_videos ORDER BY timestamp') as cursor:
            return await cursor.fetchall()

async def clear_analysis_data():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM analysis_texts')
        await db.execute('DELETE FROM analysis_audios')
        await db.execute('DELETE FROM analysis_videos')
        await db.commit()