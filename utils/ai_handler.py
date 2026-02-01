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

COUNTRY_KEYWORDS = [
    'азербайджан', 'azerbaijan',
    'казахстан', 'kazakhstan',
    'грузия', 'georgia',
    'беларусь', 'belarus',
    'молдова', 'moldova',
    'армения', 'armenia',
    'узбекистан', 'uzbekistan',
    'туркменистан', 'turkmenistan',
    'таджикистан', 'tajikistan',
    'кыргызстан', 'kyrgyzstan',
    'латвия', 'латва', 'latvia',
    'литва', 'lithuania',
    'эстония', 'estonia',
    'польша', 'poland',
    'германия', 'germany',
    'франция', 'france',
    'италия', 'italy',
    'испания', 'spain',
    'турция', 'turkey',
    'израиль', 'israel',
    'финляндия', 'finland',
    'швеция', 'sweden',
    'норвегия', 'norway',
    'дания', 'denmark',
    'швейцария', 'switzerland',
    'австрия', 'austria',
    'бельгия', 'belgium',
    'нидерланды', 'netherlands',
    'греция', 'greece',
    'чехия', 'czech',
    'венгрия', 'hungary',
    'румыния', 'romania',
    'болгария', 'bulgaria',
    'сербия', 'serbia',
    'хорватия', 'croatia',
    'словакия', 'slovakia',
    'словения', 'slovenia',
    'эаэ', 'оае', 'uae',
    'сша', 'usa',
    'канада', 'canada',
    'австралия', 'australia',
    'япония', 'japan',
    'китай', 'china',
    'индия', 'india',
    'бразилия', 'brazil',
    'мексика', 'mexico',
    'аргентина', 'argentina',
    'южная корея', 'south korea',
    'иран', 'iran',
    'ирак', 'iraq',
    'саудовская', 'saudi',
    'кувейт', 'kuwait',
    'катар', 'qatar',
    'бахрейн', 'bahrain',
    'оман', 'oman',
    'україна', 'україна', 'ukraine',
    'россия', 'russia',
]

def detect_country_in_text(text):
    text_lower = text.lower()
    for country in COUNTRY_KEYWORDS:
        if country in text_lower:
            return country
    return None

def is_g4f_error(content):
    c = content.lower()
    if 'does not exist' in c and ('model' in c or 'https://' in c):
        return True
    if 'the model does not' in c:
        return True
    if c.startswith('error') and ('provider' in c or 'model' in c):
        return True
    return False

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
    from database.analysis import get_all_analysis_texts, get_all_analysis_audios, get_all_analysis_videos
    
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
            training_materials = "\n\nОБУЧАЮЩИЕ МАТЕРИАЛЫ:\n"
            
            if texts:
                training_materials += "\nТекстовые материалы:\n"
                for text in texts[:20]:
                    training_materials += f"{text['text'][:500]}\n...\n"
            
            if audios:
                training_materials += "\nАудио материалы (расшифровки):\n"
                for audio in audios[:10]:
                    training_materials += f"{audio['transcription'][:500]}\n...\n"
            
            if videos:
                training_materials += "\nВидео материалы (расшифровки):\n"
                for video in videos[:10]:
                    training_materials += f"{video['transcription'][:500]}\n...\n"
    
    user_lang = user['language'] if user and user['language'] else 'ru'
    lang_instruction = {
        'ru': "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.",
        'uk': "ВІДПОВІДАЙ ТІЛЬКИ УКРАЇНІЄЮ МОВОЮ.",
        'en': "RESPOND ONLY IN ENGLISH."
    }
    
    context_prompt = f"""
СТАТУС ПОЛЬЗОВАТЕЛЯ: {user['status']}
СТАТУС УЧАСТИЯ: {group_status}
ЯЗЫК ПОЛЬЗОВАТЕЛЯ: {user_lang}
{lang_instruction.get(user_lang, lang_instruction['ru'])}

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
2. Если вопрос связан с предыдущим сообщением - отвечай сам с высокой confidence (85+)
3. Проверь, есть ли точный ответ в FAQ
4. Проверь обученные ответы
5. Если девушка ЕСТЬ в группе - используй обучающие материалы для ответа
6. Если это простая эмоция (супер, класс, ок, добре) - отвечай поддерживающе с confidence 95+, НЕ ЭСКАЛИРУЙ
7. Если это уточняющий вопрос в контексте диалога - отвечай с confidence 90+
8. Если девушки НЕТ в группах - отвечай только на вопросы о регистрации
9. Если девушка ЕСТЬ в группах - можешь отвечать на любые рабочие вопросы, используя обучающие материалы
10. Эскалируй только если ДЕЙСТВИТЕЛЬНО не знаешь ответа или это новая сложная тема
11. Ответ должен быть в стиле менеджера Valencia
12. ЛЮБАЯ СТРАНА ПОДХОДИТ — если спрашивают про любую страну, отвечай что она подходит
13. ВСЕГДА отвечай на том же языке, что и пользователь ({user_lang})
"""
    
    return context_prompt

async def check_faq_direct_match(question, user_lang='ru'):
    q_lower = question.lower().strip()
    
    country = detect_country_in_text(q_lower)
    if country:
        country_display = country.capitalize()
        responses = {
            'ru': f"У нас работают девочки со всех стран! {country_display} подходит ✅ При регистрации можешь выбрать любую страну 😊",
            'uk': f"У нас працюють дівчата з усіх країн! {country_display} підходить ✅ При реєстрації можешь вибрати будь-яку країну 😊",
            'en': f"We have girls working from all countries! {country_display} works perfectly ✅ During registration you can choose any country 😊"
        }
        return responses.get(user_lang, responses['ru'])
    
    detailed_info = {
        'ru': """Приветик 😊

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

Если формат подходит — жду фото 👋""",
        'uk': """Привітик 😊

🌟 РОБОТА СТРІМ-МОДЕЛЛЮ В ЗАСТОСУНКУ HALO 🌟

💬 Заробіток на спілкуванні, прямих ефірах та приватних відеодзвінках з чоловіками
📞 1 хвилина спілкування = 1$
💳 Комісія агентства — 20%
👉 Чистий дохід: 0.8$ за хвилину

💰 Приклади заробітку в дзвінках:
— 5 хвилин спілкування = 5$ → 4$ чистими
— 10 хвилин = 10$ → 8$ чистими
— 30 хвилин = 30$ → 24$ чистими
— 1 година дзвінків = 60$ → 48$ чистими

💵 Від 50$ на день при активній роботі

🌍 Аудиторія: США, Європа, Англія, ОАЕ, арабські країни
👨‍💼 Багато чоловіків приходять саме за спілкуванням, а не за 🔞
🌐 Вбудований перекладач — англійська не обов'язкова
🕒 Вільний графік — працюєш, коли зручно

🎤 У відкритих ефірах — тільки культурне спілкування
Можна танцювати, співати, спілкуватися, слухати музику
💎 Важливо виглядати охайно і презентабельно
❌ Ніякої еротики та відвертого одягу — за порушення бан

📞 У приватних дзвінках формат спілкування може бути будь-яким — за взаємною згодою
— Кожна хвилина оплачується
— Можна отримувати подарунки
— Перекладач працює і в дзвінках
— Вас ніхто не чує, крім співрозмовника

📤 Виведення коштів:
— Самостійно
— Термін: 1–3 дні
— Є відео-інструкція, як вивести гроші на карту або крипту
— Якщо виникають складнощі — допомагаємо з виведенням

📸 Як почати:
Надішли 2–3 фото
— хороша якість
— чітко видно обличчя
(фото тільки для внутрішнього схвалення)

⚠️ Важливо:
🔹 Перші 7 днів — тестовий період
🔹 Потрібно заробити 100$
🔹 У кожної дівчини є тільки одна можливість створити акаунт. Якщо акаунт блокують — новий створити не можна, тому виділяйте максимум часу для роботи
🚀 Новеньких активно просувають
❌ Тест не пройдено — акаунт блокується

Якщо формат підходить — чекаю фото 👋""",
        'en': """Hello 😊

🌟 WORK AS A STREAM MODEL IN HALO APP 🌟

💬 Earn from chatting, live streams and private video calls with men
📞 1 minute of communication = 1$
💳 Agency commission — 20%
👉 Net income: 0.8$ per minute

💰 Examples of earnings in calls:
— 5 minutes of communication = 5$ → 4$ net
— 10 minutes = 10$ → 8$ net
— 30 minutes = 30$ → 24$ net
— 1 hour of calls = 60$ → 48$ net

💵 From 50$ per day with active work

🌍 Audience: USA, Europe, England, UAE, Arab countries
👨‍💼 Many men come for communication, not for 🔞
🌐 Built-in translator — English is not required
🕒 Free schedule — work when convenient

🎤 In open streams — only cultural communication
You can dance, sing, chat, listen to music
💎 Important to look neat and presentable
❌ No erotica and revealing clothing — violation = ban

📞 In private calls the format can be anything — by mutual consent
— Every minute is paid
— Can receive gifts
— Translator works in calls
— Nobody hears you except the interlocutor

📤 Withdrawal of funds:
— Independently
— Period: 1–3 days
— There is a video instruction on how to withdraw money to card or crypto
— If there are difficulties — we help with withdrawal

📸 How to start:
Send 2–3 photos
— good quality
— face clearly visible
(photos only for internal approval)

⚠️ Important:
🔹 First 7 days — trial period
🔹 Need to earn 100$
🔹 Each girl has only one opportunity to create an account. If account is blocked — cannot create new one, so dedicate maximum time to work
🚀 Newbies are actively promoted
❌ Test not passed — account is blocked

If the format suits — waiting for photos 👋"""
    }
    
    simple_reactions = {
        'ок': ('Отлично! 😊', 'Чудово! 😊', 'Great! 😊'),
        'окей': ('Супер! 👍', 'Супер! 👍', 'Perfect! 👍'),
        'хорошо': ('Отлично! 😊', 'Чудово! 😊', 'Excellent! 😊'),
        'добре': ('Чудово! 😊', 'Чудово! 😊', 'Great! 😊'),
        'понятно': ('Супер! 😊', 'Супер! 😊', 'Great! 😊'),
        'зрозуміло': ('Добре! 😊', 'Добре! 😊', 'Good! 😊'),
        'класс': ('Рада помочь! 😊', 'Рада допомогти! 😊', 'Happy to help! 😊'),
        'супер': ('👍', '👍', '👍'),
        'круто': ('🔥', '🔥', '🔥'),
        'отлично': ('💪', '💪', '💪'),
        'ясно': ('👌', '👌', '👌'),
        'чудово': ('😊', '😊', '😊'),
        'fine': ('Отлично! 😊', 'Чудово! 😊', 'Great! 😊'),
        'okay': ('Супер! 👍', 'Супер! 👍', 'Perfect! 👍'),
        'ok': ('Отлично! 😊', 'Чудово! 😊', 'Great! 😊'),
        'good': ('Супер! 😊', 'Супер! 😊', 'Nice! 😊'),
        'great': ('Отлично! 🔥', 'Чудово! 🔥', 'Awesome! 🔥'),
        'nice': ('👍', '👍', '👍'),
        'cool': ('😊', '😊', '😊')
    }
    
    for reaction, responses in simple_reactions.items():
        if q_lower == reaction:
            lang_index = {'ru': 0, 'uk': 1, 'en': 2}.get(user_lang, 0)
            return responses[lang_index]
    
    faq_direct = {
        'привет': ('Привет! Чем могу помочь? 😊', 'Привіт! Чим можу допомогти? 😊', 'Hi! How can I help? 😊'),
        'здравствуй': ('Здравствуй! Рада тебя видеть! Есть вопросы? 😊', 'Вітаю! Рада тебе бачити! Є питання? 😊', 'Hello! Nice to see you! Any questions? 😊'),
        'вітаю': ('Вітаю! Чим можу допомогти? 😊', 'Вітаю! Чим можу допомогти? 😊', 'Hi! How can I help? 😊'),
        'привіт': ('Привіт! Є питання? 😊', 'Привіт! Є питання? 😊', 'Hi! Any questions? 😊'),
        'як дела': ('Чудово! А у тебе як? 😊', 'Чудово! А у тебе як? 😊', 'Great! How are you? 😊'),
        'как дела': ('Отлично! У тебя как? 😊', 'Чудово! А у тебе як? 😊', 'Great! How are you? 😊'),
        'кто ты': ('Я менеджер агентства Valencia, помогаю девочкам начать работу в Halo 😊', 'Я менеджер агентства Valencia, допомагаю дівчатам почати роботу в Halo 😊', "I'm a Valencia agency manager, helping girls start working in Halo 😊"),
        'спасибо': ('Пожалуйста! 😊', 'Будь ласка! 😊', "You're welcome! 😊"),
        'дякую': ('Будь ласка! 😊', 'Будь ласка! 😊', "You're welcome! 😊"),
        'thanks': ('Пожалуйста! 😊', 'Будь ласка! 😊', "You're welcome! 😊"),
        'hi': ('Hi! How can I help? 😊', 'Привіт! Чим можу допомогти? 😊', 'Hi! How can I help? 😊'),
        'hello': ('Hello! How can I help? 😊', 'Привіт! Чим можу допомогти? 😊', 'Hello! How can I help? 😊')
    }
    
    for key, answers in faq_direct.items():
        if key in q_lower or q_lower in key:
            lang_index = {'ru': 0, 'uk': 1, 'en': 2}.get(user_lang, 0)
            return answers[lang_index]
    
    detailed_keywords = [
        'подробнее', 'больше информации', 'расскажи подробнее', 
        'детальніше', 'більше інформації', 'розкажи детальніше', 
        'more details', 'more information', 'tell me more',
        'про приложен', 'о приложени', 'about app',
        'інформаці', 'информаци', 'information',
        'можно информаци', 'можна інформаці', 'can i get info'
    ]
    
    if any(kw in q_lower for kw in detailed_keywords):
        return detailed_info.get(user_lang, detailed_info['ru'])
    
    waiting_keywords = [
        'просто ждать', 'мне просто ждать', 'мне ждать', 'просто жду', 'и все', 'теперь жду', 
        'просто чекати', 'мені чекати', 'просто чекаю', 'і все', 'тепер чекаю',
        'just wait', 'should i wait', 'wait now'
    ]
    
    if any(kw in q_lower for kw in waiting_keywords):
        responses = {
            'ru': 'Да, просто жди 😊 Активация обычно происходит на следующий будний день. Как только активируют — сможешь начать зарабатывать! 💪',
            'uk': 'Так, просто чекай 😊 Активація зазвичай відбувається наступного робочого дня. Як тільки активують — зможеш почати заробляти! 💪',
            'en': 'Yes, just wait 😊 Activation usually happens the next business day. Once activated — you can start earning! 💪'
        }
        return responses.get(user_lang, responses['ru'])
    
    return None

async def is_contextual_question(question, history):
    q_lower = question.lower().strip()
    
    what_to_do_variants = [
        'що мені робити', 'что мне делать', 'що робити', 'что делать',
        'що мені', 'что мне', 'що далі', 'что дальше', 
        'що тепер', 'что теперь', 'що зараз', 'что сейчас',
        'what should i do', 'what now', 'what next', 'what to do',
        'і що', 'и что', 'а що', 'а что', 'а тепер', 'а теперь',
        'що мені робити зараз', 'что мне делать сейчас'
    ]
    
    if not any(variant in q_lower for variant in what_to_do_variants):
        return None
    
    if not history or len(history) < 2:
        return None
    
    last_bot_messages = []
    count = 0
    for msg in reversed(history):
        if msg['role'] == 'bot' and count < 3:
            last_bot_messages.append(msg['content'].lower())
            count += 1
    
    if not last_bot_messages:
        return None
    
    instructions_keywords = [
        'інструкц', 'инструкц', 'instruction',
        'реєстр', 'регистр', 'registr',
        'надішли', 'пришли', 'send',
        'скрин', 'screenshot',
        'активуют', 'активують', 'activate',
        'офіс', 'офис', 'office',
        'фото', 'photo',
        'тестовий період', 'тестовый период',
        'заробити', 'заработать'
    ]
    
    for bot_msg in last_bot_messages:
        if any(kw in bot_msg for kw in instructions_keywords):
            if 'скрин' in bot_msg or 'screenshot' in bot_msg or 'офіс' in bot_msg or 'офис' in bot_msg:
                return {
                    'ru': 'Просто жди активации от офиса. Обычно это происходит на следующий будний день. Как только активируют — сможешь начать работать! 😊',
                    'uk': 'Просто чекай активації від офісу. Зазвичай це відбувається наступного робочого дня. Як тільки активують — зможеш почати працювати! 😊',
                    'en': 'Just wait for activation from the office. Usually it happens the next business day. Once activated — you can start working! 😊'
                }
            elif 'фото' in bot_msg or 'photo' in bot_msg:
                return {
                    'ru': 'Нужно отправить мне 2-3 своих фото. После этого я отправлю их на рассмотрение офису 😊',
                    'uk': 'Потрібно надіслати мені 2-3 свої фото. Після цього я відправлю їх на розгляд офісу 😊',
                    'en': 'You need to send me 2-3 photos of yourself. After that I will send them for office review 😊'
                }
            else:
                return {
                    'ru': 'Следуй инструкциям выше шаг за шагом. Если что-то непонятно на конкретном шаге — спрашивай! 😊',
                    'uk': 'Дотримуйся інструкцій вище крок за кроком. Якщо щось незрозуміло на конкретному кроці — питай! 😊',
                    'en': 'Follow the instructions above step by step. If something is unclear at a specific step — ask! 😊'
                }
    
    return None

async def get_ai_response_with_retry(user_id, question, max_retries=2, is_in_groups=False):
    logger.info(f"Starting AI request for user {user_id}")
    
    user = await get_user(user_id)
    user_lang = user['language'] if user and user['language'] else 'ru'
    
    direct_answer = await check_faq_direct_match(question, user_lang)
    if direct_answer:
        logger.info(f"Direct FAQ match for user {user_id}")
        return {
            'answer': direct_answer,
            'confidence': 95,
            'escalate': False
        }
    
    history = await get_messages(user_id, limit=10)
    contextual_answer = await is_contextual_question(question, history)
    if contextual_answer:
        answer = contextual_answer.get(user_lang, contextual_answer.get('ru', ''))
        logger.info(f"Contextual question detected for user {user_id}")
        return {
            'answer': answer,
            'confidence': 92,
            'escalate': False
        }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"AI attempt {attempt + 1}/{max_retries} for user {user_id}")
            response = await get_ai_response(user_id, question, is_in_groups)
            if response['confidence'] > 0 or response['escalate']:
                logger.info(f"AI response successful for user {user_id}")
                return response
            logger.warning(f"AI returned 0 confidence for user {user_id}")
        except asyncio.TimeoutError:
            logger.error(f"AI timeout for user {user_id}")
            if attempt == max_retries - 1:
                return {
                    'answer': '',
                    'confidence': 0,
                    'escalate': True
                }
        except Exception as e:
            logger.error(f"AI error for user {user_id}: {e}")
            if attempt == max_retries - 1:
                return {
                    'answer': '',
                    'confidence': 0,
                    'escalate': True
                }
            await asyncio.sleep(2)
    
    return {
        'answer': '',
        'confidence': 0,
        'escalate': True
    }

async def get_ai_response(user_id, question, is_in_groups=False):
    user = await get_user(user_id)
    user_lang = user['language'] if user and user['language'] else 'ru'
    
    if await check_forbidden_topics(question):
        logger.info(f"Forbidden topic for user {user_id}")
        return {
            'answer': UNIVERSAL_RESPONSE.get(user_lang, UNIVERSAL_RESPONSE['ru']),
            'confidence': 100,
            'escalate': False
        }
    
    logger.info(f"Building context for user {user_id}")
    context_prompt = await build_context_prompt(user_id, question, is_in_groups)
    
    try:
        logger.info(f"Calling AI for user {user_id}")
        
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
        
        if not response or not hasattr(response, 'choices') or not response.choices:
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        content = response.choices[0].message.content
        content = content.strip() if hasattr(content, 'strip') else str(content).strip()
        
        if not content or is_g4f_error(content):
            logger.warning(f"g4f error in response content for user {user_id}: {content[:100]}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        if content.startswith('```json'):
            content = content[7:-3].strip()
        elif content.startswith('```'):
            content = content[3:-3].strip()
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            simple_responses = ['привет', 'здравствуй', 'хорошо', 'спасибо', 'ок', 'понятно', 
                              'супер', 'класс', 'круто', 'отлично', 'добре', 'ясно']
            q_lower = question.lower().strip()
            
            confidence = 90 if any(greeting in q_lower for greeting in simple_responses) else 70
            
            return {
                'answer': content,
                'confidence': confidence,
                'escalate': confidence < AI_CONFIDENCE_THRESHOLD
            }
        
        if not isinstance(result, dict):
            return {
                'answer': str(result),
                'confidence': 70,
                'escalate': False
            }
        
        if 'answer' not in result:
            result['answer'] = content
        if 'confidence' not in result:
            result['confidence'] = 50
        if 'escalate' not in result:
            result['escalate'] = result['confidence'] < AI_CONFIDENCE_THRESHOLD
        
        if is_g4f_error(str(result.get('answer', ''))):
            logger.warning(f"g4f error in parsed answer for user {user_id}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        logger.info(f"AI response for {user_id}: conf={result['confidence']}, esc={result['escalate']}")
        
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"AI timeout for {user_id}")
        raise
    except Exception as e:
        logger.error(f"AI error for {user_id}: {e}")
        raise