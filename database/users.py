import aiosqlite
from datetime import datetime
from config import DB_PATH

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id, username, language='ru'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO users (user_id, username, language) VALUES (?, ?, ?)',
            (user_id, username, language)
        )
        await db.commit()

async def update_user_status(user_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET status = ?, last_activity = ? WHERE user_id = ?',
            (status, datetime.now(), user_id)
        )
        await db.commit()

async def update_user_language(user_id, language):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET language = ? WHERE user_id = ?',
            (language, user_id)
        )
        await db.commit()

async def get_all_users_list(page=1, per_page=10, show_hidden=False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        offset = (page - 1) * per_page
        if show_hidden:
            async with db.execute(
                'SELECT user_id, username, status FROM users ORDER BY last_activity DESC LIMIT ? OFFSET ?',
                (per_page, offset)
            ) as cursor:
                return await cursor.fetchall()
        else:
            async with db.execute(
                'SELECT user_id, username, status FROM users WHERE hidden_at IS NULL ORDER BY last_activity DESC LIMIT ? OFFSET ?',
                (per_page, offset)
            ) as cursor:
                return await cursor.fetchall()

async def get_users_count(show_hidden=False):
    async with aiosqlite.connect(DB_PATH) as db:
        if show_hidden:
            async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
        else:
            async with db.execute('SELECT COUNT(*) FROM users WHERE hidden_at IS NULL') as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

async def delete_user_conversation(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
        await db.execute('DELETE FROM pending_questions WHERE user_id = ?', (user_id,))
        await db.commit()

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

async def hide_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET hidden_at = ? WHERE user_id = ?',
            (datetime.now(), user_id)
        )
        await db.commit()

async def unhide_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET hidden_at = NULL WHERE user_id = ?',
            (user_id,)
        )
        await db.commit()

async def unhide_user_on_activity(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET hidden_at = NULL, last_activity = ? WHERE user_id = ? AND hidden_at IS NOT NULL',
            (datetime.now(), user_id)
        )
        await db.commit()

async def has_bot_responded(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT 1 FROM messages WHERE user_id = ? AND role = ? LIMIT 1',
            (user_id, 'bot')
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

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