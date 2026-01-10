import json
import asyncio
import logging
from g4f.client import Client
from g4f.Provider import RetryProvider
import g4f

from config import SYSTEM_PROMPT, AI_CONFIDENCE_THRESHOLD, UNIVERSAL_RESPONSE
from database import get_messages, get_faq, get_ai_learning, get_user, get_forbidden_topics_from_db

logger = logging.getLogger(__name__)

all_providers = [
    provider for provider in g4f.Provider.__providers__ 
    if provider.working
]

client = Client(
    provider=RetryProvider(all_providers, shuffle=True)
)

async def check_forbidden_topics(message):
    msg_lower = message.lower()
    topics = await get_forbidden_topics_from_db()
    
    for topic in topics:
        keywords = json.loads(topic['keywords'])
        for keyword in keywords:
            if keyword.lower() in msg_lower:
                return True
    return False

async def build_context_prompt(user_id, question):
    user = await get_user(user_id)
    history = await get_messages(user_id, limit=10)
    
    status = user['status']
    if status in ['new', 'chatting', 'waiting_photos', 'asking_work_hours', 'asking_experience']:
        category = 'new'
    elif status in ['registered', 'approved', 'waiting_screenshot']:
        category = 'working'
    else:
        category = 'new'
    
    faq = await get_faq(category=category)
    learning = await get_ai_learning()
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    faq_text = "\n".join([f"Q: {f['question']}\nA: {f['answer']}" for f in faq[:15]])
    
    learning_text = "\n".join([f"Q: {l['question']}\nA: {l['answer']} (confidence: {l['confidence']})" for l in learning[:10]])
    
    context_prompt = f"""
СТАТУС ПОЛЬЗОВАТЕЛЯ: {user['status']}

ИСТОРИЯ ДИАЛОГА:
{history_text}

БАЗА ЗНАНИЙ (FAQ):
{faq_text}

ОБУЧЕННЫЕ ОТВЕТЫ:
{learning_text}

ТЕКУЩИЙ ВОПРОС:
{question}

ИНСТРУКЦИЯ:
1. Проверь, есть ли точный ответ в FAQ
2. Проверь обученные ответы
3. Если уверен на 80%+ — ответь
4. Если нет — верни escalate: true
5. Ответ должен быть в стиле менеджера Valencia
"""
    
    return context_prompt

async def check_faq_direct_match(question):
    q_lower = question.lower().strip()
    
    faq_direct = {
        'привет': 'Привет! Чем могу помочь? 😊',
        'здравствуй': 'Здравствуй! Рада тебя видеть! Есть вопросы? 😊',
        'как дела': 'Отлично, помогаю девочкам разобраться с регистрацией! У тебя как? 😊',
        'что делаешь': 'Работаю, консультирую новеньких по Halo. А ты готова начать? 💪',
        'кто ты': 'Я менеджер агентства Valencia, помогаю девочкам начать работу в Halo 😊',
        'хорошо': 'Отлично! Если что-то непонятно — обращайся 👍',
        'понятно': 'Супер! Рада, что помогла 😊',
        'спасибо': 'Пожалуйста! Если будут ещё вопросы — пиши 😊',
        'ок': 'Отлично! Я всегда на связи 😊',
        'есть работа для мужчин': 'К сожалению, нет. Мы работаем только с девушками 😊',
        'нужно ли показывать лицо': 'Да, лицо показывать обязательно. Это важно для общения с пользователями 😊',
    }
    
    for key, answer in faq_direct.items():
        if key in q_lower or q_lower in key:
            return answer
    
    registration_keywords = ['как зарегистрироваться', 'как зарегаться', 'как регистрироваться', 
                            'как зарегестрироваться', 'регистрация', 'зарегаться']
    if any(kw in q_lower for kw in registration_keywords):
        return 'Сначала пришли мне 2-3 своих фото для одобрения офисом. После одобрения я дам инструкцию по регистрации! 😊'
    
    money_keywords = ['как я зарабатываю', 'как зарабатывать', 'как заработать']
    if any(kw in q_lower for kw in money_keywords):
        return 'Ты общаешься с мужчиной в личном звонке и получаешь 0.8$ за 1 минуту общения + подарки 🎁 Также можешь вести прямые эфиры и получать заработок оттуда! 💰'
    
    earning_keywords = ['сколько можно зарабатывать', 'сколько зарабатывают', 'сколько девочки зарабатывают']
    if any(kw in q_lower for kw in earning_keywords):
        return 'Доход зависит от твоей активности и времени, которое ты готова уделять работе. В среднем девочки зарабатывают от 200$ до 1000$+ в неделю 💵'
    
    schedule_keywords = ['график', 'фиксированный график', 'когда работать']
    if any(kw in q_lower for kw in schedule_keywords):
        return 'Нет, график свободный! Ты сама выбираешь, когда работать 🕒'
    
    docs_keywords = ['нужны ли документы', 'документы', 'паспорт']
    if any(kw in q_lower for kw in docs_keywords):
        return 'Нет, документы не нужны ✅'
    
    age_keywords = ['со скольки лет', 'с какого возраста', 'сколько лет нужно']
    if any(kw in q_lower for kw in age_keywords):
        return 'С 16 лет можно начинать работу 👍'
    
    time_keywords = ['сколько времени нужно', 'сколько часов', 'минимум времени']
    if any(kw in q_lower for kw in time_keywords):
        return 'Минимум 4-6 часов в день для хорошего результата. Чем больше времени — тем больше заработок! 💪'
    
    return None

async def get_ai_response_with_retry(user_id, question, max_retries=2):
    logger.info(f"Starting AI request with retry for user {user_id}, max_retries={max_retries}")
    
    direct_answer = await check_faq_direct_match(question)
    if direct_answer:
        logger.info(f"Direct FAQ match found for user {user_id}")
        return {
            'answer': direct_answer,
            'confidence': 95,
            'escalate': False
        }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries} for user {user_id}")
            response = await get_ai_response(user_id, question)
            if response['confidence'] > 0 or response['escalate']:
                logger.info(f"AI response successful on attempt {attempt + 1} for user {user_id}")
                return response
            logger.warning(f"AI returned 0 confidence on attempt {attempt + 1} for user {user_id}")
        except asyncio.TimeoutError:
            logger.error(f"AI timeout on attempt {attempt + 1}/{max_retries} for user {user_id}")
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts timed out for user {user_id}, escalating")
                return {
                    'answer': '',
                    'confidence': 0,
                    'escalate': True
                }
        except Exception as e:
            logger.error(f"AI retry attempt {attempt + 1}/{max_retries} failed for user {user_id}: {e}", exc_info=True)
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed for user {user_id}, escalating")
                return {
                    'answer': '',
                    'confidence': 0,
                    'escalate': True
                }
            wait_time = 2
            logger.info(f"Waiting {wait_time}s before retry for user {user_id}")
            await asyncio.sleep(wait_time)
    
    logger.error(f"Exhausted all retries for user {user_id}, escalating")
    return {
        'answer': '',
        'confidence': 0,
        'escalate': True
    }

async def get_ai_response(user_id, question):
    if await check_forbidden_topics(question):
        logger.info(f"Forbidden topic detected for user {user_id}")
        return {
            'answer': UNIVERSAL_RESPONSE,
            'confidence': 100,
            'escalate': False
        }
    
    logger.info(f"Building context for user {user_id}")
    context_prompt = await build_context_prompt(user_id, question)
    logger.info(f"Context built for user {user_id}, calling AI...")
    
    try:
        logger.info(f"Sending request to AI for user {user_id}")
        
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model="",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context_prompt}
                ]
            ),
            timeout=30.0
        )
        
        logger.info(f"Received response from AI for user {user_id}")
        
        if response is None:
            logger.error(f"AI returned None response for user {user_id}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        if not hasattr(response, 'choices') or not response.choices:
            logger.error(f"AI response has no choices for user {user_id}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        content = response.choices[0].message.content
        
        if hasattr(content, 'strip'):
            content = content.strip()
        else:
            content = str(content).strip()
        
        if not content:
            logger.warning(f"Empty response from AI for user {user_id}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        logger.info(f"Raw AI response for user {user_id}: {content[:200]}")
        
        if content.startswith('```json'):
            content = content[7:-3].strip()
        elif content.startswith('```'):
            content = content[3:-3].strip()
        
        try:
            logger.info(f"Parsing JSON response for user {user_id}")
            result = json.loads(content)
            logger.info(f"JSON parsed successfully for user {user_id}")
        except json.JSONDecodeError:
            logger.warning(f"AI returned non-JSON text for user {user_id}: {content[:100]}")
            
            simple_greetings = ['привет', 'здравствуй', 'хорошо', 'спасибо', 'ок', 'понятно']
            q_lower = question.lower().strip()
            
            confidence = 85 if any(greeting in q_lower for greeting in simple_greetings) else 60
            
            logger.info(f"Non-JSON response, setting confidence to {confidence} for user {user_id}")
            return {
                'answer': content,
                'confidence': confidence,
                'escalate': confidence < AI_CONFIDENCE_THRESHOLD
            }
        
        if not isinstance(result, dict):
            logger.warning(f"AI returned non-dict result for user {user_id}")
            return {
                'answer': str(result),
                'confidence': 60,
                'escalate': False
            }
        
        if 'answer' not in result:
            result['answer'] = content
        if 'confidence' not in result:
            result['confidence'] = 50
        if 'escalate' not in result:
            result['escalate'] = result['confidence'] < AI_CONFIDENCE_THRESHOLD
        
        logger.info(f"AI response for user {user_id}: confidence={result['confidence']}, escalate={result['escalate']}, answer_length={len(result['answer'])}")
        
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"AI request timeout (30s) for user {user_id}")
        raise
    except Exception as e:
        logger.error(f"AI error for user {user_id}: {e}", exc_info=True)
        raise