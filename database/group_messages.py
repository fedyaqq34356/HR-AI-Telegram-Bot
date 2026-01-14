import aiosqlite
from config import DB_PATH

async def save_group_message(message_id, message_type, content=None, file_id=None, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO group_messages (message_id, message_type, content, file_id, username) VALUES (?, ?, ?, ?, ?)',
            (message_id, message_type, content, file_id, username)
        )
        await db.commit()

async def get_unprocessed_messages():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM group_messages WHERE processed = 0 ORDER BY timestamp') as cursor:
            return await cursor.fetchall()

async def mark_message_processed(message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE group_messages SET processed = 1 WHERE message_id = ?', (message_id,))
        await db.commit()

async def get_all_group_messages():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM group_messages ORDER BY timestamp') as cursor:
            return await cursor.fetchall()

async def clear_group_messages():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM group_messages')
        await db.commit()