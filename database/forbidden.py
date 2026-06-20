import aiosqlite
import json
from config import DB_PATH, FORBIDDEN_TOPICS

async def get_forbidden_topics_from_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM forbidden_topics') as cursor:
            return await cursor.fetchall()

async def add_forbidden_topic(topic, keywords):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO forbidden_topics (topic, keywords) VALUES (?, ?)',
            (topic, keywords)
        )
        await db.commit()

async def delete_forbidden_topic(topic_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM forbidden_topics WHERE id = ?', (topic_id,))
        await db.commit()

async def init_forbidden_topics():
    async with aiosqlite.connect(DB_PATH) as db:
        for topic_name, keywords in FORBIDDEN_TOPICS.items():
            await db.execute(
                'INSERT OR IGNORE INTO forbidden_topics (topic, keywords) VALUES (?, ?)',
                (topic_name, json.dumps(keywords))
            )
        await db.commit()