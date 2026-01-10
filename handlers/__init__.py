from aiogram import Router
from .admin import router as admin_router
from .approval import router as approval_router
from .user import router as user_router
from .screenshot import router as screenshot_router
from .reviews import router as reviews_router

def get_router() -> Router:
    router = Router()
    
    router.include_router(admin_router)
    router.include_router(approval_router)
    router.include_router(screenshot_router)
    router.include_router(reviews_router)
    router.include_router(user_router)
    
    return router