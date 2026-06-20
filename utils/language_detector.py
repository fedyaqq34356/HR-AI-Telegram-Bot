def detect_language_request(text):
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    russian_keywords = ['russian', 'ru', 'русский', 'руский', 'на русском', 'по-русски', 'по русски']
    ukrainian_keywords = ['ukrainian', 'uk', 'українська', 'украинский', 'украінська', 'на українській', 'на украинском', 'по-українськи', 'по українськи']
    english_keywords = ['english', 'en', 'англійська', 'английский', 'англиский', 'на английском', 'по-английски', 'по английски']
    
    for keyword in russian_keywords:
        if keyword in text_lower:
            return 'ru'
    
    for keyword in ukrainian_keywords:
        if keyword in text_lower:
            return 'uk'
    
    for keyword in english_keywords:
        if keyword in text_lower:
            return 'en'
    
    return None

def detect_language(text):
    if not text:
        return 'ru'
    
    text_lower = text.lower().strip()
    
    ukr_specific_chars = 'ґєії'
    ukr_specific_count = sum(1 for c in text_lower if c in ukr_specific_chars)
    
    eng_words = ['hello', 'hi', 'yes', 'no', 'please', 'thanks', 'thank', 'work', 'money', 'how', 'what', 'when', 'where', 'good', 'bad']
    rus_words = ['привет', 'здравствуй', 'да', 'нет', 'пожалуйста', 'спасибо', 'работа', 'деньги', 'как', 'что', 'когда', 'где', 'хорошо', 'понятно', 'ок', 'супер', 'класс']
    ukr_words = ['привіт', 'вітаю', 'так', 'ні', 'будь ласка', 'дякую', 'робота', 'гроші', 'як', 'що', 'коли', 'де', 'добре', 'зрозуміло', 'гаразд']
    
    eng_count = sum(1 for word in eng_words if word in text_lower)
    rus_count = sum(1 for word in rus_words if word in text_lower)
    ukr_count = sum(1 for word in ukr_words if word in text_lower)
    
    if ukr_specific_count > 0:
        return 'uk'
    
    if ukr_count > 0:
        return 'uk'
    
    if eng_count > 0 and eng_count >= rus_count:
        return 'en'
    
    if rus_count > 0:
        return 'ru'
    
    cyrillic_count = sum(1 for c in text_lower if 'а' <= c <= 'я' or c in 'ёъы')
    latin_count = sum(1 for c in text_lower if 'a' <= c <= 'z')
    
    if latin_count > cyrillic_count and latin_count > 0:
        return 'en'
    
    return 'ru'