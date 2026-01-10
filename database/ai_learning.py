import aiosqlite
from config import DB_PATH

async def save_ai_learning(question, answer, source, confidence):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO ai_learning (question, answer, source, confidence) VALUES (?, ?, ?, ?)',
            (question, answer, source, confidence)
        )
        await db.commit()

async def get_ai_learning():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM ai_learning ORDER BY confidence DESC') as cursor:
            return await cursor.fetchall()