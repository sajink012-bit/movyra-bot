import logging
from typing import Dict

logger = logging.getLogger(__name__)

class GroupManager:
    @staticmethod
    async def send_invite_to_group(context, group_data: Dict):
        try:
            invite_link = group_data.get('group_link', 'https://t.me/movyra_official')
            message = f"🎬 **Join MovYra Official Community!**\n\nGet latest movie updates, reviews & recommendations\n\n[Join Here]({invite_link})"
            
            await context.bot.send_message(
                chat_id=group_data['group_id'],
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Invite sent to {group_data['group_name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send invite: {e}")
            return False

group_manager = GroupManager()
