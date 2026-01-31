import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from states import UserStates
from database import (
    update_application_status, update_user_status, get_setting, 
    save_message, get_user
)
from keyboards import groups_keyboard
from config import GROUP_ID

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("approve_"))
async def approve_application(callback: CallbackQuery, bot, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    
    logger.info(f"Approving application for user {user_id}")
    
    await update_application_status(user_id, 'approved')
    await update_user_status(user_id, 'approved')
    
    user_state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    user_state = FSMContext(storage=state.storage, key=user_state_key)
    await user_state.set_state(UserStates.helping_registration)
    
    logger.info(f"Set state helping_registration for user {user_id}")
    
    user = await get_user(user_id)
    lang = user['language'] if user else 'ru'
    
    screenshot_file = FSInputFile('images/halo_download.jpg')
    
    part1_texts = {
        'ru': """🔰 Скачивание приложения
Заходишь на сайт и скачиваешь приложение For hosts, подходящее для твоего телефона (выделено розовым цветом).
https://livegirl.me/#/mobilepage""",
        'uk': """🔰 Завантаження застосунку
Заходиш на сайт і завантажуєш застосунок For hosts, підходящий для твого телефону (виділено рожевим кольором).
https://livegirl.me/#/mobilepage""",
        'en': """🔰 Downloading the application
Go to the website and download the For hosts application suitable for your phone (highlighted in pink).
https://livegirl.me/#/mobilepage"""
    }
    
    part1_text = part1_texts.get(lang, part1_texts['ru'])
    
    await bot.send_photo(user_id, screenshot_file, caption=part1_text)
    await save_message(user_id, 'bot', f'[Фото с инструкцией]\n{part1_text}')
    
    part2_texts = {
        'ru': """📰 Регистрация
1. Открываешь приложение и нажимаешь «Регистрация».
Вводишь:
• Почту
• Пароль для входа
2. Указываешь:
• Никнейм
• Возраст
• Языки: арабский, английский, украинский, русский
3. В разделе Агентство выбираешь: Tosagency-Ukraine
4. Загружаешь свою фотографию и записываешь короткое видео-приветствие.
🔹 Пример для видео:
Hello, my name is Anya. I am 18 years old. I live in Germany. I want to join.
👉 Укажи своё имя, возраст (можно чуть меньше реального) и страну.
📢 Если не умеешь читать на английском — вот как произносить:
Хеллоу. Май нейм Аня. Ай эм эйтин йерс олд. Ай лив ин Джермани. Ай вонт ту джойн.
5. После записи — пришли скрин, где видно твой ID в приложении и агентство.
6. Я отправляю заявку в офис. На следующий будний день твой аккаунт активируют.""",
        'uk': """📰 Реєстрація
1. Відкриваєш застосунок і натискаєш «Реєстрація».
Вводиш:
• Пошту
• Пароль для входу
2. Вказуєш:
• Нікнейм
• Вік
• Мови: арабська, англійська, українська, російська
3. У розділі Агентство обираєш: Tosagency-Ukraine
4. Завантажуєш своє фото і записуєш коротке відео-вітання.
🔹 Приклад для відео:
Hello, my name is Anya. I am 18 years old. I live in Germany. I want to join.
👉 Вкажи своє ім'я, вік (можна трохи менше реального) і країну.
📢 Якщо не вмієш читати англійською — ось як вимовляти:
Хеллоу. Май нейм Аня. Ай ем ейтін йерс олд. Ай лів ін Джерм��ні. Ай вонт ту джойн.
5. Після запису — надішли скрін, де видно твій ID у застосунку і агентство.
6. Я відправляю заявку в офіс. Наступного робочого дня твій акаунт активують.""",
        'en': """📰 Registration
1. Open the application and click "Registration".
Enter:
• Email
• Login password
2. Specify:
• Nickname
• Age
• Languages: Arabic, English, Ukrainian, Russian
3. In the Agency section choose: Tosagency-Ukraine
4. Upload your photo and record a short video greeting.
🔹 Example for video:
Hello, my name is Anya. I am 18 years old. I live in Germany. I want to join.
👉 State your name, age (can be slightly less than real) and country.
5. After recording — send a screenshot showing your ID in the application and agency.
6. I send the application to the office. The next business day your account will be activated."""
    }
    
    part2_text = part2_texts.get(lang, part2_texts['ru'])
    
    await bot.send_message(user_id, part2_text)
    await save_message(user_id, 'bot', part2_text)
    
    logger.info(f"Registration instructions sent, user {user_id} remains in helping_registration")
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ ОДОБРЕНО"
    )
    await callback.answer("Заявка одобрена")
    logger.info(f"Application approved for user {user_id}")

@router.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: CallbackQuery, bot, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    
    logger.info(f"Rejecting application for user {user_id}")
    
    await update_application_status(user_id, 'rejected')
    await update_user_status(user_id, 'rejected')
    
    user_state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    user_state = FSMContext(storage=state.storage, key=user_state_key)
    await user_state.set_state(UserStates.rejected)
    
    rejection_msg = await get_setting('rejection_message')
    await bot.send_message(user_id, rejection_msg)
    await save_message(user_id, 'bot', rejection_msg)
    
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ ОТКЛОНЕНО"
    )
    await callback.answer("Заявка отклонена")
    logger.info(f"Application rejected for user {user_id}")
