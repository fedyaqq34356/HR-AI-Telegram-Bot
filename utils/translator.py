# utils/translator.py
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

async def _translate_with_retry(text, target_lang, max_retries=3):
    if not text or len(text.strip()) < 3:
        return text

    lang_names = {
        'uk': 'Ukrainian',
        'en': 'English'
    }

    target_lang_name = lang_names.get(target_lang, 'English')

    prompt = (
        f"Translate this text to {target_lang_name}.\n"
        "Keep the same style and tone.\n"
        "Do not add any explanations or comments.\n"
        "Return ONLY the translated text.\n\n"
        f"Text to translate:\n{text}"
    )

    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model="",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                ),
                timeout=120.0
            )

            if not response or not hasattr(response, 'choices') or not response.choices:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                logger.warning(f"Translation failed for lang={target_lang} after {max_retries} attempts")
                return None

            translated = response.choices[0].message.content.strip()

            if translated.startswith('```'):
                translated = translated.split('```')[1].strip()

            logger.info(f"Translated to {target_lang}: {len(translated)} chars (attempt {attempt + 1})")
            return translated

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                logger.warning(f"Translation timeout for lang={target_lang}, attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 * (attempt + 1))
                continue
            logger.error(f"Translation timeout for lang={target_lang} after {max_retries} attempts")
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Translation error for lang={target_lang}, attempt {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(2 * (attempt + 1))
                continue
            logger.error(f"Translation error for lang={target_lang} after {max_retries} attempts: {e}")
            return None

    return None

async def translate_ru_to_uk_en(text):
    uk_result, en_result = await asyncio.gather(
        _translate_with_retry(text, 'uk'),
        _translate_with_retry(text, 'en'),
        return_exceptions=True
    )

    uk_translation = uk_result if not isinstance(uk_result, Exception) else None
    en_translation = en_result if not isinstance(en_result, Exception) else None

    return {
        'ru': text,
        'uk': uk_translation,
        'en': en_translation
    }