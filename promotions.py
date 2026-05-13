import logging
from typing import Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import db

logger = logging.getLogger(__name__)

class PromotionManager:
    @staticmethod
    def format_promotion_message(promotion: Dict) -> str:
        rating_stars = "⭐" * int(promotion['rating']) if promotion['rating'] else ""
        return f"""
🎬 *{promotion['title'].upper()}*

{rating_stars} *{promotion['rating']}/10*

📝 {promotion['description']}

🏷️ {promotion['genres']}

🔗 [Watch on MovYra]({promotion['website_link']})
"""
    
    @staticmethod
    def get_promotion_keyboard(promotion: Dict) -> InlineKeyboardMarkup:
        keyboard = [[
            InlineKeyboardButton("🎬 Watch Trailer", url=promotion.get('trailer_link', '#')),
            InlineKeyboardButton("👥 Join Community", url="https://t.me/movyra_official")
        ]]
        return InlineKeyboardMarkup(keyboard)

promotion_manager = PromotionManager()
