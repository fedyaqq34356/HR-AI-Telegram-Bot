from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    chatting = State()
    waiting_photos = State()
    asking_work_hours = State()
    asking_experience = State()
    pending_review = State()
    waiting_screenshot = State()
    registered = State()
    rejected = State()
    waiting_admin = State()

class AdminStates(StatesGroup):
    answering_question = State()
    editing_welcome = State()
    adding_forbidden_topic = State()
    adding_forbidden_keywords = State()