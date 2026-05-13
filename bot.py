"""
MovYra Telegram Bot - Main Application
"""

import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from database import db
from promotions import promotion_manager
from groups import group_manager
from scheduler import scheduler
from templates import WELCOME_MESSAGE, HELP_MESSAGE, STATUS_TEMPLATE

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - Add your values here or use environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_USER_IDS = [int(x.strip()) for x in os.environ.get('ADMIN_USER_IDS', '').split(',') if x.strip()]
MAIN_GROUP_ID = int(os.environ.get('MAIN_GROUP_ID', '0'))
WEBSITE_BASE_URL = os.environ.get('WEBSITE_BASE_URL', 'https://movyra.com')

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_USER_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        stats = db.get_statistics()
        message = f"""
🎬 **MovYra Bot - Admin Panel**

**📊 Quick Stats:**
• Active Promotions: {stats['promo_count']}
• Connected Groups: {stats['group_count']}
• Messages Sent: {stats['total_sent']}
• Success Rate: {stats['success_rate']}%

**Commands:**
/help - Show all commands
/status - Detailed status
/listpromos - View promotions
/listgroups - View groups
"""
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.message.reply_text("🎬 Welcome to MovYra Bot!\n\nContact @admin for access.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 **MovYra Bot Commands**

**Promotion Management:**
/addpromo - Add new promotion
/editpromo [id] - Edit promotion
/deletepromo [id] - Delete promotion
/listpromos - Show all promotions

**Auto-Posting Control:**
/setinterval [minutes] - Change frequency
/pause - Pause auto-posting
/resume - Resume auto-posting
/status - Show bot status
/broadcast - Send instant promotion

**Group Management:**
/addgroup [group_id] [name] - Add group
/removegroup [group_id] - Remove group
/listgroups - Show all groups
/sendinvite [group_id] - Send invite

**Movie Info:**
/movie [name] - Get movie details
/trending - Get trending movies
/toprated - Get top rated movies
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    stats = db.get_statistics()
    
    status_message = f"""
📊 **Bot Status**

**Auto-Posting:** {'🟢 Running' if stats['auto_posting'] else '🔴 Paused'}
**Interval:** {stats['interval']} minutes
**Active Promotions:** {stats['promo_count']}
**Connected Groups:** {stats['group_count']}
**Total Messages Sent:** {stats['total_sent']}
**Success Rate:** {stats['success_rate']}%
"""
    await update.message.reply_text(status_message, parse_mode='Markdown')

async def list_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listpromos command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    promotions = db.get_all_promotions(active_only=False)
    
    if not promotions:
        await update.message.reply_text("📭 No promotions found. Use /addpromo to create one.")
        return
    
    message = "📋 **Your Promotions:**\n\n"
    for promo in promotions[:20]:
        status = "✅" if promo['active'] else "❌"
        message += f"{status} **ID {promo['id']}:** {promo['title']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setinterval command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/setinterval [minutes]`")
        return
    
    try:
        minutes = int(context.args[0])
        if minutes < 1 or minutes > 1440:
            await update.message.reply_text("❌ Interval must be between 1 and 1440 minutes")
            return
        
        scheduler.update_interval(minutes)
        await update.message.reply_text(f"✅ Interval updated to {minutes} minutes")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number")

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pause command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    scheduler.pause()
    await update.message.reply_text("⏸️ Auto-posting paused")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    scheduler.resume()
    await update.message.reply_text("▶️ Auto-posting resumed")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    promotion = db.get_next_promotion()
    if not promotion:
        await update.message.reply_text("❌ No active promotions found")
        return
    
    groups = db.get_all_groups(active_only=True)
    if not groups:
        await update.message.reply_text("❌ No groups connected")
        return
    
    status_msg = await update.message.reply_text(f"📡 Broadcasting to {len(groups)} groups...")
    
    success_count = 0
    for group in groups:
        await scheduler.post_to_group(promotion, group)
        success_count += 1
        await asyncio.sleep(1)
    
    await status_msg.edit_text(f"✅ Broadcast complete! Sent to {success_count}/{len(groups)} groups")

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addgroup command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: `/addgroup [group_id] [group_name]`")
        return
    
    group_id = context.args[0]
    group_name = ' '.join(context.args[1:])
    
    success = db.add_group(group_id, group_name, added_by=update.effective_user.username)
    
    if success:
        await update.message.reply_text(f"✅ Group '{group_name}' added!")
    else:
        await update.message.reply_text("⚠️ Group already exists")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removegroup command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/removegroup [group_id]`")
        return
    
    group_id = context.args[0]
    success = db.remove_group(group_id)
    
    if success:
        await update.message.reply_text("✅ Group removed")
    else:
        await update.message.reply_text("❌ Group not found")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listgroups command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    groups = db.get_all_groups(active_only=False)
    
    if not groups:
        await update.message.reply_text("📭 No groups added")
        return
    
    message = "👥 **Connected Groups:**\n\n"
    for group in groups[:20]:
        status = "✅" if group['active'] else "❌"
        message += f"{status} {group['group_name']} (`{group['group_id']}`)\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def send_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sendinvite command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/sendinvite [group_id]`")
        return
    
    group_id = context.args[0]
    
    groups = db.get_all_groups(active_only=False)
    target_group = None
    for g in groups:
        if g['group_id'] == group_id:
            target_group = g
            break
    
    if not target_group:
        await update.message.reply_text("❌ Group not found")
        return
    
    await update.message.reply_text(f"📤 Sending invite to {target_group['group_name']}...")
    await group_manager.send_invite_to_group(context, target_group)

async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /movie command"""
    if not context.args:
        await update.message.reply_text("🎬 Usage: `/movie [movie_name]`")
        return
    
    movie_name = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Searching for '{movie_name}'...\n\n(API integration coming soon)")

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trending command"""
    await update.message.reply_text("📊 Trending movies feature coming soon!")

async def toprated_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /toprated command"""
    await update.message.reply_text("🏆 Top rated movies feature coming soon!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not set!")
        print("Please add BOT_TOKEN in Render Environment Variables")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("listpromos", list_promos))
    application.add_handler(CommandHandler("setinterval", set_interval))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("addgroup", add_group))
    application.add_handler(CommandHandler("removegroup", remove_group))
    application.add_handler(CommandHandler("listgroups", list_groups))
    application.add_handler(CommandHandler("sendinvite", send_invite))
    application.add_handler(CommandHandler("movie", movie_command))
    application.add_handler(CommandHandler("trending", trending_command))
    application.add_handler(CommandHandler("toprated", toprated_command))
    
    application.add_error_handler(error_handler)
    
    # Start the scheduler
    scheduler.start()
    
    # Start the bot
    logger.info("Starting MovYra Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
