import asyncio
import logging
from datetime import datetime, timedelta
import aiosqlite
from config import DB_PATH

logger = logging.getLogger(__name__)

REGISTRATION_TIMEOUT_MINUTES = 60
REGISTERED_TIMEOUT_HOURS = 8
CHECK_INTERVAL_SECONDS = 300

REGISTRATION_STATUSES = ['new', 'chatting', 'waiting_photos', 'asking_work_hours', 'asking_experience', 'pending_review', 'helping_registration', 'waiting_screenshot', 'waiting_admin']
REGISTERED_STATUSES = ['registered', 'approved']

async def auto_hide_inactive_users():
    while True:
        try:
            now = datetime.now()
            reg_cutoff = now - timedelta(minutes=REGISTRATION_TIMEOUT_MINUTES)
            reg_cutoff_str = reg_cutoff.strftime('%Y-%m-%d %H:%M:%S')
            registered_cutoff = now - timedelta(hours=REGISTERED_TIMEOUT_HOURS)
            registered_cutoff_str = registered_cutoff.strftime('%Y-%m-%d %H:%M:%S')

            async with aiosqlite.connect(DB_PATH) as db:
                placeholders_reg = ','.join(['?' for _ in REGISTRATION_STATUSES])
                cursor = await db.execute(
                    f'''UPDATE users SET hidden_at = ?
                        WHERE hidden_at IS NULL
                        AND status IN ({placeholders_reg})
                        AND last_activity < ?''',
                    (now.strftime('%Y-%m-%d %H:%M:%S'), *REGISTRATION_STATUSES, reg_cutoff_str)
                )
                reg_hidden = cursor.rowcount

                placeholders_act = ','.join(['?' for _ in REGISTERED_STATUSES])
                cursor = await db.execute(
                    f'''UPDATE users SET hidden_at = ?
                        WHERE hidden_at IS NULL
                        AND status IN ({placeholders_act})
                        AND last_activity < ?''',
                    (now.strftime('%Y-%m-%d %H:%M:%S'), *REGISTERED_STATUSES, registered_cutoff_str)
                )
                act_hidden = cursor.rowcount

                await db.commit()

                if reg_hidden > 0:
                    logger.info(f"Auto-hide: {reg_hidden} registration users hidden (>{REGISTRATION_TIMEOUT_MINUTES}min inactive)")
                if act_hidden > 0:
                    logger.info(f"Auto-hide: {act_hidden} registered users hidden (>{REGISTERED_TIMEOUT_HOURS}h inactive)")

        except Exception as e:
            logger.error(f"Auto-hide task error: {e}", exc_info=True)

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)