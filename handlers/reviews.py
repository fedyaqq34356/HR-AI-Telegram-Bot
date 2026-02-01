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

REVIEW_KEYWORDS = {
    'ru': [
        'отзыв', 'отзывы', 'отзывами',
        'реальн', 'правда', 'работает',
        'кто работал', 'кто работает',
        'девочки зарабатывают', 'можно ли доверять',
        'это правда', 'это реально'
    ],
    'uk': [
        'відгук', 'відгуки', 'відгуками',
        'реальн', 'правда', 'працює',
        'хто працював', 'хто працює',
        'дівчата заробляють', 'чи можна довіряти',
        'це правда', 'це реально'
    ],
    'en': [
        'review', 'reviews', 'testimonial',
        'real', 'truth', 'works',
        'who worked', 'who works',
        'girls earn', 'can trust',
        'is it true', 'is it real'
    ]
}

def is_review_request(text: str) -> bool:
    text_lower = text.lower()
    for lang_keywords in REVIEW_KEYWORDS.values():
        if any(keyword in text_lower for keyword in lang_keywords):
            return True
    return False

async def send_reviews(message: Message, user_lang='ru'):
    try:
        if not os.path.exists(REVIEWS_FOLDER):
            logger.error(f"Reviews folder '{REVIEWS_FOLDER}' does not exist")
            responses = {
                'ru': "Конечно! У нас много довольных девочек, которые успешно работают 😊",
                'uk': "Звичайно! У нас багато задоволених дівчат, які успішно працюють 😊",
                'en': "Of course! We have many satisfied girls who work successfully 😊"
            }
            await message.answer(responses.get(user_lang, responses['ru']))
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
            responses = {
                'ru': "Конечно! У нас много довольных девочек, которые успешно работают 😊",
                'uk': "Звичайно! У нас багато задоволених дівчат, які успішно працюють 😊",
                'en': "Of course! We have many satisfied girls who work successfully 😊"
            }
            await message.answer(responses.get(user_lang, responses['ru']))
            return
        
        logger.info(f"Found {len(existing_reviews)} valid review files")
        
        intro_texts = {
            'ru': "Конечно! Вот отзывы наших девочек 😊",
            'uk': "Звичайно! Ось відгуки наших дівчат 😊",
            'en': "Of course! Here are reviews from our girls 😊"
        }
        await message.answer(intro_texts.get(user_lang, intro_texts['ru']))
        
        sent_count = 0
        for filepath in existing_reviews:
            try:
                await message.answer_photo(FSInputFile(filepath))
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send photo {filepath}: {e}")
                continue
        
        if sent_count > 0:
            outro_texts = {
                'ru': "Вот такие результаты у наших моделей! Готова присоединиться? 💪",
                'uk': "Ось такі результати у наших моделей! Готова приєднатися? 💪",
                'en': "These are the results of our models! Ready to join? 💪"
            }
            await message.answer(outro_texts.get(user_lang, outro_texts['ru']))
            logger.info(f"Sent {sent_count} reviews to user {message.from_user.id}")
        else:
            responses = {
                'ru': "Конечно! У нас много довольных девочек, которые успешно работают 😊",
                'uk': "Звичайно! У нас багато задоволених дівчат, які успішно працюють 😊",
                'en': "Of course! We have many satisfied girls who work successfully 😊"
            }
            await message.answer(responses.get(user_lang, responses['ru']))
        
    except Exception as e:
        logger.error(f"Error sending reviews: {e}", exc_info=True)
        responses = {
            'ru': "Конечно! У нас много довольных девочек, которые успешно работают 😊",
            'uk': "Звичайно! У нас багато задоволених дівчат, які успішно працюють 😊",
            'en': "Of course! We have many satisfied girls who work successfully 😊"
        }
        await message.answer(responses.get(user_lang, responses['ru']))