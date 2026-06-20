import aiosqlite
from config import DB_PATH

async def save_photo(user_id, file_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO photos (user_id, file_id) VALUES (?, ?)',
            (user_id, file_id)
        )
        await db.execute(
            'UPDATE users SET photos_count = photos_count + 1 WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()

async def get_photos(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT file_id FROM photos WHERE user_id = ? ORDER BY timestamp',
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()