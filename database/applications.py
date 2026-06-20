import aiosqlite
from config import DB_PATH

async def create_application(user_id, work_hours, experience):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO applications (user_id, work_hours, previous_experience) VALUES (?, ?, ?)',
            (user_id, work_hours, experience)
        )
        await db.commit()

async def update_application_status(user_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE applications SET status = ? WHERE user_id = ? AND status = "pending"',
            (status, user_id)
        )
        await db.commit()