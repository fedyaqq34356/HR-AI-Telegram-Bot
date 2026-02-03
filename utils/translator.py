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

async def _translate(text, target_lang):
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

async def translate_ru_to_uk_en(text):
    uk_task = asyncio.create_task(_translate(text, 'uk'))
    en_task = asyncio.create_task(_translate(text, 'en'))

    uk_result, en_result = await asyncio.gather(uk_task, en_task)

    return {
        'ru': text,
        'uk': uk_result,
        'en': en_result
    }