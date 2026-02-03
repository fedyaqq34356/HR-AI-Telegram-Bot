import asyncio
import logging
from g4f.client import Client
from g4f.Provider import RetryProvider
import g4f

logger = logging.getLogger(__name__)

all_providers = [
    provider for provider in g4f.Provider.__providers__ 
    if provider.working
]

client = Client(
    provider=RetryProvider(all_providers, shuffle=True)
)

async def translate_text(text, target_lang):
    if not text or len(text.strip()) < 3:
        return text
    
    lang_names = {
        'ru': 'Russian',
        'uk': 'Ukrainian',
        'en': 'English'
    }
    
    target_lang_name = lang_names.get(target_lang, 'Russian')
    
    prompt = f"""Translate this text to {target_lang_name}. 
Keep the same style and tone. 
Do not add any explanations or comments.
Return ONLY the translated text.

Text to translate:
{text}"""
    
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model="",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            ),
            timeout=30.0
        )
        
        if not response or not hasattr(response, 'choices') or not response.choices:
            logger.warning(f"Translation failed for lang={target_lang}")
            return None
        
        translated = response.choices[0].message.content.strip()
        
        if translated.startswith('```'):
            translated = translated.split('```')[1].strip()
        
        logger.info(f"Translated to {target_lang}: {len(translated)} chars")
        return translated
        
    except asyncio.TimeoutError:
        logger.error(f"Translation timeout for lang={target_lang}")
        return None
    except Exception as e:
        logger.error(f"Translation error for lang={target_lang}: {e}")
        return None

async def translate_to_all_languages(text):
    translations = {
        'ru': None,
        'uk': None,
        'en': None
    }
    
    from utils.language_detector import detect_language
    source_lang = detect_language(text)
    
    translations[source_lang] = text
    
    for lang in ['ru', 'uk', 'en']:
        if lang != source_lang:
            translated = await translate_text(text, lang)
            translations[lang] = translated
            await asyncio.sleep(1)
    
    return translations