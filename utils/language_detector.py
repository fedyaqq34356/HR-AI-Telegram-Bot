def detect_language(text):
    if not text:
        return 'ru'
    
    text_lower = text.lower()
    
    ukr_chars = sum(1 for c in text_lower if c in 'ґєіїьюяѝєїі')
    eng_words = ['hello', 'hi', 'yes', 'no', 'please', 'thanks', 'thank', 'work', 'money', 'how']
    rus_words = ['привет', 'здравствуй', 'да', 'нет', 'пожалуйста', 'спасибо', 'работа', 'деньги', 'как']
    ukr_words = ['привіт', 'вітаю', 'так', 'ні', 'будь ласка', 'дякую', 'робота', 'гроші', 'як']
    
    eng_count = sum(1 for word in eng_words if word in text_lower)
    rus_count = sum(1 for word in rus_words if word in text_lower)
    ukr_count = sum(1 for word in ukr_words if word in text_lower)
    
    if ukr_chars > 2 or ukr_count > 0:
        return 'uk'
    elif eng_count > rus_count and eng_count > 0:
        return 'en'
    elif rus_count > 0:
        return 'ru'
    
    cyrillic_count = sum(1 for c in text_lower if 'а' <= c <= 'я' or c in 'ёъы')
    latin_count = sum(1 for c in text_lower if 'a' <= c <= 'z')
    
    if latin_count > cyrillic_count:
        return 'en'
    elif ukr_chars > 0:
        return 'uk'
    else:
        return 'ru'
