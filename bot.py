"""
MovYra Telegram Bot - Main Application
Complete automation system for movie promotions
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Import local modules
from database import db
from scheduler import scheduler
from groups import group_manager
from promotions import promotion_manager
from templates import WELCOME_MESSAGE, HELP_MESSAGE, STATUS_TEMPLATE

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_USER_IDS = os.environ.get('ADMIN_USER_IDS', '')
ADMIN_IDS = [int(x.strip()) for x in ADMIN_USER_IDS.split(',') if x.strip()] if ADMIN_USER_IDS else []
MAIN_GROUP_ID = int(os.environ.get('MAIN_GROUP_ID', '0')) if os.environ.get('MAIN_GROUP_ID') else 0

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_IDS

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
        await update.message.reply_text(
            "🎬 Welcome to MovYra Bot!\n\n"
            "Your movie promotion and community management bot.\n\n"
            "Contact @admin for access."
        )

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
    """Handle /status command - show bot status"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    stats = db.get_statistics()
    
    status_text = f"""
📊 **Bot Status**

**Status:** {'🟢 Running' if stats['auto_posting'] else '🔴 Paused'}
**Interval:** {stats['interval']} minutes
**Active Promotions:** {stats['promo_count']}
**Connected Groups:** {stats['group_count']}
**Total Messages Sent:** {stats['total_sent']}
**Success Rate:** {stats['success_rate']}%
"""
    await update.message.reply_text(status_text, parse_mode='Markdown')

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
        status = "✅ Active" if promo['active'] else "❌ Inactive"
        message += f"**ID {promo['id']}:** {promo['title']}\n"
        message += f"   Status: {status}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setinterval command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/setinterval [minutes]`\n"
            "Example: `/setinterval 30`",
            parse_mode='Markdown'
        )
        return
    
    try:
        minutes = int(context.args[0])
        if minutes < 1:
            await update.message.reply_text("❌ Interval must be at least 1 minute")
            return
        if minutes > 1440:
            await update.message.reply_text("❌ Interval cannot exceed 1440 minutes (24 hours)")
            return
        
        scheduler.update_interval(minutes)
        await update.message.reply_text(f"✅ Posting interval updated to {minutes} minutes")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number")

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pause command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    scheduler.pause()
    await update.message.reply_text("⏸️ Auto-posting paused. Use /resume to start again.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    scheduler.resume()
    await update.message.reply_text("▶️ Auto-posting resumed!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command - send promotion to all groups immediately"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    # Get the next promotion
    promotion = db.get_next_promotion()
    if not promotion:
        await update.message.reply_text("❌ No active promotions found. Add a promotion first.")
        return
    
    groups = db.get_all_groups(active_only=True)
    if not groups:
        await update.message.reply_text("❌ No groups connected. Add groups first.")
        return
    
    status_msg = await update.message.reply_text(f"📡 Broadcasting to {len(groups)} groups...")
    
    success_count = 0
    for group in groups:
        await scheduler.post_to_group(promotion, group)
        success_count += 1
        await asyncio.sleep(1)  # Rate limiting
    
    await status_msg.edit_text(
        f"✅ Broadcast complete!\n"
        f"Sent to {success_count}/{len(groups)} groups\n"
        f"Promotion: {promotion['title']}"
    )

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addgroup command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Usage: `/addgroup [group_id] [group_name]`\n"
            "Example: `/addgroup -1001234567890 My Movie Group`",
            parse_mode='Markdown'
        )
        return
    
    group_id = context.args[0]
    group_name = ' '.join(context.args[1:])
    
    success = db.add_group(group_id, group_name, added_by=update.effective_user.username)
    
    if success:
        await update.message.reply_text(f"✅ Group '{group_name}' added successfully!")
    else:
        await update.message.reply_text(f"⚠️ Group already exists or couldn't be added")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removegroup command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/removegroup [group_id]`", parse_mode='Markdown')
        return
    
    group_id = context.args[0]
    success = db.remove_group(group_id)
    
    if success:
        await update.message.reply_text("✅ Group removed successfully!")
    else:
        await update.message.reply_text("❌ Group not found")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listgroups command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    groups = db.get_all_groups(active_only=False)
    
    if not groups:
        await update.message.reply_text("📭 No groups added. Use /addgroup to add one.")
        return
    
    message = "👥 **Connected Groups:**\n\n"
    for group in groups[:20]:
        status = "✅ Active" if group['active'] else "❌ Inactive"
        message += f"**Name:** {group['group_name']}\n"
        message += f"**ID:** `{group['group_id']}`\n"
        message += f"**Status:** {status}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def send_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sendinvite command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/sendinvite [group_id]`", parse_mode='Markdown')
        return
    
    group_id = context.args[0]
    
    # Find group
    groups = db.get_all_groups(active_only=False)
    target_group = None
    for g in groups:
        if g['group_id'] == group_id:
            target_group = g
            break
    
    if not target_group:
        await update.message.reply_text("❌ Group not found")
        return
    
    status_msg = await update.message.reply_text(f"📤 Sending invite to {target_group['group_name']}...")
    
    result = await group_manager.send_invite_to_group(context, target_group)
    
    if result:
        await status_msg.edit_text(f"✅ Invite sent successfully to {target_group['group_name']}!")
    else:
        await status_msg.edit_text(f"❌ Failed to send invite to {target_group['group_name']}")

async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /movie command - fetch movie from website"""
    if not context.args:
        await update.message.reply_text(
            "🎬 **Movie Search**\n\n"
            "Usage: `/movie [movie_name]`\n"
            "Example: `/movie Oppenheimer`",
            parse_mode='Markdown'
        )
        return
    
    movie_name = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Searching for '{movie_name}'...\n\n✨ Movie API coming soon!")

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trending command"""
    await update.message.reply_text(
        "📊 **Trending Movies**\n\n"
        "This feature is coming soon! 🚀\n\n"
        "Check back later for trending movie updates."
    )

async def toprated_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /toprated command"""
    await update.message.reply_text(
        "🏆 **Top Rated Movies**\n\n"
        "This feature is coming soon! 🚀\n\n"
        "Check back later for top rated movies."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Try to notify admin
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"⚠️ Bot Error:\n{str(context.error)[:200]}"
            )
        except:
            pass

# Global application variable for scheduler access
application = None

def main():
    """Main function to run the bot"""
    global application
    
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not set!")
        print("Please add BOT_TOKEN in Render Environment Variables")
        return
    
    if not ADMIN_IDS:
        print("⚠️ WARNING: ADMIN_USER_IDS not set! Admin commands will be restricted.")
    
    print(f"🤖 Starting MovYra Bot...")
    print(f"📊 Bot Token: {'✓ Set' if BOT_TOKEN else '✗ Missing'}")
    print(f"👥 Admin IDs: {ADMIN_IDS}")
    
    # Create application
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
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the scheduler
    scheduler.start()
    
    # Start the bot
    logger.info("Starting MovYra Bot...")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
