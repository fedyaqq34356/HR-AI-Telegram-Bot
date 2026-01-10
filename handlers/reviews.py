import os
import logging
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

router = Router()
logger = logging.getLogger(__name__)

REVIEWS_FOLDER = 'goods'

REVIEW_FILES = [
    'review_testimonial_1.jpg',
    'review_success_2.jpg', 
    'review_earnings_3.jpg',
    'review_feedback_4.jpg',
    'review_rating_5.jpg',
    'review_experience_6.jpg',
    'review_satisfaction_7.jpg',
    'review_recommendation_8.jpg',
    'review_results_9.jpg',
    'review_achievement_10.jpg'
]

REVIEW_KEYWORDS = [
    'отзыв', 'отзывы', 'отзывами',
    'реальн', 'правда', 'работает',
    'кто работал', 'кто работает',
    'девочки зарабатывают', 'можно ли доверять',
    'это правда', 'это реально'
]

def is_review_request(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in REVIEW_KEYWORDS)

async def send_reviews(message: Message):
    try:
        if not os.path.exists(REVIEWS_FOLDER):
            logger.error(f"Reviews folder '{REVIEWS_FOLDER}' does not exist")
            await message.answer("Конечно! У нас много довольных девочек, которые успешно работают 😊")
            return
        
        existing_reviews = []
        for filename in REVIEW_FILES:
            filepath = os.path.join(REVIEWS_FOLDER, filename)
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    existing_reviews.append(filepath)
                else:
                    logger.warning(f"File {filepath} is empty, skipping")
        
        if not existing_reviews:
            logger.warning(f"No valid review files found in {REVIEWS_FOLDER}")
            await message.answer("Конечно! У нас много довольных девочек, которые успешно работают 😊")
            return
        
        logger.info(f"Found {len(existing_reviews)} valid review files")
        
        await message.answer("Конечно! Вот отзывы наших девочек 😊")
        
        sent_count = 0
        for filepath in existing_reviews:
            try:
                await message.answer_photo(FSInputFile(filepath))
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send photo {filepath}: {e}")
                continue
        
        if sent_count > 0:
            await message.answer("Вот такие результаты у наших моделей! Готова присоединиться? 💪")
            logger.info(f"Sent {sent_count} reviews to user {message.from_user.id}")
        else:
            await message.answer("Конечно! У нас много довольных девочек, которые успешно работают 😊")
        
    except Exception as e:
        logger.error(f"Error sending reviews: {e}", exc_info=True)
        await message.answer("Конечно! У нас много довольных девочек, которые успешно работают 😊")