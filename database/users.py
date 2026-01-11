import aiosqlite
from datetime import datetime
from config import DB_PATH

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id, username):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO users (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        await db.commit()

async def update_user_status(user_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET status = ?, last_activity = ? WHERE user_id = ?',
            (status, datetime.now(), user_id)
        )
        await db.commit()

async def get_all_users_list():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT user_id, username, status FROM users ORDER BY last_activity DESC') as cursor:
            return await cursor.fetchall()

async def is_user_in_groups(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT in_groups FROM users WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result and result[0] == 1

async def add_user_to_groups(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET in_groups = 1 WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            total = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM users WHERE status="approved"') as cursor:
            approved = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM users WHERE status="rejected"') as cursor:
            rejected = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM users WHERE status="pending_review"') as cursor:
            pending = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM users WHERE status="registered"') as cursor:
            registered = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM ai_learning WHERE source="admin"') as cursor:
            admin_answers = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT COUNT(*) FROM ai_learning WHERE source="auto"') as cursor:
            auto_answers = (await cursor.fetchone())[0]
        
        async with db.execute('SELECT AVG(confidence) FROM ai_learning WHERE source="auto"') as cursor:
            avg_confidence = (await cursor.fetchone())[0] or 0
        
        return {
            'total': total,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'registered': registered,
            'admin_answers': admin_answers,
            'auto_answers': auto_answers,
            'avg_confidence': round(avg_confidence, 1)
        }