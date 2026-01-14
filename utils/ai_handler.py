import json
import asyncio
import logging
from g4f.client import Client
from g4f.Provider import RetryProvider
import g4f

from config import SYSTEM_PROMPT, AI_CONFIDENCE_THRESHOLD, UNIVERSAL_RESPONSE
from database import get_messages, get_faq, get_ai_learning, get_user, get_forbidden_topics_from_db
from database.analysis import get_all_analysis_texts, get_all_analysis_audios, get_all_analysis_videos

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

async def build_context_prompt(user_id, question, is_in_groups=False):
    user = await get_user(user_id)
    history = await get_messages(user_id, limit=15)
    
    status = user['status']
    if status in ['new', 'chatting', 'waiting_photos', 'asking_work_hours', 'asking_experience']:
        category = 'new'
    elif status in ['helping_registration', 'waiting_screenshot']:
        category = 'registration'
    elif status in ['registered', 'approved']:
        category = 'working'
    else:
        category = 'new'
    
    faq = await get_faq(category=category)
    learning = await get_ai_learning()
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    faq_text = "\n".join([f"Q: {f['question']}\nA: {f['answer']}" for f in faq[:30]])
    learning_text = "\n".join([f"Q: {l['question']}\nA: {l['answer']} (confidence: {l['confidence']})" for l in learning[:10]])
    
    group_status = "ЕСТЬ В ГРУППАХ (можно отвечать на рабочие вопросы)" if is_in_groups else "НЕТ В ГРУППАХ (только регистрация)"
    
    last_messages = history[-5:] if len(history) >= 5 else history
    recent_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in last_messages])
    
    training_materials = ""
    if is_in_groups:
        texts = await get_all_analysis_texts()
        audios = await get_all_analysis_audios()
        videos = await get_all_analysis_videos()
        
        if texts or audios or videos:
            training_materials = "\n\nОБУЧАЮЩИЕ МАТЕРИАЛЫ ИЗ ГРУППЫ:\n"
            
            if texts:
                training_materials += "\nТЕКСТОВЫЕ МАТЕРИАЛЫ:\n"
                for text in texts[:20]:
                    training_materials += f"{text['text'][:500]}\n...\n"
            
            if audios:
                training_materials += "\nТРАНСКРИПЦИИ АУДИО:\n"
                for audio in audios[:10]:
                    training_materials += f"{audio['transcription'][:500]}\n...\n"
            
            if videos:
                training_materials += "\nТРАНСКРИПЦИИ ВИДЕО:\n"
                for video in videos[:10]:
                    training_materials += f"{video['transcription'][:500]}\n...\n"
    
    context_prompt = f"""
СТАТУС ПОЛЬЗОВАТЕЛЯ: {user['status']}
СТАТУС УЧАСТИЯ: {group_status}

ПОСЛЕДНИЕ СООБЩЕНИЯ (ВАЖНО ДЛЯ КОНТЕКСТА):
{recent_context}

ПОЛНАЯ ИСТОРИЯ ДИАЛОГА:
{history_text}

БАЗА ЗНАНИЙ (FAQ):
{faq_text}

ОБУЧЕННЫЕ ОТВЕТЫ:
{learning_text}
{training_materials}

ТЕКУЩИЙ ВОПРОС:
{question}

ИНСТРУКЦИЯ:
1. ВНИМАТЕЛЬНО прочитай последние 3-5 сообщений - это контекст текущего разговора
2. Если вопрос связан с предыдущим сообщением (например "просто ждать?" после "аккаунт активируют") - отвечай сам с высокой confidence
3. Проверь, есть ли точный ответ в FAQ
4. Проверь обученные ответы
5. Если девушка ЕСТЬ в группе - используй обучающие материалы для ответа
6. Если это простая эмоция (супер, класс, ок) - отвечай поддерживающе с confidence 90+
7. Если это уточняющий вопрос в контексте диалога - отвечай с confidence 80+
8. Если девушки НЕТ в группах - отвечай только на вопросы о регистрации
9. Если девушка ЕСТЬ в группах - можешь отвечать на любые рабочие вопросы, используя обучающие материалы
10. Эскалируй только если ДЕЙСТВИТЕЛЬНО не знаешь ответа или это новая сложная тема
11. Ответ должен быть в стиле менеджера Valencia
"""
    
    return context_prompt

async def check_faq_direct_match(question):
    q_lower = question.lower().strip()
    
    detailed_info = """Приветик

🌟 РАБОТА СТРИМ-МОДЕЛЬЮ В ПРИЛОЖЕНИИ HALO 🌟

💬 Заработок на общении, прямых эфирах и приватных видеозвонках с мужчинами
📞 1 минута общения = 1$
💳 Комиссия агентства — 20%
👉 Чистый доход: 0.8$ за минуту

💰 Примеры заработка в звонках:
— 5 минут общения = 5$ → 4$ чистыми
— 10 минут = 10$ → 8$ чистыми
— 30 минут = 30$ → 24$ чистыми
— 1 час звонков = 60$ → 48$ чистыми

💵 От 50$ в день при активной работе

🌍 Аудитория: США, Европа, Англия, ОАЭ, арабские страны
👨‍💼 Многие мужчины приходят именно за общением, а не за 🔞
🌐 Встроенный переводчик — английский не обязателен
🕒 Свободный график — работаешь, когда удобно

🎤 В открытых эфирах — только культурное общение
Можно танцевать, петь, общаться, слушать музыку
💎 Важно выглядеть опрятно и презентабельно
❌ Никакой эротики и откровенной одежды — за нарушение бан

📞 В приватных звонках формат общения может быть любым — по взаимному согласию
— Каждая минута оплачивается
— Можно получать подарки
— Переводчик работает и в звонках
— Вас никто не слышит, кроме собеседника

📤 Вывод средств:
— Самостоятельно
— Срок: 1–3 дня
— Есть видео-инструкция, как вывести деньги на карту или крипту
— Если возникают сложности — помогаем с выводом

📸 Как начать:
Пришли 2–3 фото
— хорошее качество
— чётко видно лицо
(фото только для внутреннего одобрения)

⚠️ Важно:
🔹 Первые 7 дней — тестовый период
🔹 Нужно заработать 100$
🔹 У каждой девушки есть только одна возможность создать аккаунт. Если аккаунт блокируют — новый создать нельзя, поэтому выделяйте максимум времени для работы
🚀 Новеньких активно продвигают
❌ Тест не пройден — аккаунт блокируется

Если формат подходит — жду фото 👋"""
    
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
        'супер': 'Рада помочь! Если будут вопросы — обращайся 💪',
        'класс': 'Отлично! Всегда рада помочь 😊',
        'круто': '👍 Если что-то непонятно — пиши!',
        'есть работа для мужчин': 'К сожалению, нет. Мы работаем только с девушками 😊',
        'нужно ли показывать лицо': 'Да, лицо показывать обязательно. Это важно для общения с пользователями 😊',
        'в звонке что происходит': 'В приватном звонке ты общаешься 1 на 1 с мужчиной. Там может происходить что угодно по обоюдному согласию. За каждую минуту получаешь деньги 💰 Есть встроенный переводчик! 😊',
        'что происходит в звонке': 'В приватном звонке ты общаешься 1 на 1 с мужчиной. Там может происходить что угодно по обоюдному согласию. За каждую минуту получаешь деньги 💰 Есть встроенный переводчик! 😊',
        'в чем суть работы': 'Суть простая: находишься в онлайн-эфире (можно петь, танцевать, просто общаться), получаешь подарки и приглашения в приватные звонки. 1 минута звонка = 0.8$ + подарки! 💵',
        'суть работы': 'Суть простая: находишься в онлайн-эфире (можно петь, танцевать, просто общаться), получаешь подарки и приглашения в приватные звонки. 1 минута звонка = 0.8$ + подарки! 💵',
    }
    
    for key, answer in faq_direct.items():
        if key in q_lower or q_lower in key:
            return answer
    
    detailed_keywords = ['подробнее', 'больше информации', 'расскажи подробнее', 
                        'можно подробнее', 'хочу узнать больше', 'детальнее',
                        'дай больше информации', 'расскажи больше']
    if any(kw in q_lower for kw in detailed_keywords):
        return detailed_info
    
    waiting_keywords = ['просто ждать', 'мне просто ждать', 'мне ждать', 'просто жду',
                       'что дальше', 'и все', 'теперь жду']
    if any(kw in q_lower for kw in waiting_keywords):
        return 'Да, просто жди 😊 Активация обычно происходит на следующий будний день. Как только активируют — сможешь начать зарабатывать! 💪'
    
    agency_keywords = ['какое агентство', 'какого агента', 'агентство выбрать', 
                      'какое агенство', 'что за агентство', 'название агентства']
    if any(kw in q_lower for kw in agency_keywords):
        return 'В разделе Агентство выбирай: Tosagency-Ukraine 😊'
    
    age_keywords = ['возраст', 'сколько лет указать', '40 лет', '45 лет', '50 лет',
                   'большой возраст', 'мне много лет']
    if any(kw in q_lower for kw in age_keywords):
        return 'Ты можешь указать возраст чуть меньше реального, например 30-33 года. Это нормально 😊'
    
    country_keywords = ['страна', 'какую страну', 'казахстан', 'россия', 'беларусь',
                       'страну выбрать', 'какую страну указать']
    if any(kw in q_lower for kw in country_keywords):
        return 'Ты можешь выбрать любую страну во время регистрации, не обязательно свою. Выбери ту, что тебе больше нравится 😊'
    
    languages_keywords = ['языки', 'все языки', 'обязательно языки', 'какие языки',
                         'надо все языки', 'языки указывать']
    if any(kw in q_lower for kw in languages_keywords):
        return 'Да, указывай все языки: арабский, английский, украинский, русский. Это важно для алгоритма продвижения 😊'
    
    video_keywords = ['что говорить в видео', 'что записать', 'видео приветствие',
                     'что сказать', 'текст для видео']
    if any(kw in q_lower for kw in video_keywords):
        return 'Скажи: Hello, my name is [твоё имя]. I am [возраст] years old. I live in [страна]. I want to join. 😊'
    
    id_keywords = ['где найти id', 'как найти id', 'где id', 'найти айди',
                  'где мой id', 'как найти айди']
    if any(kw in q_lower for kw in id_keywords):
        return 'После регистрации в приложении зайди в свой профиль — там будет твой ID. Пришли скрин, где видно ID и название агентства 😊'
    
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
    
    work_age_keywords = ['со скольки лет', 'с какого возраста', 'сколько лет нужно']
    if any(kw in q_lower for kw in work_age_keywords):
        return 'С 16 лет можно начинать работу 👍'
    
    time_keywords = ['сколько времени нужно', 'сколько часов', 'минимум времени']
    if any(kw in q_lower for kw in time_keywords):
        return 'Минимум 4-6 часов в день для хорошего результата. Чем больше времени — тем больше заработок! 💪'
    
    app_download_keywords = ['не скачивается', 'не могу скачать', 'не скачивается приложение']
    if any(kw in q_lower for kw in app_download_keywords):
        return 'Попробуй зайти через другой браузер или очисти кэш. Если не помогает — перезагрузи телефон и попробуй ещё раз. Если проблема останется — напиши мне, я помогу разобраться! 😊'
    
    app_crash_keywords = ['приложение вылетает', 'вылетает', 'приложение закрывается', 'крашится']
    if any(kw in q_lower for kw in app_crash_keywords):
        return 'Попробуй переустановить приложение или обнови его до последней версии. Убедись, что на телефоне достаточно места. Если не поможет — напиши, помогу! 📱'
    
    video_record_keywords = ['не могу записать видео', 'не записывается видео', 'видео не записывается']
    if any(kw in q_lower for kw in video_record_keywords):
        return 'В приложении должна быть кнопка записи видео. Убедись, что разрешила доступ к камере и микрофону. Просто скажи: Hello, my name is [имя]. I am [возраст] years old. I live in [страна]. I want to join. 😊'
    
    return None

async def get_ai_response_with_retry(user_id, question, max_retries=2, is_in_groups=False):
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
            response = await get_ai_response(user_id, question, is_in_groups)
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

async def get_ai_response(user_id, question, is_in_groups=False):
    if await check_forbidden_topics(question):
        logger.info(f"Forbidden topic detected for user {user_id}")
        return {
            'answer': UNIVERSAL_RESPONSE,
            'confidence': 100,
            'escalate': False
        }
    
    logger.info(f"Building context for user {user_id}")
    context_prompt = await build_context_prompt(user_id, question, is_in_groups)
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
            
            simple_responses = ['привет', 'здравствуй', 'хорошо', 'спасибо', 'ок', 'понятно', 
                              'супер', 'класс', 'круто', 'отлично']
            q_lower = question.lower().strip()
            
            confidence = 85 if any(greeting in q_lower for greeting in simple_responses) else 60
            
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