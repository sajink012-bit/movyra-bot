import asyncio
import logging
from datetime import datetime
from typing import Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import db

logger = logging.getLogger(__name__)

class PromotionScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.current_job = None
        self.retry_queue = []
    
    def start(self):
        self.scheduler.start()
        self.schedule_posting()
        logger.info("Promotion scheduler started")
    
    def schedule_posting(self):
        if self.current_job:
            self.current_job.remove()
        
        interval_str = db.get_setting('post_interval_minutes')
        interval = int(interval_str) if interval_str else 30
        
        auto_enabled = db.get_setting('auto_posting_enabled')
        if auto_enabled == 'false':
            logger.info("Auto-posting is disabled")
            return
        
        self.current_job = self.scheduler.add_job(
            self.post_next_promotion,
            trigger=IntervalTrigger(minutes=interval),
            id='promotion_poster',
            replace_existing=True
        )
        logger.info(f"Posting scheduled every {interval} minutes")
    
    async def post_next_promotion(self):
        auto_enabled = db.get_setting('auto_posting_enabled')
        if auto_enabled == 'false':
            return
        
        promotion = db.get_next_promotion()
        if not promotion:
            logger.warning("No active promotions found")
            return
        
        groups = db.get_all_groups(active_only=True)
        if not groups:
            logger.warning("No active groups found")
            return
        
        logger.info(f"Posting promotion #{promotion['id']} - '{promotion['title']}'")
        
        for group in groups:
            await self.post_to_group(promotion, group)
        
        db.update_promotion_sent(promotion['id'])
    
    async def post_to_group(self, promotion: Dict, group: Dict):
        try:
            # Import here to avoid circular import
            from bot import application
            
            message = f"🎬 *{promotion['title']}*\n\n{promotion['description']}\n\n⭐ Rating: {promotion['rating']}/10\n🏷️ {promotion['genres']}\n\n🔗 {promotion['website_link']}"
            
            await application.bot.send_message(
                chat_id=group['group_id'],
                text=message,
                parse_mode='Markdown'
            )
            
            db.log_sent_message(
                promotion_id=promotion['id'],
                group_id=group['group_id'],
                message_id=0,
                status='success'
            )
            logger.info(f"Posted to {group['group_name']}")
        except Exception as e:
            logger.error(f"Failed to post to {group['group_name']}: {e}")
            db.log_sent_message(
                promotion_id=promotion['id'],
                group_id=group['group_id'],
                message_id=0,
                status='failed',
                error=str(e)
            )
    
    def update_interval(self, minutes: int):
        db.set_setting('post_interval_minutes', str(minutes))
        self.schedule_posting()
    
    def pause(self):
        db.set_setting('auto_posting_enabled', 'false')
        if self.current_job:
            self.current_job.remove()
            self.current_job = None
        logger.info("Auto-posting paused")
    
    def resume(self):
        db.set_setting('auto_posting_enabled', 'true')
        self.schedule_posting()
        logger.info("Auto-posting resumed")

scheduler = PromotionScheduler()
