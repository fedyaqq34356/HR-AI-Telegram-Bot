from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    chatting = State()
    waiting_photos = State()
    asking_work_hours = State()
    asking_experience = State()
    pending_review = State()
    helping_registration = State()
    waiting_screenshot = State()
    registered = State()
    rejected = State()
    waiting_admin = State()

class AdminStates(StatesGroup):
    answering_question = State()
    editing_welcome = State()
    editing_welcome_lang = State()
    editing_training_link = State()
    editing_chat_link = State()
    adding_forbidden_topic = State()
    adding_forbidden_keywords = State()
