# utils/ai_handler.py
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

HALO_TRAINING_KNOWLEDGE = {
    'ru': {
        'start_hunting': 'Нажми значок сети и выбери "начать охоту" (start hunting). Эта функция называется хайтинг/hunting.',
        'hunting_info': '''Охота (hunting) - это обязательная функция перед звонками:
- Дает +4 коина ($0.20) и повышает цену за звонок
- Звонок сбрасывается автоматически через 2 минуты
- Если клиент отключился раньше - охота не засчитывается, нужно проходить повторно
- Если не прошла охоту - минус 20% коинов со всех звонков
- Если получила дизлайк - минус 25% коинов
- Делать раз в сутки, до звонков''',
        
        'multibeam_join': 'Чтобы присоединиться к мультибиму, нажми "Press unit" и жди очередь, пока тебя подключат в спот.',
        'multibeam_types': '''Есть два типа Multi Beam:
1) Официальные - в самом верху в закреплённых. Иногда могут не добавить, особенно если арабский эфир
2) Неофициальные - немного ниже официальных, иногда появляются. Не всегда доступны, но можно зайти и заработать
Если войдёшь в топ 200 приложения - откроется доступ к открытию своего неофициального MultiBeam''',
        
        'profile_setup': '''Настройка профиля:
- Установи теги - мужчины ищут девушек по тегам
- Добавь привлекательные фото - именно фото влияют на решение написать или позвонить
- Можно добавлять фото в купальнике, в образах где чувствуешь себя уверенно
- Профиль - это твоя витрина, сделай его привлекательным''',
        'profile_edit': '''Редактирование профиля:
1. Нажми на свою иконку → стрелочку → редактировать
2. Можешь изменить: аватар, обложку, привлекательные фото
3. Аватар и обложка должны отличаться
4. ЗАПРЕЩЕНО постить фото в нижнем белье или купальнике на аватар/обложку
5. Такие фото только в "привлекательные фотографии" (платный раздел)
6. Можно изменить: никнейм, возраст, область, языки
7. В "Обо мне" напиши например: "I'm new here, be gentleman"''',
        
        'posts_activity': '''Публикация постов = больше звонков:
- Делай от 20 постов в день
- Интервал - 1 пост каждые 10-15 минут
- Запрещено: AI-фото, фото с Pinterest, чужие фото
- Нарушения = бан от 3 дней или навсегда''',
        'how_to_post': '''Как публиковать посты:
1. Нажми на кнопку публикации
2. Добавь подпись ОБЯЗАТЕЛЬНО на английском (например: "I'm new here" или "Call me")
3. Нажми плюс, добавь фото
4. Нажми опубликовать
Можешь заходить в ленту смотреть как далеко твоё фото - если далеко, публикуй новое''',
        
        'live_stream_posture': '''Как правильно сидеть в эфире:
✅ МОЖНО: сидеть ровно, камера на уровне глаз (телефон прямо напротив лица), видно лицо, хороший свет
❌ НЕЛЬЗЯ: лежать, снимать снизу или сверху, сутулиться, тёмный кадр''',
        
        'live_stream_start': '''Запуск прямого эфира:
1. Нажми start, чтобы запустить
2. Выбери обложку (НЕ в нижнем белье, иначе отключат)
3. Напиши название комнаты: "I'm new here"
4. Описание: "Call me"
5. Квота комнаты - сколько хочешь заработать монет
6. Выбери подарок для приватной зоны (рекомендую 99 монет сначала)
7. Можешь выбрать маски
8. Нажми start''',
        
        'live_stream_messages': '''Когда запускаешь эфир - ОБЯЗАТЕЛЬНО пиши мужчинам:
- Видишь зашёл мужчина с s-vip или уровнем
- Сразу нажми на его nickname
- Напиши: "Hi, call me"
- Большинство заходят, смотрят и уходят - важно написать первой''',
        
        'live_stream_rules': '''Правила прямых эфиров:
ЗАПРЕЩЕНО:
- Показывать интимные части тела крупным планом
- Тверкинг, тряска телом, эротичные движения
- Трогать интимные части тела
- Стонать или издавать эротические звуки
- Показывать секс-игрушки
- Использовать предметы фаллической формы (банан, огурец)
ДРЕСС-КОД:
- Запрещена одежда с открытыми сосками или большой частью груди
- Запрещена слишком откровенная/прозрачная одежда без прикрытия
- Нижнее бельё и стринги РАЗРЕШЕНЫ''',
        
        'tasks': '''Выполнение заданий:
- Нажми "центр задач"
- Есть ежедневные, еженедельные, ежемесячные задания
- За них получаешь золотые коины (доллары) или фиолетовые очки
- За очки можешь удалять дизлайки или продвигать трансляцию
В магазине очков:
- День без охоты - 300 очков
- Увеличение актива в комнате - 200 очков
- Минус один дизлайк - 200 очков''',
        
        'dislikes_info': '''Два коэффициента дизлайков:
1️⃣ Коэффициент в профиле (видишь в профиле):
- Всегда должен быть НИЖЕ 0.18
- Если 0.18 или выше - нарушение, могут заблокировать
2️⃣ Коэффициент за 30 дней (не видно):
- Нужно считать самостоятельно
- Офис проверяет каждый день
- Тоже должен быть ниже 0.18''',
        
        'dislikes_delete': '''Как удалить дизлайк:
1. Зайди в "центр задач"
2. Выполняй задания, чтобы получить фиолетовые очки
3. Накопи 200 очков
4. Зайди в магазин очков
5. Купи "Минус один дизлайк" за 200 очков
Так можно удалять дизлайки и поддерживать коэффициент ниже 0.18 ✅''',
        
        'auto_messages': '''Автосообщения:
- ОБЯЗАТЕЛЬНО делай автосообщения
- Через 10 дней несколько мужчин могут открыть платный контент
- Одно сообщение идёт ~600 мужчинам
- Откроют ~10, купят 1-2
- Если 10 автосообщений работают - это +$100
- Работают в долгую - настраивай и жди''',
        
        'registration_steps': '''Регистрация в Halo:
1. Скачай приложение For hosts (розовое) с https://livegirl.me/#/mobilepage
2. Открой → нажми "Регистрация"
3. Введи: почту, пароль
4. Укажи: никнейм, возраст, языки (арабский, английский, украинский, русский)
5. В разделе Агентство: Tosagency-Ukraine
6. Загрузи фото и запиши видео-приветствие
Видео: "Hello, my name is [имя]. I am [возраст] years old. I live in [страна]. I want to join."
7. Пришли скрин с ID и агентством
8. Я отправлю заявку в офис
9. На следующий будний день активируют аккаунт''',
        
        'after_registration': '''После регистрации:
- Присоединяйся к двум группам
- В группе «Обучение» есть закреплённое сообщение с полной информацией
- Обязательно ознакомься с ним!
Если возникнут вопросы — пиши, я всегда на связи и помогу 😊''',
        
        'agency_name': 'В разделе Агентство выбирай: Tosagency-Ukraine 😊',
    },
    
    'uk': {
        'start_hunting': 'Натисни значок мережі і обери "почати полювання" (start hunting). Ця функція називається хайтинг/hunting.',
        'hunting_info': '''Полювання (hunting) - це обов'язкова функція перед дзвінками:
- Дає +4 коїна ($0.20) і підвищує ціну за дзвінок
- Дзвінок скидається автоматично через 2 хвилини
- Якщо клієнт відключився раніше - полювання не зараховується, потрібно проходити повторно
- Якщо не пройшла полювання - мінус 20% коїнів з усіх дзвінків
- Якщо отримала дизлайк - мінус 25% коїнів
- Робити раз на добу, до дзвінків''',
        
        'multibeam_join': 'Щоб приєднатися до мультибіму, натисни "Press unit" і чекай чергу, поки тебе підключать у спот.',
        
        'profile_setup': '''Налаштування профілю:
- Встанови теги - чоловіки шукають дівчат за тегами
- Додай привабливі фото - саме фото впливають на рішення написати або зателефонувати
- Можна додавати фото в купальнику, в образах де почуваєшся впевнено
- Профіль - це твоя вітрина, зроби його привабливим''',
        
        'posts_activity': '''Публікація постів = більше дзвінків:
- Роби від 20 постів на день
- Інтервал - 1 пост кожні 10-15 хвилин
- Заборонено: AI-фото, фото з Pinterest, чужі фото
- Порушення = бан від 3 днів або назавжди''',
        
        'live_stream_posture': '''Як правильно сидіти в ефірі:
✅ МОЖНА: сидіти рівно, камера на рівні очей (телефон прямо навпроти обличчя), видно обличчя, хороше освітлення
❌ НЕ МОЖНА: лежати, знімати знизу або зверху, горбитися, темний кадр''',
        
        'live_stream_start': '''Запуск прямого ефіру:
1. Натисни start, щоб запустити
2. Обери обкладинку (НЕ у нижній білизні, інакше відключать)
3. Напиши назву кімнати: "I'm new here"
4. Опис: "Call me"
5. Квота кімнати - скільки хочеш заробити монет
6. Обери подарунок для приватної зони (рекомендую 99 монет спочатку)
7. Можеш обрати маски
8. Натисни start''',
        
        'dislikes_info': '''Два коефіцієнти дизлайків:
1️⃣ Коефіцієнт у профілі (бачиш у профілі):
- Завжди має бути НИЖЧЕ 0.18
- Якщо 0.18 або вище - порушення, можуть заблокувати
2️⃣ Коефіцієнт за 30 днів (не видно):
- Потрібно рахувати самостійно
- Офіс перевіряє щодня
- Також має бути нижче 0.18''',
        
        'dislikes_delete': '''Як видалити дизлайк:
1. Зайди в "центр завдань"
2. Виконуй завдання, щоб отримати фіолетові очки
3. Накопи 200 очок
4. Зайди в магазин очок
5. Купи "Мінус один дизлайк" за 200 очок
Так можна видаляти дизлайки і підтримувати коефіцієнт нижче 0.18 ✅''',
        
        'auto_messages': '''Автоповідомлення:
- ОБОВ'ЯЗКОВО роби автоповідомлення
- Через 10 днів кілька чоловіків можуть відкрити платний контент
- Одне повідомлення йде ~600 чоловікам
- Відкриють ~10, куплять 1-2
- Якщо 10 автоповідомлень працюють - це +$100
- Працюють на довгу дистанцію - налаштовуй і чекай''',
        
        'after_registration': '''Після реєстрації:
- Приєднуйся до двох груп
- У групі «Навчання» є закріплене повідомлення з повною інформацією
- Обов'язково ознайомся з ним!
Якщо виникнуть питання — пиши, я завжди на зв'язку і допоможу 😊''',
        
        'agency_name': 'У розділі Агентство обирай: Tosagency-Ukraine 😊',
    },
    
    'en': {
        'start_hunting': 'Tap the network icon and select "start hunting". This feature is called hunting/hating.',
        'hunting_info': '''Hunting is mandatory before calls:
- Gives +4 coins ($0.20) and increases call price
- Call resets automatically after 2 minutes
- If client hangs up earlier - hunt doesn't count, need to repeat
- If didn't complete hunt - minus 20% coins from all calls
- If got dislike - minus 25% coins
- Do once per day, before calls''',
        
        'multibeam_join': 'To join multibeam, press "Press unit" and wait in line until they connect you to a spot.',
        
        'profile_setup': '''Profile setup:
- Set tags - men search for girls by tags
- Add attractive photos - photos influence decision to write or call
- Can add photos in swimsuit, outfits where you feel confident
- Profile is your showcase, make it attractive''',
        
        'posts_activity': '''Posting = more calls:
- Make at least 20 posts per day
- Interval - 1 post every 10-15 minutes
- Forbidden: AI photos, Pinterest photos, others' photos
- Violations = ban from 3 days or forever''',
        
        'live_stream_posture': '''How to sit correctly during stream:
✅ ALLOWED: sit straight, camera at eye level (phone directly in front of face), face visible, good lighting
❌ NOT ALLOWED: lying down, filming from below or above, slouching, dark frame''',
        
        'live_stream_start': '''Starting a live stream:
1. Press start to launch
2. Choose cover (NOT in underwear, or they'll disconnect you)
3. Write room title: "I'm new here"
4. Description: "Call me"
5. Room quota - how many coins you want to earn
6. Choose gift for private zone (recommend 99 coins at first)
7. Can choose masks
8. Press start''',
        
        'dislikes_info': '''Two dislike ratios:
1️⃣ Profile ratio (you can see):
- Always must be BELOW 0.18
- If 0.18 or higher - violation, may be blocked
2️⃣ 30-day ratio (not visible):
- Need to calculate manually
- Office checks daily
- Also must be below 0.18''',
        
        'dislikes_delete': '''How to delete a dislike:
1. Go to "task center"
2. Complete tasks to get purple points
3. Accumulate 200 points
4. Go to points shop
5. Buy "Minus one dislike" for 200 points
This way you can delete dislikes and keep ratio below 0.18 ✅''',
        
        'auto_messages': '''Auto-messages:
- MUST set up auto-messages
- After 10 days several men might unlock paid content
- One message sent to ~600 men
- ~10 will open, 1-2 will buy
- If 10 auto-messages work - that's +$100
- Work long-term - set up and wait''',
        
        'after_registration': '''After registration:
- Join two groups
- In the "Training" group there's a pinned message with full information
- Be sure to read it!
If you have questions — write me, I'm always available to help 😊''',
        
        'agency_name': 'In Agency section choose: Tosagency-Ukraine 😊',
    }
}

KNOWLEDGE_KEYWORDS = {
    'hunting': ['охота', 'hunting', 'хантинг', 'hunt', 'полювання', 'start hunting', 'начать охоту', 'почати полювання'],
    'multibeam': ['мультибим', 'multibeam', 'multi beam', 'multi-beam', 'multibim', 'мультібім', 'press unit', 'спот', 'spot'],
    'profile': ['профиль', 'profile', 'профіль', 'аватар', 'avatar', 'обложка', 'cover', 'теги', 'tags', 'настройка профиля', 'налаштування профілю', 'редактир', 'edit profile'],
    'posts': ['пост', 'post', 'публикация', 'публікація', 'лента', 'feed', 'posting', 'как публиковать', 'як публікувати', 'how to post'],
    
    'live_stream_start': ['запустить эфир', 'запустити ефір', 'start stream', 'начать эфир', 'почати ефір', 'как запустить', 'як запустити', 'start live', 'launch stream', 'open stream'],
    'live_stream_posture': ['как сидеть', 'як сидіти', 'how to sit', 'правильно сидеть', 'правильно сидіти', 'posture', 'поза', 'сидіти в ефірі', 'сидеть в эфире'],
    
    'live_stream': ['эфир', 'stream', 'ефір', 'прямой эфир', 'live', 'трансляция', 'прямий ефір', 'broadcast'],
    'rules': ['правила', 'rules', 'правила', 'запрещено', 'forbidden', 'заборонено', 'нельзя', 'можно', 'можна', 'what allowed', 'що дозволено'],
    'dislikes_delete': ['видалити дизлайк', 'удалить дизлайк', 'delete dislike', 'убрать дизлайк', 'прибрати дизлайк', 'как удалить', 'як видалити', 'how to delete'],
    'auto_messages': ['автосообщ', 'auto message', 'автоповідомл', 'mass message', 'массовые', 'масові', 'рассылка', 'розсилка'],
    'tasks': ['задания', 'tasks', 'завдання', 'центр задач', 'task center', 'виконати завдання', 'выполнить задания'],
    'agency': ['агентство', 'agency', 'tosagency', 'агенство', 'какое агентство', 'which agency', 'яке агентство'],
    'registration': ['регистрация', 'registration', 'реєстрація', 'зарегистр', 'register', 'зареєстр'],
    'after_registration': ['після реєстрації', 'после регистрации', 'after registration', 'що потрібно робити', 'что нужно делать', 'what to do', 'что делать после', 'що робити після'],
}

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

def extract_numbers_from_text(text):
    import re
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]

def is_dislike_calculation_request(text):
    text_lower = text.lower()
    
    calculation_keywords = [
        'порахуй', 'посчитай', 'розрахуй', 'calculate', 'рассчитай',
        'мій коефіцієнт', 'мой коэффициент', 'my ratio', 'my coefficient',
        'в мене', 'у меня', 'i have', 'у мене'
    ]
    
    dislike_keywords = ['дизлайк', 'dislike', 'лайк', 'like']
    
    has_calculation = any(kw in text_lower for kw in calculation_keywords)
    has_dislikes = any(kw in text_lower for kw in dislike_keywords)
    numbers = extract_numbers_from_text(text)
    
    if has_calculation and has_dislikes and len(numbers) >= 2:
        return True
    
    if has_dislikes and len(numbers) >= 2:
        if 'в мене' in text_lower or 'у меня' in text_lower or 'i have' in text_lower or 'у мене' in text_lower:
            return True
    
    return False

def calculate_dislike_ratio(text, user_lang='ru'):
    numbers = extract_numbers_from_text(text)
    
    if len(numbers) < 2:
        return None
    
    text_lower = text.lower()
    
    dislike_first_patterns = ['дизлайк', 'dislike']
    like_first_patterns = ['лайк', 'like']
    
    dislike_pos = min([text_lower.find(p) for p in dislike_first_patterns if p in text_lower] or [999])
    like_pos = min([text_lower.find(p) for p in like_first_patterns if p in text_lower] or [999])
    
    if dislike_pos < like_pos:
        dislikes = numbers[0]
        likes = numbers[1]
    else:
        likes = numbers[0]
        dislikes = numbers[1]
    
    total = dislikes + likes
    if total == 0:
        return None
    
    ratio = dislikes / total
    
    is_good = ratio < 0.18
    
    responses = {
        'ru': f'''Твій коефіцієнт: {ratio:.3f}

Дизлайки: {dislikes}
Лайки: {likes}
Всього: {total}

{'✅ Це добре! Коефіцієнт нижче 0.18' if is_good else '⚠️ УВАГА! Коефіцієнт 0.18 або вище - це порушення! Терміново видаляй дизлайки через центр завдань (200 очок за дизлайк)'}''',
        'uk': f'''Твій коефіцієнт: {ratio:.3f}

Дизлайки: {dislikes}
Лайки: {likes}
Всього: {total}

{'✅ Це добре! Коефіцієнт нижче 0.18' if is_good else '⚠️ УВАГА! Коефіцієнт 0.18 або вище - це порушення! Терміново видаляй дизлайки через центр завдань (200 очок за дизлайк)'}''',
        'en': f'''Your ratio: {ratio:.3f}

Dislikes: {dislikes}
Likes: {likes}
Total: {total}

{'✅ This is good! Ratio is below 0.18' if is_good else '⚠️ WARNING! Ratio 0.18 or higher is a violation! Urgently delete dislikes through task center (200 points per dislike)'}'''
    }
    
    return responses.get(user_lang, responses['ru'])

def find_relevant_knowledge(question, user_lang='ru'):
    q_lower = question.lower()
    relevant = []
    matched_categories = set()
    
    if is_dislike_calculation_request(question):
        calculation_result = calculate_dislike_ratio(question, user_lang)
        if calculation_result:
            return [calculation_result]
    
    specific_checks = [
        ('live_stream_start', KNOWLEDGE_KEYWORDS['live_stream_start']),
        ('live_stream_posture', KNOWLEDGE_KEYWORDS['live_stream_posture']),
        ('dislikes_delete', KNOWLEDGE_KEYWORDS['dislikes_delete']),
        ('after_registration', KNOWLEDGE_KEYWORDS['after_registration']),
    ]
    
    for category, keywords in specific_checks:
        for keyword in keywords:
            if keyword in q_lower:
                knowledge = HALO_TRAINING_KNOWLEDGE.get(user_lang, HALO_TRAINING_KNOWLEDGE['ru'])
                if category in knowledge:
                    relevant.append(knowledge[category])
                    matched_categories.add(category)
                    logger.info(f"Matched specific category: {category} for keyword: {keyword}")
                break
        if category in matched_categories:
            break
    
    if relevant:
        return relevant
    
    for category, keywords in KNOWLEDGE_KEYWORDS.items():
        if category in matched_categories:
            continue
        
        for keyword in keywords:
            if keyword in q_lower:
                knowledge = HALO_TRAINING_KNOWLEDGE.get(user_lang, HALO_TRAINING_KNOWLEDGE['ru'])
                for key, value in knowledge.items():
                    if category in key or keyword in key:
                        relevant.append(value)
                        logger.info(f"Matched general category: {category} for keyword: {keyword}")
                break
    
    return relevant

def find_relevant_materials(question, materials, max_results=3):
    if not materials:
        return []
    
    question_lower = question.lower()
    scored_materials = []
    
    for material in materials:
        content = material.get('text') or material.get('transcription', '')
        if not content:
            continue
        
        content_lower = content.lower()
        score = 0
        
        question_words = [w for w in question_lower.split() if len(w) > 3]
        
        for word in question_words:
            if word in content_lower:
                score += content_lower.count(word) * 2
        
        for category, keywords in KNOWLEDGE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question_lower and keyword in content_lower:
                    score += 10
        
        if score > 0:
            scored_materials.append((score, material, content))
    
    scored_materials.sort(key=lambda x: x[0], reverse=True)
    
    return [(m, c) for _, m, c in scored_materials[:max_results]]

def detect_country_in_text(text):
    text_lower = text.lower()
    for country in COUNTRY_KEYWORDS:
        if country in text_lower:
            return country
    return None

def is_g4f_error(content):
    if not content:
        return True
    c = content.lower()
    if 'does not exist' in c:
        return True
    if 'the model does not' in c:
        return True
    if 'model' in c and 'exist' in c:
        return True
    if c.startswith('error'):
        return True
    if 'api.airforce' in c:
        return True
    if 'bad request' in c:
        return True
    if len(content.strip()) < 3:
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
    from utils.language_detector import detect_language
    
    user = await get_user(user_id)
    history = await get_messages(user_id, limit=15)
    
    question_lang = detect_language(question)
    user_lang = user['language'] if user and user['language'] else question_lang
    
    answer_lang = question_lang
    
    relevant_knowledge = find_relevant_knowledge(question, answer_lang)
    
    status = user['status']
    if status in ['new', 'chatting', 'waiting_photos', 'asking_work_hours', 'asking_experience']:
        category = 'new'
    elif status in ['helping_registration', 'waiting_screenshot']:
        category = 'registration'
    elif status in ['registered', 'approved']:
        category = 'working'
    else:
        category = 'new'
    
    faq_ru = await get_faq(category=category)
    faq_all = await get_faq()
    learning = await get_ai_learning()
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
    
    faq_text = "\n".join([f"Q: {f['question']}\nA: {f['answer']}" for f in faq_ru[:30]])
    faq_text += "\n\n=== ДОПОЛНИТЕЛЬНЫЕ ВОПРОСЫ (ВСЕ ЯЗЫКИ) ===\n"
    faq_text += "\n".join([f"Q: {f['question']}\nA: {f['answer']}" for f in faq_all[:50]])
    
    learning_text = "\n".join([f"Q: {l['question']}\nA: {l['answer']} (confidence: {l['confidence']})" for l in learning[:10]])
    
    group_status = "ЕСТЬ В ГРУППАХ (можно отвечать на рабочие вопросы)" if is_in_groups else "НЕТ В ГРУППАХ (только регистрация)"
    
    last_messages = history[-5:] if len(history) >= 5 else history
    recent_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in last_messages])
    
    knowledge_section = ""
    if relevant_knowledge:
        knowledge_section = f"\n\n=== СПЕЦИАЛЬНЫЕ ЗНАНИЯ ПО ВОПРОСУ (ЯЗЫК: {answer_lang.upper()}) ===\n"
        knowledge_section += "\n\n".join(relevant_knowledge[:5])
        knowledge_section += "\n⚠️ ИСПОЛЬЗУЙ ЭТИ ЗНАНИЯ ДЛЯ ОТВЕТА - ОНИ УЖЕ НА ПРАВИЛЬНОМ ЯЗЫКЕ!\n"
        knowledge_section += f"⚠️ ОТВЕЧАЙ ТОЛЬКО НА {answer_lang.upper()} ЯЗЫКЕ!\n"
    
    training_materials = ""
    
    texts_all = await get_all_analysis_texts(lang=answer_lang)
    audios_all = await get_all_analysis_audios(lang=answer_lang)
    videos_all = await get_all_analysis_videos(lang=answer_lang)
    
    relevant_texts = find_relevant_materials(question, texts_all, max_results=5)
    relevant_audios = find_relevant_materials(question, audios_all, max_results=3)
    relevant_videos = find_relevant_materials(question, videos_all, max_results=3)
    
    if relevant_texts or relevant_audios or relevant_videos:
        training_materials = f"\n\n=== РЕЛЕВАНТНЫЕ ОБУЧАЮЩИЕ МАТЕРИАЛЫ (ЯЗЫК: {answer_lang.upper()}) ===\n"
        training_materials += "⚠️ ЭТИ МАТЕРИАЛЫ СПЕЦИАЛЬНО ОТОБРАНЫ ПО ТВОЕМУ ВОПРОСУ - ИСПОЛЬЗУЙ ИХ!\n\n"
        
        if relevant_texts:
            training_materials += "=== РЕЛЕВАНТНЫЕ ТЕКСТОВЫЕ ИНСТРУКЦИИ ===\n"
            for i, (text, content) in enumerate(relevant_texts, 1):
                training_materials += f"\n--- Документ {i} (РЕЛЕВАНТНЫЙ) ---\n{content[:2000]}\n"
        
        if relevant_audios:
            training_materials += "\n=== РЕЛЕВАНТНЫЕ АУДИО МАТЕРИАЛЫ ===\n"
            for i, (audio, content) in enumerate(relevant_audios, 1):
                training_materials += f"\n--- Аудио {i} (РЕЛЕВАНТНЫЙ) ---\n{content[:1500]}\n"
        
        if relevant_videos:
            training_materials += "\n=== РЕЛЕВАНТНЫЕ ВИДЕО МАТЕРИАЛЫ ===\n"
            for i, (video, content) in enumerate(relevant_videos, 1):
                training_materials += f"\n--- Видео {i} (РЕЛЕВАНТНЫЙ) ---\n{content[:1500]}\n"
    else:
        if texts_all or audios_all or videos_all:
            training_materials = f"\n\n=== ОБЩИЕ ОБУЧАЮЩИЕ МАТЕРИАЛЫ (ЯЗЫК: {answer_lang.upper()}) ===\n"
            
            if texts_all:
                training_materials += "=== ТЕКСТОВЫЕ ИНСТРУКЦИИ ===\n"
                for i, text in enumerate(texts_all[:5], 1):
                    content = text.get('text', '')
                    if content:
                        training_materials += f"\n--- Документ {i} ---\n{content[:1000]}\n"
            
            if audios_all:
                training_materials += "\n=== АУДИО МАТЕРИАЛЫ ===\n"
                for i, audio in enumerate(audios_all[:3], 1):
                    content = audio.get('transcription', '')
                    if content:
                        training_materials += f"\n--- Аудио {i} ---\n{content[:800]}\n"
            
            if videos_all:
                training_materials += "\n=== ВИДЕО МАТЕРИАЛЫ ===\n"
                for i, video in enumerate(videos_all[:3], 1):
                    content = video.get('transcription', '')
                    if content:
                        training_materials += f"\n--- Видео {i} ---\n{content[:800]}\n"
    
    lang_instruction = {
        'ru': "⚠️ КРИТИЧЕСКИ ВАЖНО: ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ! Пользователь задал вопрос на РУССКОМ!",
        'uk': "⚠️ КРИТИЧНО ВАЖЛИВО: ВІДПОВІДАЙ ТІЛЬКИ УКРАЇНСЬКОЮ МОВОЮ! Користувач задав питання УКРАЇНСЬКОЮ!",
        'en': "⚠️ CRITICALLY IMPORTANT: RESPOND ONLY IN ENGLISH! User asked question in ENGLISH!"
    }
    
    context_prompt = f"""
СТАТУС ПОЛЬЗОВАТЕЛЯ: {user['status']}
СТАТУС УЧАСТИЯ: {group_status}

🔴 ЯЗЫК ВОПРОСА: {answer_lang.upper()}
🔴 {lang_instruction.get(answer_lang, lang_instruction['ru'])}
🔴 ВСЕ ЗНАНИЯ И МАТЕРИАЛЫ НИЖЕ УЖЕ НА ЯЗЫКЕ {answer_lang.upper()} - ИСПОЛЬЗУЙ ИХ НАПРЯМУЮ!

СПЕЦИАЛЬНАЯ ИНСТРУКЦИЯ ПО РАСЧЕТУ КОЭФФИЦИЕНТА ДИЗЛАЙКОВ:
Если пользователь спрашивает про коэффициент дизлайков И ДАЕТ ЧИСЛА (например: "у меня 5 дизлайков и 10 лайков"):
1. НЕ ПРОСТО ВЫДАВАЙ ИНФОРМАЦИЮ О ДИЗЛАЙКАХ
2. ПОСЧИТАЙ коэффициент: дизлайки / (дизлайки + лайки)
3. СКАЖИ результат и хороший он или плохой (должен быть < 0.18)
4. Confidence: 95

ПРИОРИТЕТ ИСТОЧНИКОВ ОТВЕТА (СТРОГО СЛЕДУЙ В ЭТОМ ПОРЯДКЕ):

ПРИОРИТЕТ 1 - СПЕЦИАЛЬНЫЕ ЗНАНИЯ ПО ТЕМЕ ВОПРОСА:
{knowledge_section}
Если есть специальные знания выше - отвечай НА ИХ ОСНОВЕ с confidence 90-95
⚠️ ОНИ УЖЕ НА ЯЗЫКЕ {answer_lang.upper()} - ИСПОЛЬЗУЙ НАПРЯМУЮ!

ПРИОРИТЕТ 2 - ПОСЛЕДНИЕ 5 СООБЩЕНИЙ:
{recent_context}
Если ответ есть в последних 5 сообщениях - отвечай на их основе с confidence 90-95

ПРИОРИТЕТ 3 - БАЗА ЗНАНИЙ (FAQ) И ПРАВИЛА:
{faq_text}
Если ответа НЕТ выше, но есть в FAQ - отвечай на его основе с confidence 85-90

ПРИОРИТЕТ 4 - РЕЛЕВАНТНЫЕ ОБУЧАЮЩИЕ МАТЕРИАЛЫ:
{training_materials}
⚠️ ЕСЛИ ВЫШЕ ЕСТЬ РЕЛЕВАНТНЫЕ МАТЕРИАЛЫ - ОНИ СПЕЦИАЛЬНО ОТОБРАНЫ ПО ВОПРОСУ!
Используй их с confidence 85-95, они содержат ТОЧНЫЙ ответ на вопрос пользователя!
⚠️ ОНИ УЖЕ НА ЯЗЫКЕ {answer_lang.upper()} - ИСПОЛЬЗУЙ НАПРЯМУЮ!

ПРИОРИТЕТ 5 - ЭСКАЛАЦИЯ:
Если ответа НЕТ ни в одном из источников выше - ЭСКАЛИРУЙ (escalate: true, confidence < 70)

ПОЛНАЯ ИСТОРИЯ ДИАЛОГА (для контекста):
{history_text}

ОБУЧЕННЫЕ ОТВЕТЫ (для справки):
{learning_text}

ТЕКУЩИЙ ВОПРОС:
{question}

КРИТИЧЕСКИЕ ПРАВИЛА:
1. СТРОГО следуй приоритету: Специальные знания → 5 сообщений → FAQ → Обучающие → Эскалация
2. ⚠️ ОТВЕЧАЙ ТОЛЬКО НА ЯЗЫКЕ {answer_lang.upper()}! Это КРИТИЧЕСКИ ВАЖНО!
3. Все материалы уже на языке {answer_lang.upper()} - используй их НАПРЯМУЮ без перевода
4. Простые эмоции (ок, супер, класс, добре, ok, good) - confidence 95+
5. ЛЮБАЯ СТРАНА ПОДХОДИТ для работы
6. Ответ КРАТКИЙ (максимум 200 слов)
7. НЕ ИСПОЛЬЗУЙ MARKDOWN (без *, _, **)
8. Стиль менеджера Valencia (дружелюбный, с эмодзи)
9. Если вопрос про работу в приложении - ИСПОЛЬЗУЙ специальные знания в первую очередь
10. ⚠️ НЕ ПЕРЕВОДИ ОТВЕТ - материалы уже на правильном языке!
11. ⚠️ ЕСЛИ ВОПРОС ПРО КОЭФФИЦИЕНТ ДИЗЛАЙКОВ С ЧИСЛАМИ - СЧИТАЙ, А НЕ ПРОСТО ВЫДАВАЙ ИНФО!
"""
    
    return context_prompt

async def check_faq_direct_match(question, user_lang='ru'):
    from utils.language_detector import detect_language
    
    question_lang = detect_language(question)
    q_lower = question.lower().strip()
    
    if is_dislike_calculation_request(question):
        calculation_result = calculate_dislike_ratio(question, question_lang)
        if calculation_result:
            return calculation_result
    
    relevant_knowledge = find_relevant_knowledge(question, question_lang)
    if relevant_knowledge and len(q_lower.split()) <= 15:
        return relevant_knowledge[0]
    
    agency_keywords = [
        'which agency', 'what agency', 'agency name', 'which one',
        'яке агентство', 'какое агентство', 'назва агентства', 'название агентства',
        'яке обрати', 'какое выбрать', 'which to choose', 'which should i choose',
        'tosagency', 'агентств', 'agency', 'агентство', 'агенство',
        'яке', 'какое', 'which', 'what is agency', 'what agency name'
    ]
    
    is_agency_question = False
    for kw in agency_keywords:
        if kw in q_lower:
            is_agency_question = True
            break
    
    if not is_agency_question:
        agency_words_count = sum(1 for word in ['agency', 'агентств', 'агентство', 'агенство', 'яке', 'какое', 'which'] if word in q_lower)
        if agency_words_count > 0 and len(q_lower.split()) <= 4:
            is_agency_question = True
    
    if is_agency_question:
        responses = {
            'ru': 'В разделе Агентство выбирай: Tosagency-Ukraine 😊',
            'uk': 'У розділі Агентство обирай: Tosagency-Ukraine 😊',
            'en': 'In the Agency section choose: Tosagency-Ukraine 😊'
        }
        return responses.get(question_lang, responses['ru'])
    
    video_photo_keywords = [
        'can i send video', 'video instead', 'відео замість', 'видео вместо',
        'можу відео', 'могу видео', 'відправити відео', 'отправить видео'
    ]
    
    if any(kw in q_lower for kw in video_photo_keywords):
        responses = {
            'ru': 'Нужны именно фото, не видео 📸 Пришли 2-3 фото хорошего качества, чтобы было чётко видно лицо 😊',
            'uk': 'Потрібні саме фото, не відео 📸 Надішли 2-3 фото хорошої якості, щоб було чітко видно обличчя 😊',
            'en': 'We need photos, not videos 📸 Send 2-3 good quality photos with your face clearly visible 😊'
        }
        return responses.get(question_lang, responses['ru'])
    
    country = detect_country_in_text(q_lower)
    if country:
        country_display = country.capitalize()
        responses = {
            'ru': f"У нас работают девочки со всех стран! {country_display} подходит ✅ При регистрации можешь выбрать любую страну 😊",
            'uk': f"У нас працюють дівчата з усіх країн! {country_display} підходить ✅ При реєстрації можешь вибрати будь-яку країну 😊",
            'en': f"We have girls working from all countries! {country_display} works perfectly ✅ During registration you can choose any country 😊"
        }
        return responses.get(question_lang, responses['ru'])
    
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
            lang_index = {'ru': 0, 'uk': 1, 'en': 2}.get(question_lang, 0)
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
            lang_index = {'ru': 0, 'uk': 1, 'en': 2}.get(question_lang, 0)
            return answers[lang_index]
    
    detailed_keywords = [
        'подробнее', 'больше информации', 'расскажи подробнее', 
        'детальніше', 'більше інформації', 'розкажи детальніше', 
        'more details', 'more information', 'tell me more'
    ]
    
    if any(kw in q_lower for kw in detailed_keywords):
        return detailed_info.get(question_lang, detailed_info['ru'])
    
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
        return responses.get(question_lang, responses['ru'])
    
    return None

async def is_contextual_question(question, history):
    from utils.language_detector import detect_language
    
    question_lang = detect_language(question)
    q_lower = question.lower().strip()
    
    what_to_do_variants = [
        'що мені робити', 'что мне делать', 'що робити', 'что делать',
        'що мені', 'что мне', 'що далі', 'что дальше', 
        'що тепер', 'что теперь', 'що зараз', 'что сейчас',
        'what should i do', 'what now', 'what next', 'what to do', 'what i need to do',
        'і що', 'и что', 'а що', 'а what', 'а тепер', 'а теперь',
        'що мені робити зараз', 'что мне делать сейчас',
        'okay, what', 'ok, what', 'so what', 'okay what'
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
    
    photo_request_keywords = [
        'send 2-3 photos', 'send 2–3 photos', 'пришли 2-3 фото', 'пришли 2–3 фото',
        'надішли 2-3 фото', 'надішли 2–3 фото', 'waiting for photos', 'жду фото', 'чекаю фото',
        'how to start', 'як почати', 'как начать', 'if the format suits'
    ]
    
    instructions_keywords = [
        'інструкц', 'инструкц', 'instruction',
        'реєстр', 'регистр', 'registr',
        'надішли', 'пришли', 'send',
        'скрин', 'screenshot',
        'активуют', 'активують', 'activate',
        'офіс', 'офис', 'office',
        'тестовий період', 'тестовый період',
        'заробити', 'заработать'
    ]
    
    for bot_msg in last_bot_messages:
        if any(kw in bot_msg for kw in photo_request_keywords):
            return {
                'ru': 'Пришли мне 2-3 своих фото (хорошего качества, чтобы было чётко видно лицо) 📸',
                'uk': 'Надішли мені 2-3 свої фото (хорошої якості, щоб було чітко видно обличчя) 📸',
                'en': 'Send me 2-3 photos of yourself (good quality, face clearly visible) 📸'
            }
        
        if 'фото' in bot_msg and ('тільки для' in bot_msg or 'только для' in bot_msg or 'only for' in bot_msg):
            return {
                'ru': 'Нужно отправить мне 2-3 своих фото. После этого я отправлю их на рассмотрение офису 😊',
                'uk': 'Потрібно надіслати мені 2-3 свої фото. Після цього я відправлю їх на розгляд офісу 😊',
                'en': 'You need to send me 2-3 photos of yourself. After that I will send them for office review 😊'
            }
        
        if any(kw in bot_msg for kw in instructions_keywords):
            if 'скрин' in bot_msg or 'screenshot' in bot_msg or 'офіс' in bot_msg or 'офис' in bot_msg:
                return {
                    'ru': 'Просто жди активации от офиса. Обычно это происходит на следующий будний день. Как только активируют — сможешь начать работать! 😊',
                    'uk': 'Просто чекай активації від офісу. Зазвичай це відбувається наступного робочого дня. Як тільки активують — зможеш почати працювати! 😊',
                    'en': 'Just wait for activation from the office. Usually it happens the next business day. Once activated — you can start working! 😊'
                }
            else:
                return {
                    'ru': 'Следуй инструкциям выше шаг за шагом. Если что-то непонятно на конкретном шаге — спрашивай! 😊',
                    'uk': 'Дотримуйся інструкцій вище крок за кроком. Якщо щось незрозуміло на конкретному кроці — питай! 😊',
                    'en': 'Follow the instructions above step by step. If something is unclear at a specific step — ask! 😊'
                }
    
    return None

async def get_ai_response_with_retry(user_id, question, max_retries=3, is_in_groups=False):
    from utils.language_detector import detect_language
    
    logger.info(f"Starting AI request for user {user_id}")
    
    user = await get_user(user_id)
    question_lang = detect_language(question)
    
    direct_answer = await check_faq_direct_match(question, question_lang)
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
        answer = contextual_answer.get(question_lang, contextual_answer.get('ru', ''))
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
            
            if response['escalate']:
                logger.info(f"AI escalated for user {user_id}")
                return response
            
            if response['confidence'] > 0 and response.get('answer'):
                logger.info(f"AI response successful for user {user_id}")
                return response
            
            logger.warning(f"AI returned empty/invalid response for user {user_id}, attempt {attempt + 1}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                
        except asyncio.TimeoutError:
            logger.error(f"AI timeout for user {user_id}, attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                return {
                    'answer': '',
                    'confidence': 0,
                    'escalate': True
                }
        except Exception as e:
            logger.error(f"AI error for user {user_id}, attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                return {
                    'answer': '',
                    'confidence': 0,
                    'escalate': True
                }
    
    logger.warning(f"All AI attempts failed for user {user_id}, escalating")
    return {
        'answer': '',
        'confidence': 0,
        'escalate': True
    }

async def get_ai_response(user_id, question, is_in_groups=False):
    from utils.language_detector import detect_language
    
    user = await get_user(user_id)
    question_lang = detect_language(question)
    
    if await check_forbidden_topics(question):
        logger.info(f"Forbidden topic for user {user_id}")
        return {
            'answer': UNIVERSAL_RESPONSE.get(question_lang, UNIVERSAL_RESPONSE['ru']),
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
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context_prompt}
                ]
            ),
            timeout=45.0
        )
        
        if not response or not hasattr(response, 'choices') or not response.choices:
            logger.warning(f"Empty AI response for user {user_id}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        content = response.choices[0].message.content
        content = content.strip() if hasattr(content, 'strip') else str(content).strip()
        
        if is_g4f_error(content):
            logger.warning(f"g4f error detected for user {user_id}: {content[:100]}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        if content.startswith('```json'):
            content = content[7:-3].strip()
        elif content.startswith('```'):
            content = content[3:-3].strip()
        
        content = content.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.info(f"Non-JSON response for user {user_id}, using as plain text")
            
            if len(content) > 4000:
                content = content[:3800] + "\n\n(продолжение в следующем сообщении...)"
            
            return {
                'answer': content,
                'confidence': 75,
                'escalate': False
            }
        
        if not isinstance(result, dict):
            answer_text = str(result)
            if len(answer_text) > 4000:
                answer_text = answer_text[:3800] + "\n\n(продолжение в следующем сообщении...)"
            
            return {
                'answer': answer_text,
                'confidence': 75,
                'escalate': False
            }
        
        if 'answer' not in result:
            result['answer'] = content
        if 'confidence' not in result:
            result['confidence'] = 70
        if 'escalate' not in result:
            result['escalate'] = result['confidence'] < AI_CONFIDENCE_THRESHOLD
        
        if is_g4f_error(str(result.get('answer', ''))):
            logger.warning(f"g4f error in parsed answer for user {user_id}")
            return {
                'answer': '',
                'confidence': 0,
                'escalate': True
            }
        
        if len(str(result.get('answer', ''))) > 4000:
            result['answer'] = str(result['answer'])[:3800] + "\n\n(продолжение в следующем сообщении...)"
        
        result['answer'] = str(result['answer']).replace('**', '').replace('__', '').replace('*', '').replace('_', '')
        
        logger.info(f"AI response for {user_id}: conf={result['confidence']}, esc={result['escalate']}")
        
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"AI timeout for {user_id}")
        raise
    except Exception as e:
        logger.error(f"AI error for {user_id}: {e}")
        raise