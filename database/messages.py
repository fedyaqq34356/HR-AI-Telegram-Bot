import aiosqlite
from config import DB_PATH

async def save_message(user_id, role, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)',
            (user_id, role, content)
        )
        await db.commit()

async def get_messages(user_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT * FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return list(reversed(rows))

async def get_user_conversations(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT * FROM messages WHERE user_id = ? ORDER BY timestamp',
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def save_pending_question(user_id, question):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO pending_questions (user_id, question) VALUES (?, ?)',
            (user_id, question)
        )
        await db.commit()

async def get_pending_question(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT question FROM pending_questions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def delete_pending_question(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM pending_questions WHERE user_id = ?', (user_id,))
        await db.commit()